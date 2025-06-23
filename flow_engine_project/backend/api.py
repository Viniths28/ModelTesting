"""HTTP API surface for Flow Builder Engine."""

from __future__ import annotations

import uuid
from typing import Any, Dict

from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, Field
from loguru import logger

from flow_engine import run_section
from flow_engine.logging import configure_logging, trace_id_var, ENGINE_CALLS_TOTAL, ENGINE_CALL_ERRORS, ENGINE_CALL_DURATION
from flow_engine.errors import FlowError

configure_logging()

app = FastAPI(title="Flow Builder Engine", version="1.0.0")


class NextQuestionRequest(BaseModel):
    sectionId: str = Field(..., description="Section ID to start traversal from")
    applicationId: str
    applicantId: str
    isPrimaryFlow: bool = Field(
        default=True,
        description="True for primary applicant flow, False for co-applicant flow.",
    )


@app.post("/v1/api/next_question_flow")
async def next_question_flow(payload: NextQuestionRequest):  # noqa: D401
    """Resolve the next question or action for the given section context."""

    trace_id = str(uuid.uuid4())
    trace_id_var.set(trace_id)
    logger.bind(traceId=trace_id).info("Incoming request: {}", payload.dict())

    ENGINE_CALLS_TOTAL.inc()

    try:
        with ENGINE_CALL_DURATION.time():
            response: Dict[str, Any] = run_section(
                payload.sectionId,
                applicationId=payload.applicationId,
                applicantId=payload.applicantId,
                sectionId=payload.sectionId,
                isPrimaryFlow=payload.isPrimaryFlow,
            )
        response["traceId"] = trace_id
        return response
    except FlowError as exc:
        ENGINE_CALL_ERRORS.inc()
        logger.warning("Engine domain error: {}", exc, traceId=trace_id)
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "errorType": exc.__class__.__name__,
                "message": str(exc),
                "traceId": trace_id,
            },
        )
    except Exception as exc:
        ENGINE_CALL_ERRORS.inc()
        logger.exception("Engine error: {}", exc, traceId=trace_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "errorType": exc.__class__.__name__,
                "message": str(exc),
                "traceId": trace_id,
            },
        )
    finally:
        trace_id_var.set(None) 