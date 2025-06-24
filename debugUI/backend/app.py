"""FastAPI application for Flow Engine Debug UI."""

import uuid
import time
from datetime import datetime
from typing import List, Dict, Any, Optional
from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from models import (
    DebugExecutionRequest,
    DebugExecutionResponse,
    TrackInfo,
    SectionInfo,
    ExecutionHistoryItem,
    FavoriteToggleRequest,
    UpdateNameRequest,
    TrackAccessRequest,
    HealthResponse
)
from database import db_manager
from debug_engine import debug_walk_section, discover_tracks, get_section_info

# Configure logging
logger.add("debug_ui.log", rotation="10 MB", level="INFO")

app = FastAPI(
    title="Flow Engine Debug UI",
    description="Comprehensive debugging interface for Flow Engine",
    version="1.0.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup_event():
    """Initialize database on startup."""
    await db_manager.initialize()
    logger.info("Debug UI backend started successfully")


@app.get("/api/health")
async def health_check() -> HealthResponse:
    """Health check endpoint."""
    try:
        # Test Neo4j connection
        from debug_engine import neo_client
        neo4j_connected = True
        try:
            with neo_client._driver.session() as session:
                session.run("RETURN 1").single()
        except Exception:
            neo4j_connected = False
            
        return HealthResponse(
            status="healthy",
            neo4j_connected=neo4j_connected,
            database_initialized=True,
            timestamp=datetime.now()
        )
    except Exception as e:
        logger.exception("Health check failed")
        return HealthResponse(
            status="unhealthy",
            neo4j_connected=False,
            database_initialized=False,
            timestamp=datetime.now()
        )


@app.post("/api/execute")
async def execute_debug_flow(request: DebugExecutionRequest) -> DebugExecutionResponse:
    """Execute flow with comprehensive debug capture."""
    trace_id = str(uuid.uuid4())
    start_time = time.time()
    
    logger.info(f"Debug execution started - {trace_id}: {request.dict()}")
    
    try:
        # Prepare context
        ctx_dict = {
            "sectionId": request.sectionId,
            "applicationId": request.applicationId,
            "applicantId": request.applicantId,
            "isPrimaryFlow": request.isPrimaryFlow
        }
        
        # Execute with debug capture
        response = debug_walk_section(
            request.sectionId, 
            ctx_dict, 
            request.isPrimaryFlow
        )
        
        # Add trace ID
        response.traceId = trace_id
        
        # Calculate execution time
        execution_time = time.time() - start_time
        
        # Save to database
        await db_manager.save_execution(
            section_id=request.sectionId,
            application_id=request.applicationId,
            applicant_id=request.applicantId,
            is_primary_flow=request.isPrimaryFlow,
            execution_time=execution_time,
            debug_info=response.debug.dict() if response.debug else None,
            response_data=response.dict(),
            status="completed" if not (response.debug and response.debug.errors) else "error"
        )
        
        logger.info(f"Debug execution completed - {trace_id}: {execution_time:.3f}s")
        return response
        
    except Exception as e:
        execution_time = time.time() - start_time
        error_msg = f"Debug execution failed: {str(e)}"
        logger.exception(f"Debug execution error - {trace_id}: {error_msg}")
        
        # Save error to database
        try:
            await db_manager.save_execution(
                section_id=request.sectionId,
                application_id=request.applicationId,
                applicant_id=request.applicantId,
                is_primary_flow=request.isPrimaryFlow,
                execution_time=execution_time,
                debug_info={"errors": [error_msg]},
                response_data={"error": error_msg},
                status="error"
            )
        except Exception:
            pass
            
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": error_msg,
                "traceId": trace_id
            }
        )


@app.get("/api/tracks")
async def get_tracks() -> List[TrackInfo]:
    """Get available tracks."""
    try:
        tracks_data = discover_tracks()
        return [TrackInfo(**track) for track in tracks_data]
    except Exception as e:
        logger.exception("Failed to get tracks")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get tracks: {str(e)}"
        )


@app.post("/api/tracks/access")
async def record_track_access(request: TrackAccessRequest):
    """Record track access for analytics."""
    try:
        await db_manager.record_track_access(request.track_id, request.section_id)
        return {"status": "success"}
    except Exception as e:
        logger.exception("Failed to record track access")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to record access: {str(e)}"
        )


@app.get("/api/tracks/recent")
async def get_recent_tracks():
    """Get recently accessed tracks."""
    try:
        return await db_manager.get_recent_tracks()
    except Exception as e:
        logger.exception("Failed to get recent tracks")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get recent tracks: {str(e)}"
        )


@app.get("/api/sections/{section_id}")
async def get_section_details(section_id: str) -> Optional[SectionInfo]:
    """Get detailed information about a section."""
    try:
        section_data = get_section_info(section_id)
        if section_data:
            return SectionInfo(**section_data)
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Section '{section_id}' not found"
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Failed to get section {section_id}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get section: {str(e)}"
        )


@app.get("/api/history")
async def get_execution_history(limit: int = 50) -> List[ExecutionHistoryItem]:
    """Get execution history."""
    try:
        history_data = await db_manager.get_execution_history(limit)
        return [ExecutionHistoryItem(**item) for item in history_data]
    except Exception as e:
        logger.exception("Failed to get execution history")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get history: {str(e)}"
        )


@app.get("/api/favorites")
async def get_favorites() -> List[ExecutionHistoryItem]:
    """Get favorite executions."""
    try:
        favorites_data = await db_manager.get_favorites()
        return [ExecutionHistoryItem(**item) for item in favorites_data]
    except Exception as e:
        logger.exception("Failed to get favorites")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get favorites: {str(e)}"
        )


@app.post("/api/favorites/toggle")
async def toggle_favorite(request: FavoriteToggleRequest):
    """Toggle favorite status of an execution."""
    try:
        new_status = await db_manager.toggle_favorite(request.execution_id)
        return {"status": "success", "is_favorite": new_status}
    except Exception as e:
        logger.exception("Failed to toggle favorite")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to toggle favorite: {str(e)}"
        )


@app.post("/api/executions/update-name")
async def update_execution_name(request: UpdateNameRequest):
    """Update custom name for an execution."""
    try:
        await db_manager.update_execution_name(request.execution_id, request.name)
        return {"status": "success"}
    except Exception as e:
        logger.exception("Failed to update execution name")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update name: {str(e)}"
        )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001) 