"""SQLite database manager for debug UI."""

import sqlite3
import json
import asyncio
from datetime import datetime
from typing import List, Dict, Any, Optional
from loguru import logger
import aiosqlite


class DatabaseManager:
    """Manages SQLite database for debug UI."""
    
    def __init__(self, db_path: str = "debug_ui.db"):
        self.db_path = db_path
        
    async def initialize(self):
        """Initialize database tables."""
        async with aiosqlite.connect(self.db_path) as db:
            # Execution history table
            await db.execute("""
                CREATE TABLE IF NOT EXISTS execution_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    section_id TEXT NOT NULL,
                    application_id TEXT,
                    applicant_id TEXT,
                    is_primary_flow BOOLEAN DEFAULT TRUE,
                    execution_time REAL,
                    debug_info TEXT,
                    response_data TEXT,
                    status TEXT DEFAULT 'completed',
                    is_favorite BOOLEAN DEFAULT FALSE,
                    custom_name TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Track usage table
            await db.execute("""
                CREATE TABLE IF NOT EXISTS track_usage (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    track_id TEXT NOT NULL,
                    section_id TEXT,
                    access_count INTEGER DEFAULT 1,
                    last_accessed TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(track_id, section_id)
                )
            """)
            
            await db.commit()
            
    async def save_execution(self, 
                           section_id: str,
                           application_id: str = None,
                           applicant_id: str = None,
                           is_primary_flow: bool = True,
                           execution_time: float = None,
                           debug_info: Dict = None,
                           response_data: Dict = None,
                           status: str = "completed") -> int:
        """Save execution to history."""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("""
                INSERT INTO execution_history 
                (section_id, application_id, applicant_id, is_primary_flow, 
                 execution_time, debug_info, response_data, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                section_id, application_id, applicant_id, is_primary_flow,
                execution_time, 
                json.dumps(debug_info) if debug_info else None,
                json.dumps(response_data) if response_data else None,
                status
            ))
            await db.commit()
            return cursor.lastrowid
            
    async def get_execution_history(self, limit: int = 50) -> List[Dict]:
        """Get execution history."""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("""
                SELECT * FROM execution_history 
                ORDER BY created_at DESC 
                LIMIT ?
            """, (limit,)) as cursor:
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]
                
    async def get_favorites(self) -> List[Dict]:
        """Get favorite executions."""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("""
                SELECT * FROM execution_history 
                WHERE is_favorite = TRUE
                ORDER BY created_at DESC
            """) as cursor:
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]
                
    async def toggle_favorite(self, execution_id: int) -> bool:
        """Toggle favorite status."""
        async with aiosqlite.connect(self.db_path) as db:
            # Get current status
            async with db.execute("""
                SELECT is_favorite FROM execution_history WHERE id = ?
            """, (execution_id,)) as cursor:
                row = await cursor.fetchone()
                if not row:
                    return False
                    
            new_status = not bool(row[0])
            await db.execute("""
                UPDATE execution_history 
                SET is_favorite = ? 
                WHERE id = ?
            """, (new_status, execution_id))
            await db.commit()
            return new_status
            
    async def update_execution_name(self, execution_id: int, name: str):
        """Update custom name for execution."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                UPDATE execution_history 
                SET custom_name = ? 
                WHERE id = ?
            """, (name, execution_id))
            await db.commit()
            
    async def record_track_access(self, track_id: str, section_id: str = None):
        """Record track access for analytics."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT OR REPLACE INTO track_usage 
                (track_id, section_id, access_count, last_accessed)
                VALUES (
                    ?, ?, 
                    COALESCE((SELECT access_count FROM track_usage WHERE track_id = ? AND section_id = ?), 0) + 1,
                    CURRENT_TIMESTAMP
                )
            """, (track_id, section_id, track_id, section_id))
            await db.commit()
            
    async def get_recent_tracks(self, limit: int = 10) -> List[Dict]:
        """Get recently accessed tracks."""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("""
                SELECT track_id, section_id, access_count, last_accessed
                FROM track_usage 
                ORDER BY last_accessed DESC 
                LIMIT ?
            """, (limit,)) as cursor:
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]


# Global database manager instance
db_manager = DatabaseManager() 