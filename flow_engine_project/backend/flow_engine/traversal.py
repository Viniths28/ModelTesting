"""Graph traversal helpers.

This module implements the recursive traversal algorithm described in
`engine_build 1.md`. The current implementation supports the basics of:

* Ordering edges by `orderInForm` (fallback create-time)
* askWhen predicate evaluation (supports `python:` and `cypher:`)
* Variable caching (lazy evaluation)
* Source node resolution for PRECEDES edges

The algorithm will be extended in later tasks to cover full Action handling,
variable scoping on edges/nodes, and section completion detection.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple, Union
import re  # NEW: needed for placeholder detection

from loguru import logger

from .evaluators import cypher_eval, python_eval
from .models import EdgeType, EngineResponse, ActionType
from .neo import run_cypher, neo_client
from .errors import FlowError  # new import

# ---------------------------------------------------------------------------
# Context object
# ---------------------------------------------------------------------------


@dataclass
class Context:
    """Execution context shared during traversal."""

    input_params: Dict[str, Any]
    vars: Dict[str, Any] = field(default_factory=dict)
    source_node: Optional[Any] = None  # Neo4j node (dict-like)
    var_defs: Dict[str, Dict[str, Any]] = field(default_factory=dict)  # name -> def
    warnings: List[Dict[str, str]] = field(default_factory=list)

    # Helper to resolve a template variable lazily – *placeholder* implementation.
    def resolve_var(self, name: str) -> Any:  # noqa: D401
        if name in self.vars:
            return self.vars[name]
        var_def = self.var_defs.get(name)
        if not var_def:
            logger.warning("Variable '{}' not found in variable definitions", name)
            self.vars[name] = None
            return None

        evaluator_str = var_def.get("cypher") or var_def.get("python")
        timeout_ms = var_def.get("timeoutMs", 500)
        if not evaluator_str:
            logger.warning("Variable '{}' has no cypher or python evaluator", name)
            self.vars[name] = None
            return None

        logger.debug("Resolving variable '{}' with evaluator: {}", name, evaluator_str[:100] + "..." if len(evaluator_str) > 100 else evaluator_str)

        try:
            if evaluator_str.lower().startswith("cypher:") or var_def.get("cypher"):
                res = cypher_eval(evaluator_str, self.evaluator_ctx, timeout_ms=timeout_ms)
                logger.debug("Variable '{}' resolved to: {} (type: {})", name, res, type(res).__name__)
            else:
                res = python_eval(evaluator_str, self.evaluator_ctx, timeout_ms=timeout_ms)
                logger.debug("Variable '{}' resolved to: {} (type: {})", name, res, type(res).__name__)
        except Exception as exc:
            # Enhanced error handling with more specific error messages
            error_type = type(exc).__name__
            error_msg = str(exc)
            
            # Check for common Cypher syntax errors and provide helpful hints
            if "CypherSyntaxError" in error_type:
                if "Invalid input '}'" in error_msg and "'" in evaluator_str:
                    hint = "Hint: Cypher string literals must use double quotes, not single quotes"
                    enhanced_msg = f"{error_type}: {error_msg}. {hint}"
                else:
                    enhanced_msg = f"{error_type}: {error_msg}"
            else:
                enhanced_msg = f"{error_type}: {error_msg}"
            
            logger.error("Variable '{}' evaluation failed: {}", name, enhanced_msg)
            self.warnings.append({
                "variable": name, 
                "message": enhanced_msg,
                "evaluator": evaluator_str[:200] + "..." if len(evaluator_str) > 200 else evaluator_str
            })
            res = None

        self.vars[name] = res
        return res

    # Helper to expose sourceNode to template evaluators via input_params
    @property
    def evaluator_ctx(self) -> Dict[str, Any]:
        # Expose a reference to the Context itself under a private key so that
        # template substitution can lazily resolve not-yet-evaluated variables
        # via ``Context.resolve_var`` without changing call signatures across
        # the codebase.  The key is prefixed with double underscores to avoid
        # clashing with legitimate variable names defined by users.
        return {
            **self.input_params,
            "sourceNode": self.source_node,
            "sourceNodeId": _get_source_node_id(self.source_node),
            **self.vars,
            "__ctx__": self,  # private backlink for lazy variable loading
        }


# ---------------------------------------------------------------------------
# askWhen evaluation
# ---------------------------------------------------------------------------

def _evaluate_ask_when(expr: Optional[str], ctx: Context) -> bool:
    """Return True if *expr* is truthy or None (default TRUE)."""

    if not expr:
        return True

    expr = expr.strip()

    try:
        if expr.lower().startswith("python:"):
            return bool(python_eval(expr, ctx.evaluator_ctx))
        if expr.lower().startswith("cypher:"):
            return bool(cypher_eval(expr, ctx.evaluator_ctx))
        # Default to python evaluator if no prefix
        return bool(python_eval(expr, ctx.evaluator_ctx))
    except Exception as exc:  # pragma: no cover
        logger.warning("askWhen evaluation errored → raising FlowError: {}", exc)
        raise FlowError(f"askWhen evaluation error: {exc}") from exc


# ---------------------------------------------------------------------------
# Neo4j helper queries
# ---------------------------------------------------------------------------

def _fetch_outgoing_edges(section_id: str) -> List[Tuple[dict, dict]]:
    """Return raw (edge, target_node) rows ordered as per spec."""

    cypher = (
        """
        MATCH (s:Section {sectionId:$sectionId})-[e]->(t)
        WHERE type(e) IN ['PRECEDES','TRIGGERS']
        RETURN e, t
        ORDER BY coalesce(e.orderInForm, e.order), id(e)
        """
    )
    result = run_cypher(cypher, {"sectionId": section_id})
    return [(rec["e"], rec["t"]) for rec in result]


# ---------------------------------------------------------------------------
# Source node resolution & answered check
# ---------------------------------------------------------------------------

def _resolve_source_node(edge_rel, ctx: Context) -> Optional[Any]:  # type: ignore[return-type]
    """Determine sourceNode for the given edge and update context."""

    src_expr = edge_rel.get("sourceNode")  # type: ignore[index]

    if src_expr:
        src_expr = src_expr.strip()
        try:
            if src_expr.lower().startswith("cypher:"):
                node = cypher_eval(src_expr, ctx.evaluator_ctx)
            elif src_expr.lower().startswith("python:"):
                node = python_eval(src_expr, ctx.evaluator_ctx)
            else:
                # ------------------------------------------------------------------
                # NEW: Support variable placeholder syntax e.g. '{{ current_applicant }}'
                # ------------------------------------------------------------------
                _tmpl_re = re.compile(r"\{\{\s*([\w\.]+)\s*\}\}")
                match = _tmpl_re.fullmatch(src_expr)
                if match:
                    var_name = match.group(1).split(".")[0]  # root variable name
                    node = ctx.resolve_var(var_name)
                else:
                    node = None
        except Exception as exc:  # pragma: no cover
            logger.warning("Failed to resolve sourceNode: {}", exc)
            node = None
    else:
        node = ctx.source_node  # fallback

    # Update context for child edges
    ctx.source_node = node
    return node


def _question_answered(source_node, question_id: str) -> bool:
    """Return True if a Datapoint exists that answers *question_id*."""

    if source_node is None:
        return False

    # Enhanced logic: If source_node is an AddressHistory node, find the Applicant that owns it
    actual_source_node = source_node
    
    # Check if source_node is an AddressHistory node
    if hasattr(source_node, 'labels') and 'AddressHistory' in source_node.labels:
        logger.debug("Source node is AddressHistory, finding parent Applicant for question check")
        
        # Get the AddressHistory node ID
        history_id = _get_source_node_id(source_node)
        if history_id is None:
            return False
            
        # Query to find the Applicant that owns this AddressHistory
        if isinstance(history_id, int):
            history_where = "id(history) = $historyId"
        else:
            history_where = "elementId(history) = $historyId"
            
        find_applicant_cypher = f"""
        MATCH (history:AddressHistory)
        WHERE {history_where}
        MATCH (applicant)-[:HAS_HISTORY_PROPERTY]->(history)
        RETURN applicant
        """
        
        with neo_client._driver.session() as _session:
            applicant_record = _session.run(find_applicant_cypher, historyId=history_id).single()
            
        if applicant_record:
            actual_source_node = applicant_record["applicant"]
            logger.debug("Found parent Applicant for AddressHistory, checking from Applicant perspective")
        else:
            logger.warning("Could not find parent Applicant for AddressHistory node")
            return False

    src_id_val = _get_source_node_id(actual_source_node)
    if src_id_val is None:
        return False

    # Depending on the type of identifier construct match condition
    if isinstance(src_id_val, int):
        where_clause = "id(src) = $srcId"
    else:
        # treat as elementId (string)
        where_clause = "elementId(src) = $srcId"

    # Check both direct SUPPLIES and AddressHistory-mediated SUPPLIES patterns
    cypher = (
        f"""
        MATCH (src)
        WHERE {where_clause}
        
        // Check direct pattern: (source)-[:SUPPLIES]->(datapoint)-[:ANSWERS]->(question)
        OPTIONAL MATCH (src)-[:SUPPLIES]->(dp1:Datapoint)-[:ANSWERS]->(q1 {{questionId:$qid}})
        
        // Check AddressHistory pattern: (source)-[:HAS_HISTORY_PROPERTY]->(history)-[:SUPPLIES]->(datapoint)-[:ANSWERS]->(question)
        OPTIONAL MATCH (src)-[:HAS_HISTORY_PROPERTY]->(history)-[:SUPPLIES]->(dp2:Datapoint)-[:ANSWERS]->(q2 {{questionId:$qid}})
        
        // Return true if either pattern found a match
        RETURN CASE 
            WHEN q1 IS NOT NULL OR q2 IS NOT NULL THEN true 
            ELSE false 
        END AS answered
        """
    )
    with neo_client._driver.session() as _session:
        record = _session.run(cypher, srcId=src_id_val, qid=question_id).single()
    
    return record["answered"] if record else False


def _question_answered_in_current_context(source_node, question_id: str) -> bool:
    """
    Return True if a Datapoint exists that answers *question_id* specifically 
    from the current source_node context.
    
    This is used for allowMultiple questions to check if the question has been
    answered in the current loop iteration/context, allowing the same question
    to be asked in different contexts (e.g., different AddressHistory instances).
    """

    if source_node is None:
        return False

    src_id_val = _get_source_node_id(source_node)
    if src_id_val is None:
        return False

    # Depending on the type of identifier construct match condition
    if isinstance(src_id_val, int):
        where_clause = "id(src) = $srcId"
    else:
        # treat as elementId (string)
        where_clause = "elementId(src) = $srcId"

    # For current context check, only look for DIRECT SUPPLIES relationship
    # This means we're checking if THIS specific source node has answered the question
    cypher = (
        f"""
        MATCH (src)
        WHERE {where_clause}
        
        // Check only direct pattern from current source: (source)-[:SUPPLIES]->(datapoint)-[:ANSWERS]->(question)
        OPTIONAL MATCH (src)-[:SUPPLIES]->(dp:Datapoint)-[:ANSWERS]->(q {{questionId:$qid}})
        
        // Return true if direct pattern found a match from this specific source
        RETURN CASE 
            WHEN q IS NOT NULL THEN true 
            ELSE false 
        END AS answered
        """
    )
    with neo_client._driver.session() as _session:
        record = _session.run(cypher, srcId=src_id_val, qid=question_id).single()
    
    return record["answered"] if record else False


# ---------------------------------------------------------------------------
# Action execution helpers
# ---------------------------------------------------------------------------

def _resolve_action_source_node(action_node, ctx: Context) -> None:
    """If the Action node defines its own `sourceNode`, evaluate it."""

    src_expr = action_node.get("sourceNode")  # type: ignore[index]
    if not src_expr:
        return  # keep existing ctx.source_node

    try:
        if src_expr.lower().startswith("cypher:"):
            ctx.source_node = cypher_eval(src_expr, ctx.evaluator_ctx)
        elif src_expr.lower().startswith("python:"):
            ctx.source_node = python_eval(src_expr, ctx.evaluator_ctx)
    except Exception as exc:  # pragma: no cover
        logger.warning("Failed to resolve action sourceNode: {}", exc)


def _execute_action(action_node, ctx: Context, section_id: str) -> Dict[str, Any]:
    """Execute action node and return EngineResponse dict."""

    _resolve_action_source_node(action_node, ctx)

    action_type = action_node.get("actionType")  # type: ignore[index]
    # Accept either Boolean or string values for returnImmediately so that
    # data coming from UI layers that store properties as strings ('true'/'false')
    # is handled gracefully.
    return_immediately = action_node.get("returnImmediately", True)  # type: ignore[index]

    # Defaults
    next_section_id: Optional[str] = None
    created_ids: List[int] = []
    completed_flag = False

    def _filter_params_for_cypher(params: Dict[str, Any]) -> Dict[str, Any]:
        """Filter parameters to remove unsupported types for Cypher execution."""
        safe_params = {}
        for k, v in params.items():
            # Skip private keys
            if k.startswith("__"):
                continue
            # Skip Neo4j objects (Node, Relationship, etc.)
            if hasattr(v, '_graph') or hasattr(v, 'labels') or hasattr(v, 'type'):
                continue
            # Skip other unsupported types
            if isinstance(v, (type, type(None))) and v is not None:
                continue
            # Include supported types
            safe_params[k] = v
        return safe_params

    if action_type == ActionType.CREATE_NODE.value:
        cypher = action_node.get("cypher")  # type: ignore[index]
        if cypher:
            safe_params = _filter_params_for_cypher(ctx.evaluator_ctx)
            with neo_client._driver.session() as _session:
                records = _session.run(cypher, **safe_params).values()
            # Collect any integer IDs returned in first column by convention
            created_ids = [row[0] for row in records if row]

    elif action_type == ActionType.GOTO_SECTION.value:
        next_section_id = action_node.get("nextSectionId")  # type: ignore[index]

    elif action_type == ActionType.COMPLETE_SECTION.value:
        cypher = action_node.get("cypher")  # type: ignore[index]
        if cypher:
            safe_params = _filter_params_for_cypher(ctx.evaluator_ctx)
            run_cypher(cypher, safe_params)
        completed_flag = True

    else:
        logger.warning("Unknown action type {} – ignored", action_type)

    response = EngineResponse(
        sectionId=section_id,
        question=None,
        nextSectionId=next_section_id,
        createdNodeIds=created_ids,
        completed=completed_flag,
        requestVariables=ctx.input_params,
        sourceNode=_get_source_node_id(ctx.source_node),
        vars={name: {"value": val} for name, val in ctx.vars.items()},
        warnings=ctx.warnings,
    ).dict()

    if not return_immediately:
        # Continue walking from this Action node to follow its outgoing edges
        follow_resp = _traverse(action_node, ctx, section_id)
        # Merge created IDs from this action with any downstream ones
        follow_resp["createdNodeIds"] = created_ids + follow_resp.get("createdNodeIds", [])
        return follow_resp

    return response


# ---------------------------------------------------------------------------
# Variable definitions loading
# ---------------------------------------------------------------------------

def _load_section_vars(section_id: str) -> Dict[str, Dict[str, Any]]:
    cypher = "MATCH (s:Section {sectionId:$sid}) RETURN s.variables AS vars"  # variables is JSON string

    with neo_client._driver.session() as _session:
        rec = _session.run(cypher, sid=section_id).single()

    if rec is None:
        return {}

    raw = rec["vars"]
    if not raw:
        return {}
    try:
        parsed = json.loads(raw)
    except Exception:
        return {}
    return {v["name"]: v for v in parsed}


# ---------------------------------------------------------------------------
# Utility: fetch edges for arbitrary node
# ---------------------------------------------------------------------------

def _fetch_outgoing_edges_for_node(node_id: int) -> List[Tuple[dict, dict]]:
    """Return (edge, target_node) tuples for *node_id* ordered as per spec."""

    cypher = (
        """
        MATCH (n) WHERE id(n) = $nid
        MATCH (n)-[e]->(t)
        WHERE type(e) IN ['PRECEDES','TRIGGERS']
        RETURN e, t
        ORDER BY coalesce(e.orderInForm, e.order), id(e)
        """
    )

    with neo_client._driver.session() as _session:
        result = _session.run(cypher, nid=node_id)
        return [(r["e"], r["t"]) for r in result]


# ---------------------------------------------------------------------------
# Recursive traversal implementation
# ---------------------------------------------------------------------------

def _traverse(current_node, ctx: Context, section_id: str) -> Dict[str, Any]:
    """Depth-first traversal starting from *current_node* (Section/Question/Action)."""

    for edge_rel, target_node in _fetch_outgoing_edges_for_node(current_node.id):  # type: ignore[attr-defined]
        edge_type = edge_rel.type  # PRECEDES / TRIGGERS
        ask_when = edge_rel.get("askWhen")  # type: ignore[index]

        # Merge edge-level variable defs
        if edge_rel.get("variables"):
            try:
                edge_vars = json.loads(edge_rel["variables"])
                ctx.var_defs.update({v["name"]: v for v in edge_vars})
            except Exception:
                pass

        # Resolve and propagate sourceNode
        _resolve_source_node(edge_rel, ctx)

        # Evaluate askWhen predicate
        if not _evaluate_ask_when(ask_when, ctx):
            continue

        # --------------------------------------------------------------
        # Target is Question
        # --------------------------------------------------------------
        if edge_type == EdgeType.PRECEDES.value and target_node.labels.intersection({"Question"}):  # type: ignore[attr-defined]
            question_id = target_node["questionId"]  # type: ignore[index]
            allow_multiple = target_node.get("allowMultiple", False) # type: ignore[index]

            # Enhanced logic for allowMultiple vs regular questions
            if allow_multiple:
                # For allowMultiple questions, we DON'T check if answered in current context
                # because these are designed for loops where the same question is asked multiple
                # times against the same container node (e.g., AddressHistory).
                # Instead, we rely on the edge conditions (askWhen variables) to control when 
                # the loop should exit.
                logger.debug("Asking allowMultiple question {} (loop controlled by edge conditions)", question_id)
            else:
                # For regular questions, check if answered anywhere (existing logic)
                is_answered = _question_answered(ctx.source_node, question_id)
                
                if is_answered:
                    logger.debug("Question {} already answered – delve deeper", question_id)
                    # Recurse into this question to follow its outgoing edges
                    return _traverse(target_node, ctx, section_id)
                
                # If not answered, ask the question
                logger.debug("Asking regular question {}", question_id)
            
            # Ask the question (either allowMultiple or regular not answered)
            logger.debug("Stopping traversal – next question {}", question_id)
            return EngineResponse(
                sectionId=section_id,
                question={"questionId": question_id},
                nextSectionId=None,
                completed=False,
                createdNodeIds=[],
                requestVariables=ctx.input_params,
                sourceNode=_get_source_node_id(ctx.source_node),
                vars={name: {"value": val} for name, val in ctx.vars.items()},
                warnings=ctx.warnings,
            ).dict()

        # --------------------------------------------------------------
        # Target is Action
        # --------------------------------------------------------------
        if "actionType" in target_node:
            logger.debug("Executing action {}", target_node["actionId"])
            return _execute_action(target_node, ctx, section_id)

    # No edges matched → completed
    logger.debug("Node {} completed – no further edges", current_node)
    return EngineResponse(
        sectionId=section_id,
        question=None,
        nextSectionId=None,
        completed=True,
        createdNodeIds=[],
        requestVariables=ctx.input_params,
        sourceNode=_get_source_node_id(ctx.source_node),
        vars={name: {"value": val} for name, val in ctx.vars.items()},
        warnings=ctx.warnings,
    ).dict()


# ---------------------------------------------------------------------------
# Traversal entry-point (public)
# ---------------------------------------------------------------------------

def walk_section(start_section_id: str, ctx_dict: Dict[str, Any]) -> Dict[str, Any]:
    """Traverse a Section recursively until next unanswered question or control-flow change."""

    # Fetch the Section node object safely within a managed session so the
    # result is consumed before the session closes.
    with neo_client._driver.session() as _session:
        record = _session.run(
            "MATCH (s:Section {sectionId:$sid}) RETURN s LIMIT 1",
            sid=start_section_id,
        ).single()

    if record is None:
        raise ValueError(f"Section '{start_section_id}' not found")

    section_node = record["s"]

    ctx = Context(input_params=ctx_dict)
    
    # Resolve section-level sourceNode BEFORE loading variables
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

    ctx.var_defs.update(_load_section_vars(start_section_id))

    return _traverse(section_node, ctx, start_section_id) 


# Helper -----------------------------------------------------------------
def _get_source_node_id(node):
    """Return a safe identifier for *node* that may be a Neo4j Node, dict, str or int."""
    if node is None:
        return None
    # Neo4j 5 python driver Node has .element_id
    if hasattr(node, "element_id"):
        return node.element_id
    # Neo4j 4 driver Node uses .id
    if hasattr(node, "id"):
        return node.id
    # If we received a dict representing node properties
    if isinstance(node, dict) and "id" in node:
        return node["id"]
    # Otherwise assume it is already a scalar identifier (str/int)
    return node 