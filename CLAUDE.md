# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**MCP ADHD Server** - A Meta-Cognitive Protocol server for ADHD executive function support. This is a FastAPI-based system that implements a recursive, context-aware AI orchestration system designed specifically for neurodivergent users.

The project implements the **Meta-Cognitive Protocol (MCP)** architecture - a universal framework for building cognitive-aware AI systems with safety-first design, circuit breaker psychology, and recursive learning capabilities.

## Development Commands

### Server Management
```bash
# Start development server
python -m uvicorn src.mcp_server.main:app --reload

# Start server with specific host/port
uvicorn src.mcp_server.main:app --host 0.0.0.0 --port 8000 --reload

# Run server directly
python src/mcp_server/main.py
```

### Testing
```bash
# Run all tests
pytest tests/

# Run tests with coverage
pytest --cov=src tests/

# Run specific test file
pytest tests/test_specific.py
```

### Code Quality
```bash
# Format code
black src/ tests/

# Lint code
ruff check src/ tests/

# Type checking
mypy src/
```

### Environment Setup
```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Install development dependencies
pip install -e ".[dev]"

# Configure environment
cp .env.example .env
# Edit .env with your API keys and configuration
```

## Core Architecture

### The Cognitive Loop (`src/mcp_server/cognitive_loop.py`)
The heart of the system - implements the recursive meta-cognitive protocol:
1. **Context Assembly** - Builds contextual frames while managing cognitive load
2. **Safety Assessment** - Crisis detection with hard-coded responses
3. **Circuit Breaker** - Psychological stability protection using Dynamic Systems Theory
4. **LLM Processing** - Routes to local/cloud models based on complexity
5. **Action Execution** - Triggers environmental changes, nudges, interventions
6. **Memory Update** - Records patterns for future personalization

### Key Components

- **FastAPI Server** (`src/mcp_server/main.py`) - Main application with comprehensive endpoints for chat, context management, user management, task tracking, and webhooks
- **Frame Builder** (`src/frames/builder.py`) - Assembles contextual information optimized for ADHD cognitive patterns
- **Trace Memory** (`src/traces/memory.py`) - Pattern learning and personalization engine using Redis/PostgreSQL
- **Nudge Engine** (`src/nudge/engine.py`) - Intelligent notification and intervention system
- **LLM Router** (`src/mcp_server/llm_client.py`) - Routes between local/cloud models with safety monitoring

### Safety-First Design
- **Crisis Detection** - Pattern matching for self-harm, suicide ideation → Crisis hotlines
- **Circuit Breaker System** - Prevents overwhelming vulnerable users (trips after 3 consecutive failures, 2-4 hour recovery periods)
- **Cognitive Load Management** - ADHD-optimized information density and response formatting
- **Hard-coded Safety Responses** - Never LLM-generated for crisis situations

### Data Storage Strategy
- **Redis** (hot) - Real-time context, user sessions, circuit breaker states
- **PostgreSQL** (warm) - User profiles, task history, interaction logs
- **Vector Database** (future) - Semantic search of patterns and contexts

## Configuration

### Environment Variables
The system requires several environment variables in `.env`:
- `OPENAI_API_KEY` - For LLM processing
- `TELEGRAM_BOT_TOKEN` / `TELEGRAM_CHAT_ID` - For notifications
- `REDIS_URL` - Redis connection (defaults to `redis://localhost:6379`)
- `GOOGLE_CALENDAR_CREDENTIALS` (future) - Calendar integration
- `HOME_ASSISTANT_URL` / `HOME_ASSISTANT_TOKEN` (future) - Smart home integration

### Settings
Configuration is managed through `src/mcp_server/config.py` using Pydantic settings with environment variable support.

## Domain Adaptation Framework

The MCP architecture is designed to be domain-agnostic. The current implementation (ADHDo) serves as the reference implementation, but the framework can be adapted for:
- **MCP-Therapy** - Therapeutic support with alliance tracking
- **MCP-Learn** - Educational support for learning differences  
- **MCP-Elder** - Cognitive support for aging populations
- **MCP-Recovery** - Addiction recovery support

Each domain inherits the core cognitive loop but customizes safety patterns, context types, and response styles.

## Integration Points

### Webhooks
- `/webhooks/telegram` - Telegram bot updates
- `/webhooks/calendar` - Google Calendar events
- `/webhooks/home_assistant` - Smart home state changes

### API Endpoints
- `POST /chat` - Main user interaction endpoint
- `POST /context/{user_id}` - Update user context
- `POST /nudge/{user_id}` - Trigger manual nudge
- `POST /tasks` - Create/manage tasks

## Testing Strategy

Tests should focus on:
- **Cognitive Loop Behavior** - Circuit breaker states, safety overrides, context building
- **Safety Monitoring** - Crisis pattern detection and hard-coded responses
- **LLM Router Logic** - Model selection, local vs cloud routing
- **Memory Persistence** - Redis/PostgreSQL integration patterns
- **API Endpoints** - FastAPI route functionality

## Performance Targets

Based on performance testing, the system targets:
- **Sub-3 second response times** for cognitive loop processing
- **Local model routing** for simple tasks (privacy + speed)
- **Cloud model routing** for complex analysis requiring deeper reasoning
- **Minimal cognitive load** responses for ADHD users (max 8 context items, 150 character responses)

## Key Design Principles

1. **Neurodiversity-Affirming** - Empowering rather than pathologizing, built with ADHD patterns as foundation
2. **Privacy-First** - Sensitive processing stays local, minimal data collection
3. **Safety-First** - Crisis detection with deterministic responses, circuit breaker protection
4. **Recursive Learning** - Each interaction improves future responses through trace memory
5. **Cognitive Load Optimization** - Information density optimized for executive dysfunction patterns

## File Structure Context

- `src/mcp_server/` - Core server and cognitive loop implementation
- `src/frames/` - Context building and frame assembly
- `src/traces/` - Memory and pattern learning systems  
- `src/nudge/` - Intervention and notification engine
- `docs/` - Architecture and API documentation
- `scripts/` - Utility scripts and deployment tools