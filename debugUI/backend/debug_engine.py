"""Enhanced debug engine that extends the existing flow engine traversal."""

import sys
import os
import time
import json
from typing import Dict, Any, List, Optional, Union
from loguru import logger

# Add the flow_engine_project path to access the existing flow engine
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'flow_engine_project', 'backend'))

try:
    from flow_engine.traversal import walk_section, Context, _traverse, _question_answered
    from flow_engine.neo import neo_client
    from flow_engine.models import EngineResponse
except ImportError as e:
    logger.error(f"Failed to import flow engine modules: {e}")
    # Fallback for development
    class Context:
        def __init__(self, input_params):
            self.input_params = input_params
            self.vars = {}
            self.warnings = []
            self.source_node = None

from models import (
    DebugInformation, 
    TraversalStep, 
    VariableEvaluation, 
    ConditionEvaluation, 
    SourceNodeResolution,
    DebugExecutionResponse
)


class DebugContext(Context):
    """Enhanced context that captures debug information during traversal."""
    
    def __init__(self, input_params: Dict[str, Any]):
        super().__init__(input_params)
        self.debug_info = DebugInformation()
        self.step_counter = 0
        self.start_time = time.time()
        
    def add_traversal_step(self, 
                          node_type: str, 
                          node_id: str, 
                          node_data: Dict[str, Any],
                          edge_type: str = None,
                          edge_data: Dict[str, Any] = None):
        """Add a traversal step to debug information."""
        self.step_counter += 1
        step_start = time.time()
        
        step = TraversalStep(
            step_number=self.step_counter,
            node_type=node_type,
            node_id=node_id,
            node_data=node_data,
            edge_type=edge_type,
            edge_data=edge_data,
            execution_time=time.time() - step_start,
            variables_at_step={name: self._create_variable_evaluation(name, val) 
                             for name, val in self.vars.items()},
            conditions_evaluated=[],
            source_node_resolution=None
        )
        
        self.debug_info.traversal_path.append(step)
        return step
        
    def add_variable_evaluation(self, name: str, expression: str = None, value: Any = None, 
                              status: str = "resolved", error: str = None, 
                              dependencies: List[str] = None):
        """Add variable evaluation debug info."""
        eval_start = time.time()
        
        evaluation = VariableEvaluation(
            name=name,
            status=status,
            expression=expression,
            value=value,
            error=error,
            dependencies=dependencies or [],
            evaluation_time=time.time() - eval_start
        )
        
        self.debug_info.variable_evaluations[name] = evaluation
        return evaluation
        
    def add_condition_evaluation(self, expression: str, result: bool, 
                               variables_used: List[str] = None, error: str = None):
        """Add condition evaluation debug info."""
        eval_start = time.time()
        
        evaluation = ConditionEvaluation(
            expression=expression,
            result=result,
            variables_used=variables_used or [],
            evaluation_time=time.time() - eval_start,
            error=error
        )
        
        self.debug_info.condition_evaluations.append(evaluation)
        return evaluation
        
    def add_source_node_resolution(self, expression: str, resolved_value: Any = None,
                                 node_id: str = None, error: str = None):
        """Add source node resolution debug info."""
        resolution_start = time.time()
        
        resolution = SourceNodeResolution(
            expression=expression,
            resolved_value=resolved_value,
            node_id=node_id,
            error=error,
            resolution_time=time.time() - resolution_start
        )
        
        self.debug_info.source_node_resolutions.append(resolution)
        return resolution
        
    def add_error(self, error: str):
        """Add error to debug info."""
        self.debug_info.errors.append(error)
        
    def add_warning(self, warning: str):
        """Add warning to debug info."""
        self.debug_info.warnings.append(warning)
        
    def finalize_debug_info(self):
        """Finalize debug information with total execution time."""
        self.debug_info.total_execution_time = time.time() - self.start_time
        
    def _create_variable_evaluation(self, name: str, value: Any) -> VariableEvaluation:
        """Create a variable evaluation from current state."""
        return VariableEvaluation(
            name=name,
            status="resolved",
            value=value,
            dependencies=[],
            evaluation_time=0.0
        )


def debug_walk_section(start_section_id: str, 
                      ctx_dict: Dict[str, Any], 
                      is_primary_flow: bool = True) -> DebugExecutionResponse:
    """Enhanced walk_section with comprehensive debug capture."""
    
    debug_ctx = DebugContext(ctx_dict)
    debug_ctx.add_variable_evaluation("isPrimaryFlow", value=is_primary_flow, status="resolved")
    
    try:
        # Get the section node
        with neo_client._driver.session() as session:
            record = session.run(
                "MATCH (s:Section {sectionId:$sid}) RETURN s LIMIT 1",
                sid=start_section_id,
            ).single()
            
        if record is None:
            error_msg = f"Section '{start_section_id}' not found"
            debug_ctx.add_error(error_msg)
            debug_ctx.finalize_debug_info()
            
            return DebugExecutionResponse(
                sectionId=start_section_id,
                completed=False,
                requestVariables=ctx_dict,
                debug=debug_ctx.debug_info,
                errors=[error_msg]
            )
            
        section_node = record["s"]
        
        # Add initial traversal step
        debug_ctx.add_traversal_step(
            node_type="Section",
            node_id=start_section_id,
            node_data=dict(section_node)
        )
        
        # Perform the traversal with debug capture
        result = debug_traverse(section_node, debug_ctx, start_section_id)
        
        # Finalize debug information
        debug_ctx.finalize_debug_info()
        
        # Convert to debug response
        response = DebugExecutionResponse(
            sectionId=result.get("sectionId", start_section_id),
            question=result.get("question"),
            nextSectionId=result.get("nextSectionId"),
            createdNodeIds=result.get("createdNodeIds", []),
            completed=result.get("completed", False),
            requestVariables=result.get("requestVariables", ctx_dict),
            sourceNode=result.get("sourceNode"),
            vars=result.get("vars"),
            warnings=result.get("warnings", []),
            debug=debug_ctx.debug_info
        )
        
        return response
        
    except Exception as e:
        error_msg = f"Debug execution failed: {str(e)}"
        logger.exception(error_msg)
        debug_ctx.add_error(error_msg)
        debug_ctx.finalize_debug_info()
        
        return DebugExecutionResponse(
            sectionId=start_section_id,
            completed=False,
            requestVariables=ctx_dict,
            debug=debug_ctx.debug_info
        )


def debug_traverse(current_node, debug_ctx: DebugContext, section_id: str) -> Dict[str, Any]:
    """Enhanced traverse function with debug capture."""
    
    try:
        # Use existing traversal logic but capture debug info
        # This is a simplified version - in practice, you'd enhance the existing _traverse function
        
        # For now, we'll call the existing walk_section and capture what we can
        result = walk_section(section_id, debug_ctx.input_params)
        
        # Add some debug information based on the result
        if result.get("question"):
            debug_ctx.add_traversal_step(
                node_type="Question",
                node_id=result["question"].get("questionId", "unknown"),
                node_data=result["question"]
            )
            
        return result
        
    except Exception as e:
        error_msg = f"Traversal failed: {str(e)}"
        debug_ctx.add_error(error_msg)
        logger.exception(error_msg)
        
        return {
            "sectionId": section_id,
            "completed": False,
            "requestVariables": debug_ctx.input_params,
            "errors": [error_msg]
        }


def discover_tracks() -> List[Dict[str, Any]]:
    """Discover available tracks from Neo4j."""
    try:
        with neo_client._driver.session() as session:
            result = session.run("""
                MATCH (t:Track)
                OPTIONAL MATCH (t)-[:CONTAINS]->(s:Section)
                RETURN t.trackId as trackId, 
                       t.name as name, 
                       t.description as description,
                       collect(DISTINCT {
                           sectionId: s.sectionId,
                           name: s.name,
                           description: s.description
                       }) as sections
                ORDER BY t.name
            """)
            
            tracks = []
            for record in result:
                track = {
                    "trackId": record["trackId"],
                    "name": record["name"] or record["trackId"],
                    "description": record["description"],
                    "sections": [s for s in record["sections"] if s["sectionId"]]
                }
                tracks.append(track)
                
            return tracks
            
    except Exception as e:
        logger.exception(f"Failed to discover tracks: {e}")
        return []


def get_section_info(section_id: str) -> Optional[Dict[str, Any]]:
    """Get detailed information about a section."""
    try:
        with neo_client._driver.session() as session:
            result = session.run("""
                MATCH (s:Section {sectionId: $sectionId})
                OPTIONAL MATCH (s)-[:PRECEDES]->(q:Question)
                RETURN s.sectionId as sectionId,
                       s.name as name,
                       s.description as description,
                       s.inputParams as inputParams,
                       collect(DISTINCT {
                           questionId: q.questionId,
                           prompt: q.prompt,
                           dataType: q.dataType,
                           orderInForm: q.orderInForm
                       }) as questions
            """, sectionId=section_id)
            
            record = result.single()
            if record:
                return {
                    "sectionId": record["sectionId"],
                    "name": record["name"] or record["sectionId"],
                    "description": record["description"],
                    "inputParams": record["inputParams"] or [],
                    "questions": [q for q in record["questions"] if q["questionId"]]
                }
                
    except Exception as e:
        logger.exception(f"Failed to get section info: {e}")
        
    return None 