"""Pydantic models for debug UI API."""

from typing import List, Dict, Any, Optional, Union
from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum


class DebugExecutionRequest(BaseModel):
    """Request model for debug execution with isPrimaryFlow parameter."""
    sectionId: str = Field(..., description="Section ID to start traversal from")
    applicationId: str = Field(..., description="Application ID")
    applicantId: str = Field(..., description="Applicant ID")
    isPrimaryFlow: bool = Field(True, description="Whether this is a primary flow execution")


class VariableEvaluation(BaseModel):
    """Variable evaluation debug information."""
    name: str
    status: str  # resolved, waiting, error, pending
    expression: Optional[str] = None
    value: Any = None
    error: Optional[str] = None
    dependencies: List[str] = []
    evaluation_time: Optional[float] = None


class ConditionEvaluation(BaseModel):
    """Condition evaluation debug information."""
    expression: str
    result: bool
    variables_used: List[str] = []
    evaluation_time: Optional[float] = None
    error: Optional[str] = None


class SourceNodeResolution(BaseModel):
    """Source node resolution debug information."""
    expression: str
    resolved_value: Any = None
    node_id: Optional[str] = None
    error: Optional[str] = None
    resolution_time: Optional[float] = None


class TraversalStep(BaseModel):
    """Single step in traversal path."""
    step_number: int
    node_type: str  # Section, Question, Action
    node_id: str
    node_data: Dict[str, Any]
    edge_type: Optional[str] = None  # PRECEDES, TRIGGERS
    edge_data: Optional[Dict[str, Any]] = None
    execution_time: Optional[float] = None
    variables_at_step: Dict[str, VariableEvaluation] = {}
    conditions_evaluated: List[ConditionEvaluation] = []
    source_node_resolution: Optional[SourceNodeResolution] = None


class DebugInformation(BaseModel):
    """Comprehensive debug information."""
    traversal_path: List[TraversalStep] = []
    total_execution_time: Optional[float] = None
    variable_evaluations: Dict[str, VariableEvaluation] = {}
    condition_evaluations: List[ConditionEvaluation] = []
    source_node_resolutions: List[SourceNodeResolution] = []
    errors: List[str] = []
    warnings: List[str] = []


class DebugExecutionResponse(BaseModel):
    """Enhanced response with debug information."""
    sectionId: str
    question: Optional[Dict[str, Any]] = None
    nextSectionId: Optional[str] = None
    createdNodeIds: List[int] = []
    completed: bool = False
    requestVariables: Dict[str, Any]
    sourceNode: Optional[Dict[str, Any]] = None
    vars: Optional[Dict[str, Any]] = None
    warnings: Optional[List[str]] = None
    traceId: Optional[str] = None
    debug: Optional[DebugInformation] = None


class TrackInfo(BaseModel):
    """Track information."""
    trackId: str
    name: str
    description: Optional[str] = None
    sections: List[Dict[str, Any]] = []


class SectionInfo(BaseModel):
    """Section information."""
    sectionId: str
    name: str
    description: Optional[str] = None
    inputParams: List[str] = []
    questions: List[Dict[str, Any]] = []


class ExecutionHistoryItem(BaseModel):
    """Execution history item."""
    id: int
    section_id: str
    application_id: Optional[str] = None
    applicant_id: Optional[str] = None
    is_primary_flow: bool = True
    execution_time: Optional[float] = None
    debug_info: Optional[Dict[str, Any]] = None
    response_data: Optional[Dict[str, Any]] = None
    status: str = "completed"
    is_favorite: bool = False
    custom_name: Optional[str] = None
    created_at: datetime


class FavoriteToggleRequest(BaseModel):
    """Request to toggle favorite status."""
    execution_id: int


class UpdateNameRequest(BaseModel):
    """Request to update execution name."""
    execution_id: int
    name: str


class TrackAccessRequest(BaseModel):
    """Request to record track access."""
    track_id: str
    section_id: Optional[str] = None


class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    neo4j_connected: bool
    database_initialized: bool
    timestamp: datetime 