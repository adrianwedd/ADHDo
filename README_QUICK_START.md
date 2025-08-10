# ADHDo - Quick Start (It Just Works™)

## 🚀 Start in 10 Seconds

```bash
./start.sh
```

That's it. Open http://localhost:8001 in your browser.

## What It Does

**Automatically detects and uses:**
- ✅ Your Redis (running on port 6379)
- ✅ Your Ollama model (deepseek-r1:1.5b) 
- ✅ SQLite for storage (no PostgreSQL needed)
- ✅ Available ports (found 8001 free)

**No configuration needed** - it figured everything out.

## Features That Actually Work

### 🧠 ADHD Support
- **Task paralysis**: "I can't start" → Breaks it into 2-minute chunks
- **Overwhelm**: "Too many things" → Picks ONE thing to focus on
- **Time blindness**: "What time is it?" → Time check + body check
- **Distraction**: "Can't focus" → Practical strategies that work
- **Memory**: "I forgot" → External memory systems

### 🛡️ Safety Features
- Crisis detection with immediate resources (988, 741741)
- Circuit breaker prevents overwhelming you when struggling
- Energy-aware responses adapt to your state

### 💻 Your Actual Setup
- Uses YOUR local Ollama (privacy-first)
- Uses YOUR Redis (already running)
- Works on YOUR Raspberry Pi
- No cloud dependencies needed

## Files Created

1. **`start_adhd_server.py`** - Auto-detects your environment
2. **`adhdo_server.py`** - The actual server (500 lines, not 18,000)
3. **`start.sh`** - One-command launcher
4. **`.env`** - Auto-configured settings

## API Endpoints

- `GET /` - Web interface
- `POST /chat` - Main ADHD support chat
- `POST /task` - Create task with auto-breakdown
- `GET /tasks` - List all tasks
- `POST /nudge` - Get a gentle reminder
- `GET /health` - Check server status

## Real Examples That Work

```bash
# Chat support
curl -X POST http://localhost:8001/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "I cant focus"}'

# Create a task
curl -X POST http://localhost:8001/task \
  -H "Content-Type: application/json" \
  -d '{"title": "Write email to Sarah"}'

# Get a nudge
curl -X POST http://localhost:8001/nudge
```

## If Something Goes Wrong

1. **Port in use?** → It auto-finds another one
2. **No Ollama?** → Falls back to pattern matching (still helpful!)
3. **No Redis?** → Uses in-memory storage (works fine)
4. **Dependencies missing?** → Run: `pip install fastapi uvicorn`

## The Philosophy

- **It should just work** - No 168-line config files
- **Use what you have** - Detects your actual setup
- **Privacy first** - Local LLM, local storage
- **ADHD-friendly** - Works immediately, no setup paralysis

## Compare to Original

| Original | This Version |
|----------|-------------|
| 18,000+ lines | 500 lines |
| 50+ dependencies | 8 essentials |
| Won't start without PostgreSQL | Uses SQLite |
| Requires OpenAI API | Uses your Ollama |
| 168 config variables | Auto-detects everything |
| Enterprise monitoring | Just works |

## Next Steps When You're Ready

1. Open http://localhost:8001 and try it
2. Ask it about your current struggle
3. Create a task and see the breakdown
4. Let it help you start something

---

**Built for a real person with ADHD, on a real Raspberry Pi, to actually help.**

No enterprise BS. Just support when you need it.