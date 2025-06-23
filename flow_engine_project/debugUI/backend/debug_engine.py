"""Enhanced flow execution engine with comprehensive debug information capture."""

import time
import json
import sys
import os
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from loguru import logger

# Add the parent backend directory to the path so we can import the flow engine
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'backend'))

from flow_engine.neo import neo_client
from flow_engine.traversal import Context, _evaluate_ask_when, _resolve_source_node, _execute_action
from flow_engine.evaluators import cypher_eval, python_eval
from flow_engine.models import EngineResponse

try:
    from .models import (
        DebugInfo, TraversalStep, VariableEvaluation, ConditionEvaluation, 
        SourceNodeInfo, NodeType, VariableStatus
    )
except ImportError:  # Running as a stand-alone script
    from models import (
        DebugInfo, TraversalStep, VariableEvaluation, ConditionEvaluation, 
        SourceNodeInfo, NodeType, VariableStatus
    )

class DebugContext(Context):
    """Enhanced context that captures debug information during execution."""
    
    def __init__(self, input_params: Dict[str, Any]):
        super().__init__(input_params)
        
        # Debug tracking
        self.debug_info = DebugInfo(totalDuration=0)
        self.step_counter = 0
        self.start_time = time.perf_counter()
        
        # Execution tracking
        self.traversal_path: List[TraversalStep] = []
        self.variable_evaluations: List[VariableEvaluation] = []
        self.condition_evaluations: List[ConditionEvaluation] = []
        self.source_node_history: List[SourceNodeInfo] = []
    
    def add_traversal_step(
        self, 
        node_type: NodeType, 
        node_id: str, 
        node_name: Optional[str],
        action: str,
        duration: int,
        details: Optional[Dict[str, Any]] = None
    ):
        """Add a step to the traversal path."""
        self.step_counter += 1
        step = TraversalStep(
            step=self.step_counter,
            nodeType=node_type,
            nodeId=node_id,
            nodeName=node_name,
            action=action,
            timestamp=datetime.now(),
            duration=duration,
            details=details or {}
        )
        self.traversal_path.append(step)
        logger.debug(f"Debug: Step {self.step_counter} - {node_type}:{node_id} ({action}) took {duration}ms")
    
    @staticmethod
    def _serialize_value(val):
        """Convert values (including Neo4j types) into JSON-serialisable primitives."""
        # Primitive types are already serialisable
        if isinstance(val, (str, int, float, bool)) or val is None:
            return val
        
        # Handle Neo4j graph objects lazily imported to avoid optional dependency issues
        try:
            from neo4j.graph import Node, Relationship, Path  # type: ignore
            if isinstance(val, Node):
                # Convert to dict of properties only
                return dict(val)
            if isinstance(val, Relationship):
                return {
                    "type": val.type,
                    "start": val.start_node.element_id,
                    "end": val.end_node.element_id,
                    "properties": dict(val)
                }
            if isinstance(val, Path):
                # Represent path as list of node ids for simplicity
                return [n.element_id for n in val.nodes]
        except ImportError:
            pass  # neo4j not available, continue fallback

        # Handle iterable types recursively
        if isinstance(val, (list, tuple, set)):
            return [DebugContext._serialize_value(v) for v in val]
        if isinstance(val, dict):
            return {k: DebugContext._serialize_value(v) for k, v in val.items()}

        # Fallback to string representation
        return str(val)
    
    def add_variable_evaluation(
        self,
        name: str,
        source: str,
        source_id: str,
        expression: str,
        status: VariableStatus,
        value: Any = None,
        error: Optional[str] = None,
        duration: int = 0,
        dependencies: List[str] = None
    ):
        """Add a variable evaluation record."""
        # Ensure value is JSON-serialisable to avoid response encoding errors
        safe_value = self._serialize_value(value)

        evaluation = VariableEvaluation(
            name=name,
            source=source,
            sourceId=source_id,
            expression=expression,
            status=status,
            value=safe_value,
            error=error,
            duration=duration,
            dependencies=dependencies or []
        )
        self.variable_evaluations.append(evaluation)
        logger.debug(f"Debug: Variable {name} from {source}:{source_id} -> {status}")
    
    def add_condition_evaluation(
        self,
        edge_id: str,
        source_node: str,
        target_node: str,
        ask_when: str,
        result: bool,
        variables: List[str],
        duration: int,
        error: Optional[str] = None
    ):
        """Add a condition evaluation record."""
        evaluation = ConditionEvaluation(
            edgeId=edge_id,
            sourceNode=source_node,
            targetNode=target_node,
            askWhen=ask_when,
            result=result,
            variables=variables,
            duration=duration,
            error=error
        )
        self.condition_evaluations.append(evaluation)
        logger.debug(f"Debug: Condition {edge_id} -> {result}")
    
    def add_source_node_info(
        self,
        node_id: Optional[str],
        expression: Optional[str],
        status: str,
        value: Optional[Dict[str, Any]] = None
    ):
        """Add source node resolution information."""
        # Ensure node_id is always a string for Pydantic validation
        if node_id is not None and not isinstance(node_id, str):
            node_id = str(node_id)

        info = SourceNodeInfo(
            nodeId=node_id,
            expression=expression,
            status=status,
            value=value
        )
        self.source_node_history.append(info)
        logger.debug(f"Debug: Source node resolved to {node_id} ({status})")
    
    def resolve_var(self, name: str) -> Any:
        """Enhanced variable resolution with debug tracking."""
        start_time = time.perf_counter()
        
        if name in self.vars:
            # Already resolved
            duration = int((time.perf_counter() - start_time) * 1000)
            self.add_variable_evaluation(
                name=name,
                source="cache",
                source_id="context",
                expression="cached",
                status=VariableStatus.RESOLVED,
                value=self.vars[name],
                duration=duration
            )
            return self.vars[name]
        
        var_def = self.var_defs.get(name)
        if not var_def:
            duration = int((time.perf_counter() - start_time) * 1000)
            self.add_variable_evaluation(
                name=name,
                source="unknown",
                source_id="unknown",
                expression="not_found",
                status=VariableStatus.ERROR,
                error="Variable definition not found",
                duration=duration
            )
            self.vars[name] = None
            return None
        
        evaluator_str = var_def.get("cypher") or var_def.get("python")
        timeout_ms = var_def.get("timeoutMs", 500)
        source_id = var_def.get("sourceId", "unknown")
        
        if not evaluator_str:
            duration = int((time.perf_counter() - start_time) * 1000)
            self.add_variable_evaluation(
                name=name,
                source="definition",
                source_id=source_id,
                expression="empty",
                status=VariableStatus.ERROR,
                error="No evaluator expression found",
                duration=duration
            )
            self.vars[name] = None
            return None
        
        try:
            if evaluator_str.lower().startswith("cypher:") or var_def.get("cypher"):
                res = cypher_eval(evaluator_str, self.evaluator_ctx, timeout_ms=timeout_ms)
                evaluator_type = "cypher"
            else:
                res = python_eval(evaluator_str, self.evaluator_ctx, timeout_ms=timeout_ms)
                evaluator_type = "python"
            
            duration = int((time.perf_counter() - start_time) * 1000)
            self.add_variable_evaluation(
                name=name,
                source=evaluator_type,
                source_id=source_id,
                expression=evaluator_str,
                status=VariableStatus.RESOLVED,
                value=res,
                duration=duration
            )
            
        except Exception as exc:
            duration = int((time.perf_counter() - start_time) * 1000)
            self.add_variable_evaluation(
                name=name,
                source=var_def.get("source", "unknown"),
                source_id=source_id,
                expression=evaluator_str,
                status=VariableStatus.ERROR,
                error=str(exc),
                duration=duration
            )
            self.warnings.append({"variable": name, "message": str(exc)})
            res = None
        
        self.vars[name] = res
        return res
    
    def finalize_debug_info(self) -> DebugInfo:
        """Finalize and return complete debug information."""
        total_duration = int((time.perf_counter() - self.start_time) * 1000)
        
        return DebugInfo(
            traversalPath=self.traversal_path,
            variableEvaluations=self.variable_evaluations,
            conditionEvaluations=self.condition_evaluations,
            sourceNodeHistory=self.source_node_history,
            totalDuration=total_duration,
            errorCount=len([v for v in self.variable_evaluations if v.status == VariableStatus.ERROR]) +
                       len([c for c in self.condition_evaluations if c.error]),
            warningCount=len(self.warnings)
        )

def debug_evaluate_ask_when(expr: Optional[str], ctx: DebugContext, edge_id: str, source_id: str, target_id: str) -> bool:
    """Enhanced askWhen evaluation with debug tracking."""
    start_time = time.perf_counter()
    
    if not expr:
        duration = int((time.perf_counter() - start_time) * 1000)
        ctx.add_condition_evaluation(
            edge_id=edge_id,
            source_node=source_id,
            target_node=target_id,
            ask_when="default_true",
            result=True,
            variables=[],
            duration=duration
        )
        return True
    
    expr = expr.strip()
    variables_used = []  # TODO: Extract variables from expression
    
    try:
        if expr.lower().startswith("python:"):
            result = bool(python_eval(expr, ctx.evaluator_ctx))
        elif expr.lower().startswith("cypher:"):
            result = bool(cypher_eval(expr, ctx.evaluator_ctx))
        else:
            # Default to python evaluator if no prefix
            result = bool(python_eval(expr, ctx.evaluator_ctx))
        
        duration = int((time.perf_counter() - start_time) * 1000)
        ctx.add_condition_evaluation(
            edge_id=edge_id,
            source_node=source_id,
            target_node=target_id,
            ask_when=expr,
            result=result,
            variables=variables_used,
            duration=duration
        )
        return result
        
    except Exception as exc:
        duration = int((time.perf_counter() - start_time) * 1000)
        ctx.add_condition_evaluation(
            edge_id=edge_id,
            source_node=source_id,
            target_node=target_id,
            ask_when=expr,
            result=False,
            variables=variables_used,
            duration=duration,
            error=str(exc)
        )
        logger.warning("askWhen evaluation errored → treating as FALSE: {}", exc)
        return False

def debug_resolve_source_node(edge_rel, ctx: DebugContext) -> Optional[Any]:
    """Enhanced source node resolution with debug tracking."""
    start_time = time.perf_counter()
    
    src_expr = edge_rel.get("sourceNode")
    
    if src_expr:
        src_expr = src_expr.strip()
        try:
            if src_expr.lower().startswith("cypher:"):
                node = cypher_eval(src_expr, ctx.evaluator_ctx)
            elif src_expr.lower().startswith("python:"):
                node = python_eval(src_expr, ctx.evaluator_ctx)
            else:
                # Support variable placeholder syntax e.g. '{{ current_applicant }}'
                import re
                _tmpl_re = re.compile(r"\{\{\s*([\w\.]+)\s*\}\}")
                match = _tmpl_re.fullmatch(src_expr)
                if match:
                    var_name = match.group(1).split(".")[0]  # root variable name
                    node = ctx.resolve_var(var_name)
                else:
                    node = None
        except Exception as exc:
            logger.warning("Failed to resolve sourceNode: {}", exc)
            node = None
            
        duration = int((time.perf_counter() - start_time) * 1000)
        ctx.add_source_node_info(
            node_id=node.id if hasattr(node, 'id') else None,
            expression=src_expr,
            status="resolved" if node else "error",
            value=dict(node) if node else None
        )
    else:
        node = ctx.source_node  # fallback
        duration = int((time.perf_counter() - start_time) * 1000)
        ctx.add_source_node_info(
            node_id=node.id if node and hasattr(node, 'id') else None,
            expression="fallback",
            status="inherited",
            value=dict(node) if node else None
        )
    
    # Update context for child edges
    ctx.source_node = node
    return node

def debug_traverse(current_node, ctx: DebugContext, section_id: str) -> Dict[str, Any]:
    """Enhanced traversal with comprehensive debug tracking."""
    step_start = time.perf_counter()
    
    node_data = dict(current_node)
    node_type = None
    node_name = None
    node_id = None
    
    # Determine node type and extract info
    if hasattr(current_node, 'labels'):
        labels = list(current_node.labels)
        if 'Section' in labels:
            node_type = NodeType.SECTION
            node_name = node_data.get('name', 'Unnamed Section')
            node_id = node_data.get('sectionId', f'internal_{current_node.id}')
        elif 'Question' in labels:
            node_type = NodeType.QUESTION
            node_name = node_data.get('prompt', 'Unnamed Question')
            node_id = node_data.get('questionId', f'internal_{current_node.id}')
        elif 'Action' in labels:
            node_type = NodeType.ACTION
            node_name = node_data.get('actionType', 'Unknown Action')
            node_id = node_data.get('actionId', f'internal_{current_node.id}')
    else:
        # Handle case where we have a dict instead of Neo4j node
        if 'sectionId' in node_data:
            node_type = NodeType.SECTION
            node_name = node_data.get('name', 'Unnamed Section')
            node_id = node_data.get('sectionId')
        elif 'questionId' in node_data:
            node_type = NodeType.QUESTION
            node_name = node_data.get('prompt', 'Unnamed Question')
            node_id = node_data.get('questionId')
        elif 'actionId' in node_data:
            node_type = NodeType.ACTION
            node_name = node_data.get('actionType', 'Unknown Action')
            node_id = node_data.get('actionId')
    
    # Get outgoing edges from this node
    with neo_client._driver.session() as session:
        edges_result = session.run("""
            MATCH (n) WHERE elementId(n) = $nodeId
            MATCH (n)-[e]->(target)
            WHERE type(e) IN ['PRECEDES','TRIGGERS']
            RETURN e, target, elementId(e) as edgeId
            ORDER BY coalesce(e.orderInForm, e.order), elementId(e)
        """, nodeId=current_node.element_id if hasattr(current_node, 'element_id') else str(current_node.id))
        
        edges = edges_result.values()
    
    step_duration = int((time.perf_counter() - step_start) * 1000)
    ctx.add_traversal_step(
        node_type=node_type or NodeType.SECTION,
        node_id=node_id or "unknown",
        node_name=node_name,
        action="evaluated",
        duration=step_duration,
        details={
            "edges_found": len(edges),
            "node_data": node_data
        }
    )
    
    for edge_rel, target_node, edge_id in edges:
        edge_type = edge_rel.type  # PRECEDES / TRIGGERS
        ask_when = edge_rel.get("askWhen")
        
        target_data = dict(target_node)
        target_id = target_data.get('questionId') or target_data.get('actionId') or target_data.get('sectionId', 'unknown')
        
        # Merge edge-level variable defs
        if edge_rel.get("variables"):
            try:
                edge_vars = json.loads(edge_rel["variables"])
                for var in edge_vars:
                    var["sourceId"] = edge_id  # Track where this variable came from
                    ctx.var_defs[var["name"]] = var
            except Exception:
                pass
        
        # Resolve and propagate sourceNode
        debug_resolve_source_node(edge_rel, ctx)
        
        # Evaluate askWhen predicate
        if not debug_evaluate_ask_when(ask_when, ctx, edge_id, node_id or "unknown", target_id):
            continue
        
        # Handle different target types
        if edge_type == "PRECEDES" and target_node.labels.intersection({"Question"}):
            question_id = target_node["questionId"]
            
            # Check if question is answered (simplified for debug)
            if False:  # For now, assume not answered to see full flow
                logger.debug("Question {} already answered – delve deeper", question_id)
                return debug_traverse(target_node, ctx, section_id)
            
            logger.debug("Stopping traversal – next unanswered question {}", question_id)
            
            # Record final step
            ctx.add_traversal_step(
                node_type=NodeType.QUESTION,
                node_id=question_id,
                node_name=target_data.get('prompt', 'Unnamed Question'),
                action="stopped_here",
                duration=0,
                details={"reason": "unanswered_question"}
            )
            
            return EngineResponse(
                sectionId=section_id,
                question={"questionId": question_id},
                nextSectionId=None,
                completed=False,
                createdNodeIds=[],
                requestVariables=ctx.input_params,
                sourceNode=ctx.source_node.id if ctx.source_node else None,
                vars={name: {"value": DebugContext._serialize_value(val)} for name, val in ctx.vars.items()},
                warnings=ctx.warnings,
            ).dict()
        
        # Handle Action nodes
        if "actionType" in target_data:
            logger.debug("Executing action {}", target_data["actionId"])
            
            action_start = time.perf_counter()
            response = _execute_action(target_node, ctx)
            action_duration = int((time.perf_counter() - action_start) * 1000)
            
            ctx.add_traversal_step(
                node_type=NodeType.ACTION,
                node_id=target_data["actionId"],
                node_name=target_data.get("actionType", "Unknown Action"),
                action="executed",
                duration=action_duration,
                details={
                    "action_type": target_data.get("actionType"),
                    "created_ids": response.get("createdNodeIds", []),
                    "next_section": response.get("nextSectionId")
                }
            )
            
            return response
    
    # No edges matched → completed
    logger.debug("Node {} completed – no further edges", current_node)
    
    ctx.add_traversal_step(
        node_type=node_type or NodeType.SECTION,
        node_id=node_id or "unknown",
        node_name=node_name,
        action="completed",
        duration=0,
        details={"reason": "no_more_edges"}
    )
    
    return EngineResponse(
        sectionId=section_id,
        question=None,
        nextSectionId=None,
        completed=True,
        createdNodeIds=[],
        requestVariables=ctx.input_params,
        sourceNode=ctx.source_node.id if ctx.source_node else None,
        vars={name: {"value": DebugContext._serialize_value(val)} for name, val in ctx.vars.items()},
        warnings=ctx.warnings,
    ).dict()

def debug_walk_section(start_section_id: str, ctx_dict: Dict[str, Any]) -> Tuple[Dict[str, Any], DebugInfo]:
    """Enhanced section traversal with debug information capture."""
    logger.info("Debug engine invoked for section {} | params={}", start_section_id, ctx_dict)
    
    # Fetch the Section node
    with neo_client._driver.session() as session:
        record = session.run(
            "MATCH (s:Section {sectionId:$sid}) RETURN s LIMIT 1",
            sid=start_section_id,
        ).single()
    
    if record is None:
        raise ValueError(f"Section '{start_section_id}' not found")
    
    section_node = record["s"]
    
    # Create debug context
    ctx = DebugContext(input_params=ctx_dict)
    
    # Resolve section-level sourceNode (if any) BEFORE variable loading so $sourceNodeId works
    section_source_expr = section_node.get("sourceNode") if hasattr(section_node, "get") else None
    if section_source_expr:
        section_source_expr = section_source_expr.strip()
        try:
            if section_source_expr.lower().startswith("cypher:"):
                ctx.source_node = cypher_eval(section_source_expr, ctx.evaluator_ctx)
            elif section_source_expr.lower().startswith("python:"):
                ctx.source_node = python_eval(section_source_expr, ctx.evaluator_ctx)
        except Exception as exc:
            logger.warning("Failed to resolve section sourceNode: {}", exc)
            ctx.source_node = None
        ctx.add_source_node_info(
            node_id=(ctx.source_node.id if ctx.source_node and hasattr(ctx.source_node, 'id') else None),
            expression=section_source_expr,
            status="resolved" if ctx.source_node else "error",
            value=(dict(ctx.source_node) if ctx.source_node else None)
        )
    
    # Load section variables
    from flow_engine.traversal import _load_section_vars
    section_vars = _load_section_vars(start_section_id)
    for var_name, var_def in section_vars.items():
        var_def["sourceId"] = start_section_id  # Track source
        ctx.var_defs[var_name] = var_def
    
    # Execute traversal
    response = debug_traverse(section_node, ctx, start_section_id)
    
    # Finalize debug info
    debug_info = ctx.finalize_debug_info()
    
    logger.info("Debug engine response | completed={} question={} nextSection={} debug_steps={}",
                response.get("completed"),
                response.get("question"),
                response.get("nextSectionId"),
                len(debug_info.traversalPath))
    
    return response, debug_info 