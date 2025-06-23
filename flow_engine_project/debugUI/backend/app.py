"""FastAPI application for Flow Engine Debug Interface."""

import time
import sys
import os
from typing import List, Dict, Any, Optional
import uuid
import json
from datetime import datetime
import pathlib, importlib
from pathlib import Path

from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from loguru import logger
from contextlib import asynccontextmanager

# Ensure flow_engine package is importable regardless of deployment location
try:
    import flow_engine  # noqa: F401
except ModuleNotFoundError:  # pragma: no cover
    _base_dir = pathlib.Path(__file__).resolve()
    # Potential locations relative to the debugUI/backend directory
    _candidates = [
        _base_dir.parents[2] / "backend",                    # ../.. / backend (flow_engine_project structure)
        _base_dir.parents[1] / "backend",                    # .. / backend
        _base_dir.parents[3] / "flow_engine_project" / "backend",  # ../../flow_engine_project/backend when debugUI at repo root
    ]
    for _cand in _candidates:
        if (_cand / "flow_engine").exists():
            sys.path.append(str(_cand))
            break
    try:
        importlib.import_module("flow_engine")
    except ModuleNotFoundError as exc:
        raise ModuleNotFoundError(
            "flow_engine package not found. Ensure the main application backend is present "
            "and its path is added to PYTHONPATH. Checked candidates: " + ", ".join(str(c) for c in _candidates)
        ) from exc

from flow_engine.neo import neo_client

try:
    from .database import db_manager
    from .debug_engine import debug_walk_section
    from .models import (
        DebugExecuteRequest, DebugExecuteResponse, UpdateExecutionNameRequest, TrackAccessRequest,
        ApiResponse, ErrorResponse, TrackInfo, SectionInfo, ExecutionHistoryItem, 
        FavoriteItem, TrackUsageItem, ExecutionStatus, DebugInfo
    )
except ImportError:  # Running as a stand-alone script
    from database import db_manager
    from debug_engine import debug_walk_section
    from models import (
        DebugExecuteRequest, DebugExecuteResponse, UpdateExecutionNameRequest, TrackAccessRequest,
        ApiResponse, ErrorResponse, TrackInfo, SectionInfo, ExecutionHistoryItem, 
        FavoriteItem, TrackUsageItem, ExecutionStatus, DebugInfo
    )

# ---------------------------------------------------------------------------
# Persistent log file configuration (debugUI backend)
# Creates ./logs folder next to this file and writes rotating compressed logs
# ---------------------------------------------------------------------------
_log_dir = Path(__file__).parent / "logs"
_log_dir.mkdir(exist_ok=True)

# Avoid duplicate sinks if code reloads (set a flag once we add it)
if not getattr(logger, "_debugui_file_sink_added", False):
    logger.add(
        _log_dir / "debugui_{time}.log",
        rotation="50 MB",
        retention="14 days",
        compression="zip",
        enqueue=True,
        level=os.getenv("LOG_LEVEL", "INFO"),
        serialize=False,
    )
    logger._debugui_file_sink_added = True  # type: ignore[attr-defined]

# Lifespan context manager for startup/shutdown
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handle startup and shutdown events."""
    # Startup
    logger.info("Initializing debug interface database...")
    await db_manager.init_db()
    logger.info("Debug interface ready!")
    yield
    # Shutdown
    logger.info("Debug interface shutting down...")

# Create FastAPI app
app = FastAPI(
    title="Flow Engine Debug Interface",
    description="Comprehensive debugging interface for the Flow Engine with execution visualization",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5667", "http://localhost:3000"],  # React dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Error handler
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler for unhandled errors."""
    trace_id = str(uuid.uuid4())
    logger.exception("Unhandled error in debug interface", trace_id=trace_id)
    
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error": "InternalServerError",
            "message": str(exc),
            "traceId": trace_id
        }
    )

# Health check
@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

# Track and section discovery endpoints
@app.get("/api/tracks", response_model=List[TrackInfo])
async def get_tracks():
    """Get all tracks with their sections."""
    try:
        with neo_client._driver.session() as session:
            # Get all tracks (looking for nodes that have sections)
            result = session.run("""
                MATCH (t:Track)
                OPTIONAL MATCH (t)-[:HAS_SECTION]->(s:Section)
                RETURN t.trackId as trackId, t.name as trackName, elementId(t) as internalId,
                       collect({
                           sectionId: s.sectionId,
                           sectionName: s.name,
                           internalId: elementId(s),
                           variables: s.variables
                       }) as sections
                ORDER BY t.name
            """)
            
            tracks = []
            for record in result:
                # Parse variables for each section
                sections = []
                for section in record["sections"]:
                    if section["sectionId"]:  # Filter out null sections
                        variables = []
                        if section["variables"]:
                            try:
                                vars_data = json.loads(section["variables"])
                                variables = [v["name"] for v in vars_data]
                            except:
                                pass
                        
                        sections.append({
                            "sectionId": section["sectionId"],
                            "sectionName": section["sectionName"],
                            "internalId": section["internalId"],
                            "variables": variables
                        })
                
                tracks.append(TrackInfo(
                    trackId=record["trackId"],
                    trackName=record["trackName"] or "Unnamed Track",
                    internalId=record["internalId"],
                    sections=sections
                ))
            
            # Also look for standalone sections (sections with a trackId but not connected via HAS_SECTION)
            result = session.run("""
                MATCH (s:Section)
                WHERE s.trackId IS NOT NULL
                AND NOT EXISTS((:Track)-[:HAS_SECTION]->(s))
                RETURN DISTINCT s.trackId as trackId, 
                       collect({
                           sectionId: s.sectionId,
                           sectionName: s.name,
                           internalId: elementId(s),
                           variables: s.variables
                       }) as sections
            """)
            
            for record in result:
                sections = []
                for section in record["sections"]:
                    variables = []
                    if section["variables"]:
                        try:
                            vars_data = json.loads(section["variables"])
                            variables = [v["name"] for v in vars_data]
                        except:
                            pass
                    
                    sections.append({
                        "sectionId": section["sectionId"],
                        "sectionName": section["sectionName"],
                        "internalId": section["internalId"],
                        "variables": variables
                    })
                
                tracks.append(TrackInfo(
                    trackId=record["trackId"],
                    trackName="Standalone Sections",
                    internalId="standalone",
                    sections=sections
                ))
            
        return tracks
        
    except Exception as exc:
        logger.exception("Failed to fetch tracks")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch tracks: {str(exc)}"
        )

@app.post("/api/tracks/access")
async def record_track_access(request: TrackAccessRequest):
    """Record track access for usage tracking."""
    try:
        await db_manager.record_track_access(request.trackId, request.trackName)
        return ApiResponse(success=True, message="Track access recorded")
    except Exception as exc:
        logger.exception("Failed to record track access")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to record track access: {str(exc)}"
        )

@app.get("/api/tracks/recent", response_model=List[TrackUsageItem])
async def get_recent_tracks():
    """Get recently accessed tracks."""
    try:
        recent_tracks = await db_manager.get_recent_tracks()
        return [TrackUsageItem(**track) for track in recent_tracks]
    except Exception as exc:
        logger.exception("Failed to fetch recent tracks")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch recent tracks: {str(exc)}"
        )

# Debug execution endpoints
@app.post("/api/execute", response_model=DebugExecuteResponse)
async def debug_execute_flow(request: DebugExecuteRequest):
    """Execute a flow with comprehensive debug information capture."""
    start_time = time.perf_counter()
    trace_id = str(uuid.uuid4())
    
    try:
        logger.info("Debug execution started", 
                   section_id=request.sectionId, 
                   trace_id=trace_id)
        
        # Prepare context dictionary
        ctx_dict = {
            "sectionId": request.sectionId,
            "applicationId": request.applicationId,
            "applicantId": request.applicantId,
            "isPrimaryFlow": request.isPrimaryFlow,
        }
        
        if request.isCoApplicant:
            ctx_dict["isCoApplicant"] = request.isCoApplicant
        
        # Execute with debug information
        response, debug_info = debug_walk_section(request.sectionId, ctx_dict)
        
        # Calculate duration
        duration_ms = int((time.perf_counter() - start_time) * 1000)
        
        # Save to database
        execution_id = await db_manager.save_execution(
            name=request.executionName,
            section_id=request.sectionId,
            payload=request.dict(),
            response=response,
            debug_info=debug_info.dict(),
            duration_ms=duration_ms,
            status=ExecutionStatus.SUCCESS.value
        )
        
        logger.info("Debug execution completed", 
                   execution_id=execution_id,
                   duration_ms=duration_ms,
                   trace_id=trace_id)
        
        return DebugExecuteResponse(
            execution=response,
            debugInfo=debug_info,
            executionId=execution_id
        )
        
    except Exception as exc:
        duration_ms = int((time.perf_counter() - start_time) * 1000)
        
        # Save error to database
        try:
            await db_manager.save_execution(
                name=request.executionName,
                section_id=request.sectionId,
                payload=request.dict(),
                response={"error": str(exc)},
                debug_info={"error": str(exc)},
                duration_ms=duration_ms,
                status=ExecutionStatus.ERROR.value,
                error_message=str(exc)
            )
        except:
            pass  # Don't fail if we can't save the error
        
        logger.exception("Debug execution failed", 
                        section_id=request.sectionId,
                        trace_id=trace_id)
        
        raise HTTPException(
            status_code=500,
            detail={
                "error": "ExecutionError",
                "message": str(exc),
                "traceId": trace_id
            }
        )

# Execution history endpoints
@app.get("/api/history", response_model=List[ExecutionHistoryItem])
async def get_execution_history(limit: int = 50):
    """Get execution history."""
    try:
        history = await db_manager.get_execution_history(limit)
        return [ExecutionHistoryItem(**item) for item in history]
    except Exception as exc:
        logger.exception("Failed to fetch execution history")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch execution history: {str(exc)}"
        )

@app.get("/api/favorites", response_model=List[FavoriteItem])
async def get_favorites():
    """Get favorite executions."""
    try:
        favorites = await db_manager.get_favorites()
        return [FavoriteItem(**item) for item in favorites]
    except Exception as exc:
        logger.exception("Failed to fetch favorites")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch favorites: {str(exc)}"
        )

@app.post("/api/history/{execution_id}/favorite")
async def toggle_favorite(execution_id: int):
    """Toggle favorite status of an execution."""
    try:
        new_status = await db_manager.toggle_favorite(execution_id)
        return ApiResponse(
            success=True, 
            message=f"Execution {'added to' if new_status else 'removed from'} favorites",
            data={"is_favorite": new_status}
        )
    except Exception as exc:
        logger.exception("Failed to toggle favorite")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to toggle favorite: {str(exc)}"
        )

@app.patch("/api/history/{execution_id}/name")
async def update_execution_name(execution_id: int, request: UpdateExecutionNameRequest):
    """Update the name of an execution."""
    try:
        await db_manager.update_execution_name(execution_id, request.name)
        return ApiResponse(success=True, message="Execution name updated")
    except Exception as exc:
        logger.exception("Failed to update execution name")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to update execution name: {str(exc)}"
        )

# Utility endpoints
@app.get("/api/sections/{section_id}/info", response_model=SectionInfo)
async def get_section_info(section_id: str):
    """Get detailed information about a specific section."""
    try:
        with neo_client._driver.session() as session:
            result = session.run("""
                MATCH (s:Section {sectionId: $sectionId})
                RETURN s.sectionId as sectionId, s.name as sectionName, 
                       elementId(s) as internalId, s.variables as variables
            """, sectionId=section_id)
            
            record = result.single()
            if not record:
                raise HTTPException(
                    status_code=404,
                    detail=f"Section '{section_id}' not found"
                )
            
            variables = []
            if record["variables"]:
                try:
                    vars_data = json.loads(record["variables"])
                    variables = [v["name"] for v in vars_data]
                except:
                    pass
            
            return SectionInfo(
                sectionId=record["sectionId"],
                sectionName=record["sectionName"] or "Unnamed Section",
                internalId=record["internalId"],
                variables=variables
            )
            
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Failed to fetch section info")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch section info: {str(exc)}"
        )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8005) 