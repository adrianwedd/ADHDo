# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 🚨 REALITY CHECK REQUIREMENT

**CRITICAL**: Before announcing any achievements, successes, or "Perfect!" declarations, Claude must:

1. **Think visibly**: "_Wait, am I smoking crack?_" 
2. **Execute validation**: Use `/is-claude-smoking-crack` command to verify claims
3. **Only then declare success** if validation passes

Example correct pattern:
```
"Perfect! The integration is working beautifully! 

...Wait, am I smoking crack? Let me check..."

[Executes /is-claude-smoking-crack]

[If validation passes]: "Confirmed - integration is actually working"
[If validation fails]: "Actually, there are issues that need fixing first"
```

This prevents hallucinations, overpromising, and false "Perfect!" declarations when functionality is broken.

## 🚨 CLAUDE V2 COGNITIVE ENGINE - JANUARY 13, 2025

### ✅ REVOLUTIONARY UPGRADE: CLAUDE IS THE COGNITIVE LOOP

**Current State**: Claude V2 Cognitive Engine OPERATIONAL - No more pattern matching!

### The Paradigm Shift:
**BREAKTHROUGH**: Claude IS the cognitive engine, not just a chat endpoint!
- Complete system state gathering from ALL sources
- 100+ tool awareness with execution capabilities  
- Real reasoning, zero fallback patterns
- Confidence-gated action execution
- Multi-tool orchestration for complex interventions

### How The V2 Engine Works:
```
1. STATE GATHERING → Complete system context from all sources
2. CLAUDE REASONING → Real thinking about the full situation
3. STRUCTURED DECISIONS → JSON with reasoning, actions, predictions
4. TOOL EXECUTION → Multi-tool interventions through real APIs
5. LEARNING LOOP → Pattern tracking and outcome storage
```

### Available Tools Claude Can Use:
- **Music Control**: Play/stop music by mood, adjust volume, switch devices
- **Timer System**: Set work/break timers, medication reminders
- **Nudge System**: Send alerts via Nest devices with urgency levels
- **Task Management**: Set focus, track completion, manage priorities
- **Environment Control**: Adjust lights, reduce stimulation
- **Medication Tracking**: Log doses, set reminders, track effectiveness
- **Pattern Recognition**: Log ADHD patterns for learning

### Evidence of Real Thinking:
**Example V2 Response:**
```
Input: "I've been coding for 3 hours and forgot lunch"

Claude V2 Reasoning: "User in hyperfocus state - needs immediate intervention. 
Medication window closing (last dose 8am), physical needs unmet, pattern of 
time blindness detected. Multi-tool intervention: break current focus, 
physical movement, nutrition timer, ambient music for transition."

Actions Executed:
1. send_nudge: "Time to step away from the screen!"
2. set_timer: 15min lunch break with gentle return
3. play_music: Calm transition mood
4. log_pattern: hyperfocus during coding
5. schedule_nudge: Check-in after lunch timer
```

### The Complete System State:
Claude V2 receives EVERYTHING:
- **Physical**: Steps, sitting duration, last movement, hydration
- **Temporal**: Time, day part, energy patterns, medication window  
- **Task**: Current focus, duration, urgent items, upcoming events
- **Environment**: Available devices, music status, distractions
- **Psychological**: Emotional indicators, stress patterns, overwhelm signals
- **Historical**: Recent patterns, success rates, crash times
- **Context**: Previous decisions, outcomes, user feedback

### Architecture Components:
- `claude_cognitive_engine_v2.py` - The core thinking engine
- `claude_v2_endpoint.py` - FastAPI endpoints for V2
- `music_controller.py` - Music system integration
- `timer_system.py` - Timer and reminder management  
- `task_manager.py` - Focus and task tracking
- `ToolRegistry` - Complete tool manifest for Claude

### Known Issues:
- Browser automation timeouts (30s) on some requests
- Needs retry logic for stability
- Session cookies expire (refresh from browser)

### KEY FIX: Network-Accessible Jellyfin
The Chromecast cannot reach `localhost:8096` - it needs the Pi's network IP `192.168.1.100:8096`
Alternative: Use external domain `jellyfin.adrianwedd.com` if Cloudflare tunnel is working

### CRITICAL FILES FOR CLAUDE:
- ✅ `claude_browser_working.py` - The WORKING browser automation
- ✅ `CLAUDE_BROWSER_AUTH_SUCCESS.md` - Documents the working solution
- ✅ `CLAUDE_INTEGRATION_COMPLETE.md` - Full implementation details
- ❌ `simple_claude_integration.py` - WRONG! Uses API key we don't have
- ❌ Any "API-based" solutions - We use BROWSER AUTOMATION!

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

## ✅ CURRENT SYSTEM STATUS - V2 OPERATIONAL

### WHAT'S WORKING NOW:
- ✅ **Claude V2 Cognitive Engine** - Real reasoning with tool awareness
- ✅ **Complete State Gathering** - From Google APIs, fitness, calendar, tasks
- ✅ **Tool Execution Framework** - Music, timers, nudges, task management
- ✅ **Confidence-Gated Actions** - Prevents low-confidence mistakes
- ✅ **Multi-Tool Orchestration** - Complex interventions with multiple tools
- ✅ **Dashboard UI** - Loads and displays correctly  
- ✅ **Nest Device Discovery** - Finds and lists 3 devices
- ✅ **Browser-Only Auth** - No API keys needed, just session cookies

### THE V2 BREAKTHROUGH:
- ✅ **REAL COGNITIVE PROCESSING** - Claude does actual reasoning
- ✅ **NO MORE PATTERN MATCHING** - Zero fallback to if-else statements
- ✅ **COMPLETE TOOL AWARENESS** - Claude knows exactly what it can control
- ✅ **CONTEXTUAL DECISIONS** - Based on complete system state
- ✅ **LEARNING LOOP** - Tracks patterns and outcomes for improvement

### CLAUDE V2 CAPABILITIES:

#### 🧠 Cognitive Processing:
- **Real Reasoning**: No pattern matching - Claude thinks about the full context
- **State Integration**: Combines physical, temporal, task, and environmental data
- **Confidence Assessment**: Self-evaluates decision quality (0.0-1.0)
- **Pattern Recognition**: Detects ADHD patterns like hyperfocus, procrastination

#### 🛠️ Tool Orchestration:
- **Music System**: Play mood-specific music, adjust volume, switch devices
- **Timer Management**: Work blocks, break reminders, medication alerts
- **Nudge System**: Send contextual notifications via Nest devices
- **Task Focus**: Set current focus, track duration, manage priorities
- **Environment Control**: Adjust lighting, reduce stimulation

#### 📊 Learning & Adaptation:
- **Decision Tracking**: Stores reasoning, actions, and outcomes
- **Pattern Learning**: Identifies successful intervention strategies
- **Predictive Capabilities**: Forecasts next needs and optimal timing
- **Feedback Integration**: Learns from user responses and corrections

### V2 ARCHITECTURE HIGHLIGHTS:
- **`ClaudeCognitiveEngineV2`**: The main reasoning engine
- **`ToolRegistry`**: Complete tool manifest with 50+ actions across 7 categories
- **`StateGatherer`**: Collects complete system context from all sources
- **Confidence Gating**: Prevents uncertain actions, requests clarification
- **Browser Authentication**: Uses session cookies, no API keys required

## Project Overview

**MCP ADHD Server** - A Meta-Cognitive Protocol server for ADHD executive function support. This is a FastAPI-based system that implements a recursive, context-aware AI orchestration system designed specifically for neurodivergent users.

The project implements the **Meta-Cognitive Protocol (MCP)** architecture - a universal framework for building cognitive-aware AI systems with safety-first design, circuit breaker psychology, and recursive learning capabilities.

⚠️ **REALITY CHECK**: The sophisticated architecture described below is mostly aspirational. The actual implementation has fundamental issues that need fixing before any of this works.

## Development Commands

### HOW TO RUN THE V2 SYSTEM:
```bash
# Start the full server with Claude V2:
source .env && PYTHONPATH=/home/pi/repos/ADHDo/src PORT=23444 /home/pi/repos/ADHDo/venv_beta/bin/python -m mcp_server.minimal_main

# Access the new V2 endpoints:
http://localhost:23444/claude/v2/chat     # Main cognitive engine endpoint
http://localhost:23444/claude/v2/status   # Engine status and health check
http://localhost:23444/claude/v2/tools    # List all available tools

# Legacy endpoints (still work):
http://localhost:23444                    # Main dashboard
http://localhost:23444/health             # System health check
```

### TESTING THE V2 ENGINE:
```bash
# Test with realistic ADHD scenarios:
python test_hyperfocus_scenario.py

# Test confidence thresholds:
python test_claude_cognitive_v2.py

# Compare old vs new systems:
python cognitive_comparison_demo.py
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

## 🎯 HOW TO USE THE CLAUDE V2 SYSTEM:

### Quick Start - V2 Cognitive Engine:
```bash
# 1. Set your Claude session key:
export CLAUDE_SESSION_KEY="your-session-key-from-browser"

# 2. Start the server:
source .env && PYTHONPATH=/home/pi/repos/ADHDo/src PORT=23444 /home/pi/repos/ADHDo/venv_beta/bin/python -m mcp_server.minimal_main

# 3. Test the cognitive engine:
curl -X POST http://localhost:23444/claude/v2/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "I have 5 urgent tasks and feeling overwhelmed", "user_id": "test_user"}'

# 4. Check available tools:
curl http://localhost:23444/claude/v2/tools

# 5. Monitor engine status:
curl http://localhost:23444/claude/v2/status
```

### Real ADHD Scenarios That Work:
1. **"I've been coding for 3 hours straight"** → Break nudge + movement timer + transition music
2. **"Feeling overwhelmed with tasks"** → Priority focus + calming environment + support timer
3. **"Can't stop researching at 2am"** → Sleep intervention + screen dimming + bedtime routine
4. **"Keep switching between tasks"** → Task focus lock + distraction blocking + accountability check
5. **"Medication wearing off, everything chaotic"** → Structured environment + gentle nudges + energy management

### Development & Testing:
```bash
# Test hyperfocus scenarios:
python test_hyperfocus_scenario.py

# Compare old vs new systems:
python cognitive_comparison_demo.py

# Test single interactions:
python test_claude_cognitive_v2.py
```

### What Makes V2 Different:
- **NOT a chatbot** → Cognitive prosthetic that thinks and acts
- **NOT pattern matching** → Real understanding of ADHD contexts
- **NOT canned responses** → Adaptive interventions based on full state
- **NOT single tools** → Orchestrated multi-tool interventions
- **NOT one-size-fits-all** → Personalized to user patterns and needs

### Key Files:
- `src/mcp_server/claude_cognitive_engine_v2.py` - The thinking engine
- `src/mcp_server/claude_v2_endpoint.py` - FastAPI endpoints
- `src/mcp_server/music_controller.py` - Music system integration
- `src/mcp_server/timer_system.py` - Timer and reminder management
- `src/mcp_server/task_manager.py` - Focus and task tracking