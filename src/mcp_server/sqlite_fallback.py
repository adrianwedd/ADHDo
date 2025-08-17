#!/usr/bin/env python3
"""
SQLite fallback storage for when PostgreSQL is unavailable.
Provides same interface as PostgreSQL storage but with local SQLite.
"""

import json
import logging
import aiosqlite
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import asdict
import os

logger = logging.getLogger(__name__)

class SQLiteFallbackStorage:
    """SQLite fallback storage for cognitive system data."""
    
    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or os.path.expanduser("~/adhd_data.db")
        self.conn = None
        
    async def initialize(self):
        """Initialize SQLite database and create tables."""
        try:
            self.conn = await aiosqlite.connect(self.db_path)
            await self._create_tables()
            logger.info(f"✅ SQLite fallback initialized at {self.db_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize SQLite: {e}")
            return False
    
    async def _create_tables(self):
        """Create necessary tables for ADHD support system."""
        
        # State snapshots table
        await self.conn.execute("""
            CREATE TABLE IF NOT EXISTS state_snapshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                
                -- User context
                current_message TEXT,
                emotional_indicators TEXT,
                
                -- Physical state (ALL FIT DATA!)
                steps_today INTEGER,
                steps_last_hour INTEGER,
                calories_burned INTEGER,
                distance_km REAL,
                active_minutes INTEGER,
                last_movement_minutes INTEGER,
                sitting_duration_minutes INTEGER,
                
                -- Temporal state
                day_part TEXT,
                weekday_weekend TEXT,
                typical_energy TEXT,
                
                -- Task state
                current_focus TEXT,
                task_duration_minutes INTEGER,
                urgent_task_count INTEGER,
                overdue_task_count INTEGER,
                
                -- Environmental state
                available_devices TEXT,  -- JSON array
                music_playing INTEGER,  -- Boolean
                active_timers INTEGER,
                
                -- Complete state JSON for flexibility
                full_state TEXT  -- JSON
            )
        """)
        
        # Claude decisions table
        await self.conn.execute("""
            CREATE TABLE IF NOT EXISTS claude_decisions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                state_snapshot_id INTEGER REFERENCES state_snapshots(id),
                
                -- Decision details
                reasoning TEXT,
                confidence REAL,
                predicted_outcomes TEXT,  -- JSON array
                
                -- Actions taken
                immediate_actions TEXT,  -- JSON
                actions_executed TEXT,  -- JSON array
                actions_failed TEXT,  -- JSON array
                
                -- Response
                response_text TEXT,
                response_mood TEXT
            )
        """)
        
        # Pattern tracking table
        await self.conn.execute("""
            CREATE TABLE IF NOT EXISTS adhd_patterns (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                
                pattern_type TEXT,  -- hyperfocus, procrastination, time_blindness, etc
                context TEXT,
                trigger_conditions TEXT,  -- JSON
                
                -- Physical correlates
                steps_at_detection INTEGER,
                calories_at_detection INTEGER,
                sitting_duration_at_detection INTEGER,
                
                -- Intervention and outcome
                intervention_used TEXT,
                effectiveness_rating INTEGER,  -- 1-5 scale
                user_feedback TEXT
            )
        """)
        
        # Fitness trends table (aggregated daily)
        await self.conn.execute("""
            CREATE TABLE IF NOT EXISTS fitness_trends (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                date DATE NOT NULL,
                
                -- Daily totals
                total_steps INTEGER,
                total_calories INTEGER,
                total_distance_km REAL,
                total_active_minutes INTEGER,
                
                -- Sleep data (when available)
                sleep_duration_hours REAL,
                sleep_quality_score INTEGER,
                
                -- Patterns
                peak_activity_hour INTEGER,
                sedentary_periods INTEGER,
                hyperfocus_episodes INTEGER,
                
                -- Correlations
                focus_score INTEGER,  -- 1-10 subjective or calculated
                energy_crashes INTEGER,
                medication_effectiveness INTEGER,  -- 1-10
                
                UNIQUE(user_id, date)
            )
        """)
        
        # Create indexes
        await self.conn.execute("CREATE INDEX IF NOT EXISTS idx_user_timestamp ON state_snapshots (user_id, timestamp DESC)")
        await self.conn.execute("CREATE INDEX IF NOT EXISTS idx_user_decisions ON claude_decisions (user_id, timestamp DESC)")
        await self.conn.execute("CREATE INDEX IF NOT EXISTS idx_pattern_type ON adhd_patterns (user_id, pattern_type)")
        await self.conn.execute("CREATE INDEX IF NOT EXISTS idx_user_date ON fitness_trends (user_id, date DESC)")
        
        await self.conn.commit()
        logger.info("✅ SQLite tables created/verified")
    
    async def store_state_snapshot(self, user_id: str, state: Any) -> Optional[int]:
        """Store a complete state snapshot and return its ID."""
        if not self.conn:
            logger.warning("SQLite not initialized, skipping state storage")
            return None
        
        try:
            # Convert state object to dict
            if hasattr(state, '__dict__'):
                state_dict = asdict(state) if hasattr(state, '__dataclass_fields__') else state.__dict__
            else:
                state_dict = state
            
            cursor = await self.conn.execute("""
                INSERT INTO state_snapshots (
                    user_id,
                    current_message,
                    emotional_indicators,
                    steps_today,
                    steps_last_hour,
                    calories_burned,
                    distance_km,
                    active_minutes,
                    last_movement_minutes,
                    sitting_duration_minutes,
                    day_part,
                    weekday_weekend,
                    typical_energy,
                    current_focus,
                    task_duration_minutes,
                    urgent_task_count,
                    overdue_task_count,
                    available_devices,
                    music_playing,
                    active_timers,
                    full_state
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                user_id,
                state_dict.get('current_message'),
                state_dict.get('emotional_indicators'),
                state_dict.get('steps_today', 0),
                state_dict.get('steps_last_hour', 0),
                state_dict.get('calories_burned', 0),
                state_dict.get('distance_km', 0.0),
                state_dict.get('active_minutes', 0),
                state_dict.get('last_movement_minutes', 0),
                state_dict.get('sitting_duration_minutes', 0),
                state_dict.get('day_part'),
                state_dict.get('weekday_weekend'),
                state_dict.get('typical_energy_now'),
                state_dict.get('current_focus'),
                state_dict.get('task_duration_minutes', 0),
                len(state_dict.get('urgent_tasks', [])),
                len(state_dict.get('overdue_tasks', [])),
                json.dumps(state_dict.get('available_devices', [])),
                1 if state_dict.get('music_playing', False) else 0,
                state_dict.get('active_timers', 0),
                json.dumps(state_dict)
            ))
            
            await self.conn.commit()
            snapshot_id = cursor.lastrowid
            
            logger.info(f"✅ Stored state snapshot {snapshot_id} in SQLite")
            return snapshot_id
            
        except Exception as e:
            logger.error(f"Failed to store state snapshot in SQLite: {e}")
            return None
    
    async def store_claude_decision(
        self, 
        user_id: str, 
        state_snapshot_id: Optional[int],
        decision: Dict[str, Any]
    ) -> Optional[int]:
        """Store Claude's decision and actions."""
        if not self.conn:
            return None
        
        try:
            cursor = await self.conn.execute("""
                INSERT INTO claude_decisions (
                    user_id,
                    state_snapshot_id,
                    reasoning,
                    confidence,
                    predicted_outcomes,
                    immediate_actions,
                    actions_executed,
                    actions_failed,
                    response_text,
                    response_mood
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                user_id,
                state_snapshot_id,
                decision.get('reasoning'),
                decision.get('confidence', 0.5),
                json.dumps(decision.get('predicted_outcomes', [])),
                json.dumps(decision.get('immediate_actions', [])),
                json.dumps(decision.get('actions_executed', [])),
                json.dumps(decision.get('actions_failed', [])),
                decision.get('response'),
                decision.get('response_mood')
            ))
            
            await self.conn.commit()
            decision_id = cursor.lastrowid
            
            logger.info(f"✅ Stored Claude decision {decision_id} in SQLite")
            return decision_id
            
        except Exception as e:
            logger.error(f"Failed to store Claude decision in SQLite: {e}")
            return None
    
    async def close(self):
        """Close SQLite connection."""
        if self.conn:
            await self.conn.close()
            logger.info("SQLite connection closed")

# Unified storage interface that tries PostgreSQL first, then SQLite
async def get_persistent_storage():
    """Get storage backend - PostgreSQL if available, otherwise SQLite."""
    try:
        # Try PostgreSQL first
        from .database_storage import get_database_storage
        db = await get_database_storage()
        if db and db.pool:
            logger.info("Using PostgreSQL for storage")
            return db
    except Exception as e:
        logger.warning(f"PostgreSQL not available: {e}")
    
    # Fallback to SQLite
    logger.info("Falling back to SQLite for storage")
    sqlite_db = SQLiteFallbackStorage()
    await sqlite_db.initialize()
    return sqlite_db