"""Pydantic contracts mirroring the domain objects.

Detailed fields will be added in later tasks.
"""
from pydantic import BaseModel
from typing import List, Optional, Any, Union, Literal, Dict
from enum import Enum


class VariableDef(BaseModel):
    name: str
    cypher: Optional[str] = None
    python: Optional[str] = None
    timeoutMs: Optional[int] = 500


# ---------------------------------------------------------------------------
# Shared helpers & mixins
# ---------------------------------------------------------------------------


class VersionedModel(BaseModel):
    """Mixin adding versioning metadata common to *Version nodes."""

    versionNumber: int
    active: bool = True

    class Config:
        orm_mode = True


def latest_active(items: List["VersionedModel"]) -> Optional["VersionedModel"]:
    """Return the latest *active* version from a collection."""

    active_items = [i for i in items if i.active]
    if not active_items:
        return None
    return max(active_items, key=lambda i: i.versionNumber)


# ---------------------------------------------------------------------------
# Edge types
# ---------------------------------------------------------------------------


class EdgeType(str, Enum):
    PRECEDES = "PRECEDES"
    TRIGGERS = "TRIGGERS"


class PrecedesEdge(BaseModel):
    type: Literal[EdgeType.PRECEDES] = EdgeType.PRECEDES
    fromId: str
    toId: str
    orderInForm: Optional[int] = None
    askWhen: Optional[str] = None
    variables: Optional[List[VariableDef]] = None
    sourceNode: Optional[str] = None

    class Config:
        orm_mode = True


class TriggersEdge(BaseModel):
    type: Literal[EdgeType.TRIGGERS] = EdgeType.TRIGGERS
    fromId: str
    toId: str
    askWhen: Optional[str] = None
    variables: Optional[List[VariableDef]] = None

    class Config:
        orm_mode = True


Edge = Union[PrecedesEdge, TriggersEdge]


# ---------------------------------------------------------------------------
# Question & Section
# ---------------------------------------------------------------------------


class Question(VersionedModel):
    questionId: str
    prompt: Optional[str]
    fieldId: Optional[str]
    dataType: Optional[str]
    exampleAnswer: Optional[str]
    orderInForm: Optional[int]
    variables: Optional[List[VariableDef]]


class Section(VersionedModel):
    sectionId: str
    name: Optional[str]
    stage: Optional[str]
    description: Optional[str]
    inputParams: Optional[List[str]]
    variables: Optional[List[VariableDef]]


# ---------------------------------------------------------------------------
# Actions
# ---------------------------------------------------------------------------


class ActionType(str, Enum):
    CREATE_PROPERTY_NODE = "CreatePropertyNode"
    GOTO_SECTION = "GotoSection"
    MARK_SECTION_COMPLETE = "MarkSectionComplete"


class ActionBase(VersionedModel):
    actionId: str
    actionType: ActionType
    variables: Optional[List[VariableDef]]


class CreatePropertyNodeAction(ActionBase):
    actionType: Literal[ActionType.CREATE_PROPERTY_NODE] = ActionType.CREATE_PROPERTY_NODE
    cypher: str
    returns: Optional[Dict[str, Any]]


class GotoSectionAction(ActionBase):
    actionType: Literal[ActionType.GOTO_SECTION] = ActionType.GOTO_SECTION
    nextSectionId: str
    props: Optional[Dict[str, Any]]


class MarkSectionCompleteAction(ActionBase):
    actionType: Literal[ActionType.MARK_SECTION_COMPLETE] = ActionType.MARK_SECTION_COMPLETE
    cypher: str


Action = Union[CreatePropertyNodeAction, GotoSectionAction, MarkSectionCompleteAction]


# ---------------------------------------------------------------------------
# Engine response (unchanged except orm_mode)
# ---------------------------------------------------------------------------


class EngineResponse(BaseModel):
    sectionId: str
    question: Optional[Any]
    nextSectionId: Optional[str]
    createdNodeIds: List[int] = []
    completed: bool = False
    requestVariables: dict
    sourceNode: Optional[Any]
    vars: Optional[Dict[str, Any]] = None
    warnings: Optional[List[Dict[str, str]]] = None

    class Config:
        orm_mode = True 