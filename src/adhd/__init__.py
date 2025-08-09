"""
Advanced ADHD Support Module for MCP ADHD Server.

This module provides comprehensive ADHD support through:
- Real-time behavioral pattern recognition
- Personalized user profiling and adaptation
- Executive function scaffolding tools
- Machine learning-powered insights
- Intelligent interface adaptation
- Crisis detection and intervention

The module is designed to augment rather than replace human executive function,
providing scaffolding that empowers users while respecting neurodiversity
principles and user autonomy.

Key Components:
- pattern_engine: Real-time ADHD pattern recognition
- user_profile: Personalized profiling and adaptation
- adaptation_engine: Intelligent system adaptation
- executive_function: Executive function support tools
- ml_pipeline: Privacy-preserving machine learning
- enhanced_cognitive_loop: Integration layer

Usage:
    from adhd import enhanced_cognitive_loop
    
    result = await enhanced_cognitive_loop.process_user_input(
        user_id="user123",
        user_input="I need help with this task",
        task_focus="Write weekly report"
    )

All components are designed to work together while remaining modular
and independently testable. The system maintains backward compatibility
with existing MCP server functionality while providing significant
enhancements for ADHD users.
"""

__version__ = "1.0.0"
__author__ = "CODEFORGE"

# Core exports for easy importing
from .enhanced_cognitive_loop import enhanced_cognitive_loop, EnhancedCognitiveLoopResult
from .pattern_engine import get_pattern_engine, PatternType, PatternSeverity
from .user_profile import profile_manager
from .adaptation_engine import adaptation_engine
from .executive_function import (
    task_breakdown_engine, 
    context_switching_assistant,
    working_memory_support,
    procrastination_intervenor
)
from .ml_pipeline import ml_pipeline

__all__ = [
    "enhanced_cognitive_loop",
    "EnhancedCognitiveLoopResult",
    "get_pattern_engine", 
    "PatternType",
    "PatternSeverity",
    "profile_manager",
    "adaptation_engine",
    "task_breakdown_engine",
    "context_switching_assistant", 
    "working_memory_support",
    "procrastination_intervenor",
    "ml_pipeline"
]