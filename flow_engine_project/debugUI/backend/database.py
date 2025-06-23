"""Database setup and operations for the Flow Engine Debug Interface."""

import sqlite3
import json
import aiosqlite
from datetime import datetime
from typing import List, Dict, Any, Optional
from pathlib import Path
from loguru import logger

# Database file path
DB_PATH = Path(__file__).parent / "debug.db"

class DateTimeEncoder(json.JSONEncoder):
    """Custom JSON encoder that handles datetime objects and falls back to str."""
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        # Fallback: stringify any non-serializable object (e.g., Neo4j Node)
        try:
            return super().default(obj)
        except TypeError:
            return str(obj)

class DatabaseManager:
    """Manages SQLite database operations for debug interface."""
    
    def __init__(self):
        self.db_path = str(DB_PATH)
    
    async def init_db(self):
        """Initialize the database with required tables."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS execution_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT,
                    section_id TEXT NOT NULL,
                    payload TEXT NOT NULL,  -- JSON
                    response TEXT NOT NULL, -- JSON
                    debug_info TEXT,        -- JSON debug information
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    duration_ms INTEGER,
                    is_favorite BOOLEAN DEFAULT FALSE,
                    status TEXT DEFAULT 'success', -- success, error, timeout
                    error_message TEXT
                )
            """)
            
            await db.execute("""
                CREATE TABLE IF NOT EXISTS track_usage (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    track_id TEXT NOT NULL,
                    track_name TEXT,
                    last_accessed TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    access_count INTEGER DEFAULT 1,
                    UNIQUE(track_id) ON CONFLICT REPLACE
                )
            """)
            
            await db.execute("""
                CREATE INDEX IF NOT EXISTS idx_execution_created_at 
                ON execution_history(created_at DESC)
            """)
            
            await db.execute("""
                CREATE INDEX IF NOT EXISTS idx_execution_section 
                ON execution_history(section_id)
            """)
            
            await db.commit()
            logger.info("Database initialized successfully")
    
    async def save_execution(
        self, 
        name: Optional[str],
        section_id: str,
        payload: Dict[str, Any],
        response: Dict[str, Any],
        debug_info: Dict[str, Any],
        duration_ms: int,
        status: str = 'success',
        error_message: Optional[str] = None
    ) -> int:
        """Save an execution to the history."""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("""
                INSERT INTO execution_history 
                (name, section_id, payload, response, debug_info, duration_ms, status, error_message)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                name,
                section_id,
                json.dumps(payload, cls=DateTimeEncoder),
                json.dumps(response, cls=DateTimeEncoder),
                json.dumps(debug_info, cls=DateTimeEncoder),
                duration_ms,
                status,
                error_message
            ))
            await db.commit()
            return cursor.lastrowid
    
    async def get_execution_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent execution history."""
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute("""
                SELECT id, name, section_id, payload, response, debug_info,
                       created_at, duration_ms, is_favorite, status, error_message
                FROM execution_history 
                ORDER BY created_at DESC 
                LIMIT ?
            """, (limit,)) as cursor:
                rows = await cursor.fetchall()
                
                return [
                    {
                        "id": row[0],
                        "name": row[1],
                        "section_id": row[2],
                        "payload": json.loads(row[3]),
                        "response": json.loads(row[4]),
                        "debug_info": json.loads(row[5]) if row[5] else {},
                        "created_at": row[6],
                        "duration_ms": row[7],
                        "is_favorite": bool(row[8]),
                        "status": row[9],
                        "error_message": row[10]
                    }
                    for row in rows
                ]
    
    async def get_favorites(self) -> List[Dict[str, Any]]:
        """Get favorite executions."""
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute("""
                SELECT id, name, section_id, payload, created_at, duration_ms
                FROM execution_history 
                WHERE is_favorite = TRUE
                ORDER BY name, created_at DESC
            """) as cursor:
                rows = await cursor.fetchall()
                
                return [
                    {
                        "id": row[0],
                        "name": row[1],
                        "section_id": row[2],
                        "payload": json.loads(row[3]),
                        "created_at": row[4],
                        "duration_ms": row[5]
                    }
                    for row in rows
                ]
    
    async def toggle_favorite(self, execution_id: int) -> bool:
        """Toggle favorite status of an execution."""
        async with aiosqlite.connect(self.db_path) as db:
            # Get current status
            async with db.execute("""
                SELECT is_favorite FROM execution_history WHERE id = ?
            """, (execution_id,)) as cursor:
                row = await cursor.fetchone()
                if not row:
                    return False
                
                new_status = not bool(row[0])
                
            # Update status
            await db.execute("""
                UPDATE execution_history SET is_favorite = ? WHERE id = ?
            """, (new_status, execution_id))
            await db.commit()
            return new_status
    
    async def update_execution_name(self, execution_id: int, name: str) -> bool:
        """Update the name of an execution."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                UPDATE execution_history SET name = ? WHERE id = ?
            """, (name, execution_id))
            await db.commit()
            return True
    
    async def record_track_access(self, track_id: str, track_name: str):
        """Record track access for usage tracking."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT OR REPLACE INTO track_usage (track_id, track_name, last_accessed, access_count)
                VALUES (?, ?, CURRENT_TIMESTAMP, 
                    COALESCE((SELECT access_count FROM track_usage WHERE track_id = ?), 0) + 1)
            """, (track_id, track_name, track_id))
            await db.commit()
    
    async def get_recent_tracks(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recently accessed tracks."""
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute("""
                SELECT track_id, track_name, last_accessed, access_count
                FROM track_usage 
                ORDER BY last_accessed DESC 
                LIMIT ?
            """, (limit,)) as cursor:
                rows = await cursor.fetchall()
                
                return [
                    {
                        "track_id": row[0],
                        "track_name": row[1],
                        "last_accessed": row[2],
                        "access_count": row[3]
                    }
                    for row in rows
                ]

# Global database manager instance
db_manager = DatabaseManager() 