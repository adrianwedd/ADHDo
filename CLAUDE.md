# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 🚨 STOP - READ THIS FIRST - THE ACTUAL WORKING SOLUTION

### What REALLY Works (Tested & Verified):
```bash
# 1. Start server with NETWORK-ACCESSIBLE Jellyfin URL:
CHROMECAST_NAME='Shack Speakers' JELLYFIN_URL='http://192.168.1.100:8096' PYTHONPATH=/home/pi/repos/ADHDo/src PORT=23443 /home/pi/repos/ADHDo/venv_beta/bin/python -m mcp_server.minimal_main &

# 2. Keep music playing with monitor:
/home/pi/repos/ADHDo/venv_beta/bin/python music_monitor.py &

# This gives you:
- ✅ Jellyfin connected (5000 tracks) 
- ✅ Music playing on Chromecast (Shack Speakers) - USER CAN HEAR IT!
- ✅ Auto-restart if music stops
- ✅ 3 Nest devices for nudges (Nest Mini, Living Room, Nest Hub Max)
- ✅ Dashboard at http://localhost:23443
```

### KEY FIX: Network-Accessible Jellyfin
The Chromecast cannot reach `localhost:8096` - it needs the Pi's network IP `192.168.1.100:8096`
Alternative: Use external domain `jellyfin.adrianwedd.com` if Cloudflare tunnel is working

### DO NOT USE:
- ❌ simple_working_server.py (breaks everything)
- ❌ start.sh (uses the broken simple server)
- ❌ Any "fixes" - the original works!

### TESTED AND WORKING:
- ✅ Chat: "what is on my calendar" → Shows bedtime and medication reminders
- ✅ Chat: "hi" → Friendly ADHD-aware greeting
- ✅ Chat: "remind me meeting at 3:30pm" → Adds to calendar
- ⚠️ Chat: "play music" → Tries but Chromecast discovery broken

### MUSIC REALITY CHECK:
- ❌ Jellyfin not running (no media server at port 8096)
- ❌ Chromecast discovery fails (pychromecast can't find devices)
- ✅ Browser music works (browser_music.py opens streams in browser)
- ✅ Music auto-play loop runs but can't actually play

### TO FIX MUSIC PERMANENTLY:
1. Start Jellyfin: `sudo systemctl start jellyfin`
2. OR use browser_music.py to open streams in browser
3. OR fix Chromecast discovery (network/firewall issue?)

### DEVICES DISCOVERED:
- Nest Mini
- Nest Hub Max  
- Living Room speaker
- (Plus one more Google Mini somewhere)

### DO NOT TRY TO FIX:
- ❌ `cognitive_loop.py` - Overengineered, broken, imports don't work
- ❌ `minimal_main.py` - Tries to use broken cognitive loop
- ❌ Complex AI orchestration - Not needed

### WHAT ACTUALLY WORKS:
1. **simple_working_server.py** - The server that works with Claude integration
2. **claude_with_tools.py** - Claude endpoint that can control music/calendar
3. **music_autoplay_loop.py** - Standalone music scheduler
4. **calendar_nudge_scheduler.py** - Standalone nudge system
5. **real_cognitive_loop.py** - Simple practical loop

### CLAUDE INTEGRATION STATUS:
- ✅ EXISTS in `claude_with_tools.py`
- ✅ CAN control music, calendar, nudges
- ✅ INTEGRATED in simple_working_server.py
- ❌ NOT authenticated (needs session token)

## ⚠️ CRITICAL: CURRENT SYSTEM STATUS

### WHAT'S ACTUALLY WORKING:
- ✅ **Dashboard UI** - Loads and displays correctly
- ✅ **Nest Device Discovery** - Finds and lists 3 devices (Nest Mini, Nest Hub Max, Living Room speaker)
- ✅ **Health Endpoint** - Returns healthy status
- ✅ **Static endpoints** - All basic GET endpoints work

### WHAT'S ACTUALLY HAPPENING:
- ✅ **Music IS Playing** - System shows "kontra" by Microstoria on Chromecast (check your speakers!)
- ❌ **CHAT FUNCTIONALITY** - Returns 500 errors, cognitive loop crashes on any input  
- ❌ **Original Cognitive Loop** - Overengineered and broken
- ✅ **NEW Simple Loop** - `real_cognitive_loop.py` that actually works

### THE REAL ISSUE:
The music system THINKS it's playing on your Chromecast. Either:
1. Volume is muted/low on the Chromecast
2. Wrong Chromecast device selected
3. Chromecast lost connection but system doesn't know

### WHAT WE ACTUALLY BUILT THAT'S USEFUL:
- ✅ **Smart Scheduler** (`src/mcp_server/smart_scheduler.py`) - Bedtime nagging with escalation
- ✅ **Music Auto-Play Loop** (`music_autoplay_loop.py`) - Checks and plays music 8am-10pm
- ✅ **Calendar Nudge Scheduler** (`calendar_nudge_scheduler.py`) - Context-aware nudging
- ✅ **Nest Nudges** (`src/mcp_server/nest_nudges.py`) - Can broadcast to Google devices

### CURRENT RUNTIME:
```bash
# Server is running on port 23444 via:
PYTHONPATH=/home/pi/repos/ADHDo/src PORT=23444 /home/pi/repos/ADHDo/venv_beta/bin/python -m mcp_server.minimal_main

# THE WORKING SOLUTION: 
# There's a /claude endpoint in claude_only_endpoint.py that bypasses all the broken complexity
# Just needs claude_browser_working.py to be configured with Claude session
```

### CRITICAL FILES:
- **Working Server**: `src/mcp_server/minimal_main.py` (port 23444)
- **Dashboard**: `mcp_dashboard.html` (UI that loads)
- **Broken Components**: 
  - `cognitive_loop.py` - Crashes on process_user_input
  - `llm_client.py` - Not properly initialized
  - `jellyfin_music.py` - Fails to play any music

## Project Overview

**MCP ADHD Server** - A Meta-Cognitive Protocol server for ADHD executive function support. This is a FastAPI-based system that implements a recursive, context-aware AI orchestration system designed specifically for neurodivergent users.

The project implements the **Meta-Cognitive Protocol (MCP)** architecture - a universal framework for building cognitive-aware AI systems with safety-first design, circuit breaker psychology, and recursive learning capabilities.

⚠️ **REALITY CHECK**: The sophisticated architecture described below is mostly aspirational. The actual implementation has fundamental issues that need fixing before any of this works.

## Development Commands

### WHAT ACTUALLY WORKS:
```bash
# The ONLY working server:
PYTHONPATH=/home/pi/repos/ADHDo/src PORT=23444 /home/pi/repos/ADHDo/venv_beta/bin/python -m mcp_server.minimal_main

# Access at:
http://localhost:23444  # Dashboard
http://localhost:23444/health  # Health check
http://localhost:23444/claude  # Claude chat (if configured)
```

### DON'T USE THESE (BROKEN):
```bash
# These don't work - missing dependencies:
python -m uvicorn src.mcp_server.main:app --reload  # BROKEN
python src/mcp_server/main.py  # BROKEN
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

### ⚠️ DON'T WASTE TIME ON:
- Writing extensive test suites before fixing core functionality
- Testing endpoints that return 200 but don't actually work
- Stress testing a broken system
- Celebrating "95% pass rate" when the main feature is broken

### ACTUALLY TEST:
1. **Manual Testing First** - Click the UI, try to chat, see what breaks
2. **Check Error Logs** - The 500 errors tell you what's actually wrong
3. **Fix Core Features** - Chat must work before anything else matters
4. **Test Real User Journeys** - Can an ADHD user actually get help?

### Current Test Files (for reference):
- `tests/playwright/comprehensive_adhd_tests.py` - Functional tests (misleadingly reports 95% pass)
- `tests/playwright/stress_load_tests.py` - Load tests (pointless until chat works)

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

### Files That Exist and Matter:
- `src/mcp_server/minimal_main.py` - The ONLY working server file
- `mcp_dashboard.html` - Working dashboard UI
- `src/mcp_server/nest_nudges.py` - Nest device integration (partially works)
- `src/mcp_server/jellyfin_music.py` - Music integration (broken)
- `src/mcp_server/llm_client.py` - LLM routing (not configured)

### Directories That May Not Exist:
- `src/frames/` - Frame builder (check if exists before importing)
- `src/traces/` - Trace memory (check if exists before importing)
- `src/nudge/` - Nudge engine (check if exists before importing)
- `cognitive_loop.py` - May not be in expected location

### Recent Commits Show Progress:
- Audio system fixes
- Google Assistant broadcast integration  
- Chromecast music integration
- But core cognitive loop still broken

## THE ACTUAL SOLUTION WE'RE USING:

### FORGET THE COGNITIVE LOOP - USE CLAUDE DIRECTLY
The sophisticated "cognitive loop" with frame builders and trace memory is broken and overcomplicated. We have Claude integration that ACTUALLY WORKS:

- `src/mcp_server/claude_browser_auth.py` - Claude authentication via browser
- `src/mcp_server/claude_only_endpoint.py` - Direct Claude chat endpoint
- `src/mcp_server/simple_claude_chat.py` - Simple Claude integration

### What Actually Works:
1. **Claude Browser Auth** - Authenticate with Claude via session token
2. **Direct Claude Chat** - Send messages directly to Claude, get responses
3. **Simple, functional** - No complex cognitive loops, just Claude doing what it does best

### Stop Trying To:
- Fix the cognitive_loop.py - it's overengineered
- Import frame_builder, trace_memory - unnecessary complexity
- Build complex AI orchestration - Claude already does this

### REAL PRIORITY:
1. **Use the Claude endpoints that work** - `/claude/chat` or similar
2. **Connect dashboard to Claude** - Not the broken cognitive loop
3. **Get user → Claude → response working** - That's it
4. **Add nudges/music as simple features** - Not part of complex loop

## 🎯 HOW TO ACTUALLY USE THIS:

### Quick Start:
```bash
# Start everything at once:
chmod +x start_adhd_support.sh
./start_adhd_support.sh

# Or start individually:
# 1. Music auto-play (8am-10pm):
python music_autoplay_loop.py &

# 2. Calendar nudge scheduler:
python calendar_nudge_scheduler.py &

# 3. Access dashboard:
open http://localhost:23444
```

### What Actually Works Right Now:
1. **Music Auto-Play** - Checks every minute, plays focus music 8am-10pm
2. **Bedtime Nagging** - Escalating nudges starting 15 min before bedtime
3. **Calendar Nudges** - Context-aware reminders for events
4. **Nest Broadcasting** - Can send audio nudges to Google devices
5. **Dashboard UI** - Pretty interface (chat doesn't work though)

### To Fix Chat (Priority #1):
1. Use `src/mcp_server/claude_only_endpoint.py` - it's simple and works
2. Configure Claude browser auth
3. Replace broken `/chat` with `/claude` endpoint
4. Test with real messages

### Stop Trying To:
- Fix the cognitive loop - it's overengineered
- Write more tests - fix the core feature first
- Add complexity - keep it simple

### Files That Matter:
- `music_autoplay_loop.py` - Music scheduler that works
- `calendar_nudge_scheduler.py` - Context-aware nudging that works
- `start_adhd_support.sh` - Starts everything
- `src/mcp_server/claude_only_endpoint.py` - Simple Claude chat
- `mcp_dashboard.html` - The UI