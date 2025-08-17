#!/usr/bin/env python3
"""
PostgreSQL storage for ADHD cognitive system.
Stores all state snapshots, decisions, and outcomes for pattern learning.
"""

import json
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
import asyncpg
from dataclasses import asdict
import os

logger = logging.getLogger(__name__)

class DatabaseStorage:
    """Persistent storage for cognitive system data."""
    
    def __init__(self, db_url: Optional[str] = None):
        self.db_url = db_url or os.getenv(
            "DATABASE_URL", 
            "postgresql://adhd_user:adhd_pass@localhost/adhd_db"
        )
        self.pool = None
        
    async def initialize(self):
        """Initialize database connection pool and create tables."""
        try:
            self.pool = await asyncpg.create_pool(
                self.db_url,
                min_size=2,
                max_size=10,
                command_timeout=60
            )
            
            # Create tables if they don't exist
            await self._create_tables()
            logger.info("✅ Database storage initialized")
            
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            self.pool = None
    
    async def _create_tables(self):
        """Create necessary tables for ADHD support system."""
        
        async with self.pool.acquire() as conn:
            # State snapshots table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS state_snapshots (
                    id SERIAL PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    timestamp TIMESTAMPTZ DEFAULT NOW(),
                    
                    -- User context
                    current_message TEXT,
                    emotional_indicators TEXT,
                    
                    -- Physical state (ALL FIT DATA!)
                    steps_today INTEGER,
                    steps_last_hour INTEGER,
                    calories_burned INTEGER,
                    distance_km FLOAT,
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
                    available_devices TEXT[],
                    music_playing BOOLEAN,
                    active_timers INTEGER,
                    
                    -- Complete state JSON for flexibility
                    full_state JSONB
                )
            """)
            
            # Claude decisions table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS claude_decisions (
                    id SERIAL PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    timestamp TIMESTAMPTZ DEFAULT NOW(),
                    state_snapshot_id INTEGER REFERENCES state_snapshots(id),
                    
                    -- Decision details
                    reasoning TEXT,
                    confidence FLOAT,
                    predicted_outcomes TEXT[],
                    
                    -- Actions taken
                    immediate_actions JSONB,
                    actions_executed TEXT[],
                    actions_failed TEXT[],
                    
                    -- Response
                    response_text TEXT,
                    response_mood TEXT
                )
            """)
            
            # Pattern tracking table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS adhd_patterns (
                    id SERIAL PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    timestamp TIMESTAMPTZ DEFAULT NOW(),
                    
                    pattern_type TEXT,  -- hyperfocus, procrastination, time_blindness, etc
                    context TEXT,
                    trigger_conditions JSONB,
                    
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
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS fitness_trends (
                    id SERIAL PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    date DATE NOT NULL,
                    
                    -- Daily totals
                    total_steps INTEGER,
                    total_calories INTEGER,
                    total_distance_km FLOAT,
                    total_active_minutes INTEGER,
                    
                    -- Sleep data (when available)
                    sleep_duration_hours FLOAT,
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
            
            # Create indexes separately (PostgreSQL doesn't support inline INDEX)
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_user_timestamp 
                ON state_snapshots (user_id, timestamp DESC);
                
                CREATE INDEX IF NOT EXISTS idx_physical_activity 
                ON state_snapshots (steps_today, active_minutes);
                
                CREATE INDEX IF NOT EXISTS idx_temporal 
                ON state_snapshots (day_part, weekday_weekend);
                
                CREATE INDEX IF NOT EXISTS idx_user_decisions 
                ON claude_decisions (user_id, timestamp DESC);
                
                CREATE INDEX IF NOT EXISTS idx_confidence 
                ON claude_decisions (confidence);
                
                CREATE INDEX IF NOT EXISTS idx_pattern_type 
                ON adhd_patterns (user_id, pattern_type);
                
                CREATE INDEX IF NOT EXISTS idx_effectiveness 
                ON adhd_patterns (effectiveness_rating DESC);
                
                CREATE INDEX IF NOT EXISTS idx_user_date 
                ON fitness_trends (user_id, date DESC);
            """)
            
            logger.info("✅ Database tables and indexes created/verified")
    
    async def store_state_snapshot(self, user_id: str, state: Any) -> Optional[int]:
        """Store a complete state snapshot and return its ID."""
        if not self.pool:
            logger.warning("Database not initialized, skipping state storage")
            return None
        
        try:
            # Convert state object to dict
            if hasattr(state, '__dict__'):
                state_dict = asdict(state) if hasattr(state, '__dataclass_fields__') else state.__dict__
            else:
                state_dict = state
            
            async with self.pool.acquire() as conn:
                snapshot_id = await conn.fetchval("""
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
                    ) VALUES (
                        $1, $2, $3, $4, $5, $6, $7, $8, $9, $10,
                        $11, $12, $13, $14, $15, $16, $17, $18, $19, $20, $21
                    ) RETURNING id
                """,
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
                    state_dict.get('available_devices', []),
                    state_dict.get('music_playing', False),
                    state_dict.get('active_timers', 0),
                    json.dumps(state_dict)
                )
                
                logger.info(f"✅ Stored state snapshot {snapshot_id} for user {user_id}")
                return snapshot_id
                
        except Exception as e:
            logger.error(f"Failed to store state snapshot: {e}")
            return None
    
    async def store_claude_decision(
        self, 
        user_id: str, 
        state_snapshot_id: Optional[int],
        decision: Dict[str, Any]
    ) -> Optional[int]:
        """Store Claude's decision and actions."""
        if not self.pool:
            return None
        
        try:
            async with self.pool.acquire() as conn:
                decision_id = await conn.fetchval("""
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
                    ) VALUES (
                        $1, $2, $3, $4, $5, $6, $7, $8, $9, $10
                    ) RETURNING id
                """,
                    user_id,
                    state_snapshot_id,
                    decision.get('reasoning'),
                    decision.get('confidence', 0.5),
                    decision.get('predicted_outcomes', []),
                    json.dumps(decision.get('immediate_actions', [])),
                    decision.get('actions_executed', []),
                    decision.get('actions_failed', []),
                    decision.get('response'),
                    decision.get('response_mood')
                )
                
                logger.info(f"✅ Stored Claude decision {decision_id}")
                return decision_id
                
        except Exception as e:
            logger.error(f"Failed to store Claude decision: {e}")
            return None
    
    async def log_adhd_pattern(
        self,
        user_id: str,
        pattern_type: str,
        context: str,
        physical_state: Dict[str, Any],
        intervention: Optional[str] = None
    ):
        """Log an ADHD pattern detection."""
        if not self.pool:
            return
        
        try:
            async with self.pool.acquire() as conn:
                await conn.execute("""
                    INSERT INTO adhd_patterns (
                        user_id,
                        pattern_type,
                        context,
                        trigger_conditions,
                        steps_at_detection,
                        calories_at_detection,
                        sitting_duration_at_detection,
                        intervention_used
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                """,
                    user_id,
                    pattern_type,
                    context,
                    json.dumps(physical_state),
                    physical_state.get('steps_today', 0),
                    physical_state.get('calories_burned', 0),
                    physical_state.get('sitting_duration_minutes', 0),
                    intervention
                )
                
                logger.info(f"✅ Logged {pattern_type} pattern for {user_id}")
                
        except Exception as e:
            logger.error(f"Failed to log pattern: {e}")
    
    async def get_user_patterns(
        self, 
        user_id: str, 
        pattern_type: Optional[str] = None,
        days: int = 7
    ) -> List[Dict]:
        """Get recent patterns for a user."""
        if not self.pool:
            return []
        
        try:
            async with self.pool.acquire() as conn:
                if pattern_type:
                    rows = await conn.fetch("""
                        SELECT * FROM adhd_patterns
                        WHERE user_id = $1 
                        AND pattern_type = $2
                        AND timestamp > NOW() - INTERVAL '%s days'
                        ORDER BY timestamp DESC
                    """, user_id, pattern_type, days)
                else:
                    rows = await conn.fetch("""
                        SELECT * FROM adhd_patterns
                        WHERE user_id = $1
                        AND timestamp > NOW() - INTERVAL '%s days'
                        ORDER BY timestamp DESC
                    """, user_id, days)
                
                return [dict(row) for row in rows]
                
        except Exception as e:
            logger.error(f"Failed to get patterns: {e}")
            return []
    
    async def update_daily_fitness(self, user_id: str, fitness_data: Dict):
        """Update or insert daily fitness trends."""
        if not self.pool:
            return
        
        try:
            today = datetime.now().date()
            
            async with self.pool.acquire() as conn:
                await conn.execute("""
                    INSERT INTO fitness_trends (
                        user_id,
                        date,
                        total_steps,
                        total_calories,
                        total_distance_km,
                        total_active_minutes
                    ) VALUES ($1, $2, $3, $4, $5, $6)
                    ON CONFLICT (user_id, date) 
                    DO UPDATE SET
                        total_steps = $3,
                        total_calories = $4,
                        total_distance_km = $5,
                        total_active_minutes = $6
                """,
                    user_id,
                    today,
                    fitness_data.get('steps_today', 0),
                    fitness_data.get('calories_burned', 0),
                    fitness_data.get('distance_km', 0.0),
                    fitness_data.get('active_minutes', 0)
                )
                
                logger.info(f"✅ Updated daily fitness for {user_id}")
                
        except Exception as e:
            logger.error(f"Failed to update daily fitness: {e}")
    
    async def close(self):
        """Close database connection pool."""
        if self.pool:
            await self.pool.close()
            logger.info("Database connection closed")

# Singleton instance
_db_storage = None

async def get_database_storage() -> DatabaseStorage:
    """Get or create the database storage singleton."""
    global _db_storage
    if _db_storage is None:
        _db_storage = DatabaseStorage()
        await _db_storage.initialize()
    return _db_storage