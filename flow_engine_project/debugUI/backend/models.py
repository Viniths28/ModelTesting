"""Pydantic models for the Flow Engine Debug Interface API."""

from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum

class ExecutionStatus(str, Enum):
    """Execution status enumeration."""
    SUCCESS = "success"
    ERROR = "error"
    TIMEOUT = "timeout"

class NodeType(str, Enum):
    """Node type enumeration for flow visualization."""
    SECTION = "Section"
    QUESTION = "Question" 
    ACTION = "Action"

class EdgeType(str, Enum):
    """Edge type enumeration for flow visualization."""
    PRECEDES = "PRECEDES"
    TRIGGERS = "TRIGGERS"
    HAS_SECTION = "HAS_SECTION"

class VariableStatus(str, Enum):
    """Variable evaluation status."""
    RESOLVED = "resolved"
    WAITING = "waiting"
    ERROR = "error"
    PENDING = "pending"

# Request Models
class DebugExecuteRequest(BaseModel):
    """Request model for executing a flow with debug information."""
    sectionId: str = Field(..., description="Section ID to start execution from")
    applicationId: str = Field(..., description="Application ID for context")
    applicantId: str = Field(..., description="Applicant ID for context")
    isPrimaryFlow: bool = Field(default=True, description="Whether this is a primary flow")
    isCoApplicant: Optional[str] = Field(default=None, description="Co-applicant flag")
    stepThrough: bool = Field(default=False, description="Whether to step through execution")
    executionName: Optional[str] = Field(default=None, description="Optional name for this execution")

class UpdateExecutionNameRequest(BaseModel):
    """Request model for updating execution name."""
    name: str = Field(..., description="New name for the execution")

class TrackAccessRequest(BaseModel):
    """Request model for recording track access."""
    trackId: str = Field(..., description="Track ID being accessed")
    trackName: str = Field(..., description="Track name for display")

# Response Models
class TraversalStep(BaseModel):
    """Single step in the traversal path."""
    step: int = Field(..., description="Step number in sequence")
    nodeType: NodeType = Field(..., description="Type of node")
    nodeId: str = Field(..., description="ID of the node")
    nodeName: Optional[str] = Field(default=None, description="Display name of the node")
    action: str = Field(..., description="Action performed (evaluated, executed, skipped)")
    timestamp: datetime = Field(..., description="When this step occurred")
    duration: int = Field(..., description="Duration in milliseconds")
    details: Optional[Dict[str, Any]] = Field(default=None, description="Additional step details")

class VariableEvaluation(BaseModel):
    """Variable evaluation result."""
    name: str = Field(..., description="Variable name")
    source: str = Field(..., description="Source (section, edge, action)")
    sourceId: str = Field(..., description="ID of the source node/edge")
    expression: str = Field(..., description="Cypher or Python expression")
    status: VariableStatus = Field(..., description="Evaluation status")
    value: Optional[Any] = Field(default=None, description="Resolved value")
    error: Optional[str] = Field(default=None, description="Error message if failed")
    duration: int = Field(..., description="Evaluation duration in milliseconds")
    dependencies: List[str] = Field(default_factory=list, description="Variable dependencies")

class ConditionEvaluation(BaseModel):
    """askWhen condition evaluation result."""
    edgeId: str = Field(..., description="Edge identifier")
    sourceNode: str = Field(..., description="Source node ID")
    targetNode: str = Field(..., description="Target node ID")
    askWhen: str = Field(..., description="askWhen expression")
    result: bool = Field(..., description="Evaluation result")
    variables: List[str] = Field(default_factory=list, description="Variables used in condition")
    duration: int = Field(..., description="Evaluation duration in milliseconds")
    error: Optional[str] = Field(default=None, description="Error message if evaluation failed")

class SourceNodeInfo(BaseModel):
    """Source node resolution information."""
    nodeId: Optional[str] = Field(default=None, description="Resolved node ID")
    expression: Optional[str] = Field(default=None, description="Source node expression")
    status: str = Field(..., description="Resolution status")
    value: Optional[Dict[str, Any]] = Field(default=None, description="Resolved node data")

class DebugInfo(BaseModel):
    """Comprehensive debug information for flow execution."""
    traversalPath: List[TraversalStep] = Field(default_factory=list, description="Complete traversal path")
    variableEvaluations: List[VariableEvaluation] = Field(default_factory=list, description="All variable evaluations")
    conditionEvaluations: List[ConditionEvaluation] = Field(default_factory=list, description="All condition evaluations")
    sourceNodeHistory: List[SourceNodeInfo] = Field(default_factory=list, description="Source node resolution history")
    totalDuration: int = Field(..., description="Total execution duration in milliseconds")
    errorCount: int = Field(default=0, description="Number of errors encountered")
    warningCount: int = Field(default=0, description="Number of warnings encountered")

class DebugExecuteResponse(BaseModel):
    """Enhanced response with debug information."""
    execution: Dict[str, Any] = Field(..., description="Standard flow engine response")
    debugInfo: DebugInfo = Field(..., description="Debug information")
    executionId: int = Field(..., description="Database ID for this execution")

class TrackInfo(BaseModel):
    """Track information for browser."""
    trackId: Optional[str] = Field(default=None, description="Track ID")
    trackName: str = Field(..., description="Track display name")
    internalId: str = Field(..., description="Neo4j internal ID")
    sections: List[Dict[str, Any]] = Field(default_factory=list, description="Sections in this track")

class SectionInfo(BaseModel):
    """Section information for browser."""
    sectionId: str = Field(..., description="Section ID")
    sectionName: str = Field(..., description="Section display name")
    internalId: str = Field(..., description="Neo4j internal ID")
    variables: List[str] = Field(default_factory=list, description="Variable names")

class ExecutionHistoryItem(BaseModel):
    """Execution history item."""
    id: int = Field(..., description="Database ID")
    name: Optional[str] = Field(default=None, description="User-defined name")
    section_id: str = Field(..., description="Section ID that was executed")
    payload: Dict[str, Any] = Field(..., description="Request payload")
    response: Dict[str, Any] = Field(..., description="Flow engine response")
    debug_info: Dict[str, Any] = Field(default_factory=dict, description="Debug information")
    created_at: datetime = Field(..., description="When execution occurred")
    duration_ms: int = Field(..., description="Execution duration")
    is_favorite: bool = Field(..., description="Whether marked as favorite")
    status: ExecutionStatus = Field(..., description="Execution status")
    error_message: Optional[str] = Field(default=None, description="Error message if failed")

class FavoriteItem(BaseModel):
    """Favorite execution item."""
    id: int = Field(..., description="Database ID")
    name: Optional[str] = Field(default=None, description="User-defined name")
    section_id: str = Field(..., description="Section ID")
    payload: Dict[str, Any] = Field(..., description="Request payload")
    created_at: datetime = Field(..., description="When execution was created")
    duration_ms: int = Field(..., description="Last execution duration")

class TrackUsageItem(BaseModel):
    """Track usage information."""
    track_id: str = Field(..., description="Track ID")
    track_name: str = Field(..., description="Track name")
    last_accessed: datetime = Field(..., description="Last access time")
    access_count: int = Field(..., description="Total access count")

# Standard API Response Models
class ApiResponse(BaseModel):
    """Standard API response wrapper."""
    success: bool = Field(..., description="Whether the request was successful")
    message: str = Field(..., description="Response message")
    data: Optional[Any] = Field(default=None, description="Response data")

class ErrorResponse(BaseModel):
    """Error response model."""
    success: bool = Field(default=False, description="Always false for errors")
    error: str = Field(..., description="Error type")
    message: str = Field(..., description="Error message")
    traceId: Optional[str] = Field(default=None, description="Trace ID for debugging") 