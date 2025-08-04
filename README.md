# MCP ADHD Server 🧠⚡

> **Meta-Cognitive Protocol** - A recursive, context-aware AI orchestration system for ADHD executive function support

## 🎯 Vision

An agentic, context-aware, accountability-overclocked _meta-orchestrator_ that collaborates with you and your LLM agents to surf the ever-mutating wave of executive dysfunction, task-switching, and just-do-the-fucking-thing energy.

**Not a "to-do list." A cognitive OS layer.**

## 🏗️ Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   MCP Server    │────│  TraceMemory    │────│   FrameBuilder  │
│   (FastAPI)     │    │ (Redis/Postgres)│    │  (Context Gen)  │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│  NudgeEngine    │    │  AgentRouter    │    │  Integrations   │
│  (Notifications)│    │   (LLM Coord)   │    │ (Calendar/HA)   │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## 🚀 Features

### Core Functions
- **Trace-Integrated Nudging**: Tiered escalation from gentle pokes to drill sergeant mode
- **Calendar-Dopamine Fusion**: GPT-assisted calendar co-pilot with energy-aware scheduling
- **Context Syncing**: Recursive knowledge state tracking intentions vs. actions
- **Environmental Integration**: Home Assistant triggers for ADHD-friendly rituals
- **Gamified Feedback**: Points, badges, and optional cringe punishment mode

### MCP Frame Protocol
Standardized context frames for LLM orchestration:
```json
{
  "frame_id": "trace-2025-08-01T13:30Z-user42",
  "user_id": "user42",
  "agent_id": "clarity-coach-llm", 
  "task_focus": "Write response email to Sarah",
  "context": [...],
  "actions": [...]
}
```

## 🛠️ Tech Stack

| Layer         | Tool                         |
|--------------|------------------------------|
| Server       | FastAPI + Python             |
| Storage      | Redis (hot) + Postgres (cold)|
| Semantics    | Weaviate (future)            |
| Notification | Telegram Bot API             |
| Agents       | OpenAI + function calling    |
| Integration  | Home Assistant + Google Cal  |

## 🧪 Development Phases

### Phase 1 - Bootstrap (MVP)
- [x] Project structure
- [ ] FastAPI server foundation  
- [ ] MCP Frame specification
- [ ] Basic TraceMemory (Redis)
- [ ] Telegram bot integration
- [ ] OpenAI agent routing

### Phase 2 - Agency Emergence
- [ ] Recursive trace memory
- [ ] Task-priority rebalancer
- [ ] Energy/time profiling
- [ ] Voice command input

### Phase 3 - CyberGodMode
- [ ] Self-modifying trace memory
- [ ] Multi-modal context (vision/voice)
- [ ] Agent-to-agent collaboration
- [ ] Personal agent summoner

## 🚦 Getting Started

```bash
# Setup environment
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your API keys

# Start development server
python -m uvicorn src.mcp_server.main:app --reload

# Run tests
pytest tests/
```

## 📋 Environment Variables

```bash
# OpenAI
OPENAI_API_KEY=sk-...

# Telegram Bot
TELEGRAM_BOT_TOKEN=...
TELEGRAM_CHAT_ID=...

# Redis
REDIS_URL=redis://localhost:6379

# Google Calendar (future)
GOOGLE_CALENDAR_CREDENTIALS=...

# Home Assistant (future)  
HOME_ASSISTANT_URL=...
HOME_ASSISTANT_TOKEN=...
```

## 🎯 Sample Use Case

**The ADHD Morning:**
1. 7:15am: Coffee machine detected → MCP pulls context
2. Calendar shows "Write tribunal brief" at 9am 
3. MCP generates dopamine hook tasks via LLM
4. Sends Telegram: "Choose: ✅ Brew checklist ✅ Shower + music ✅ Skim notes"
5. User chooses → MCP updates trace, prepares environment
6. Success tracked, patterns learned, future improved

## 📚 Documentation

- [API Reference](docs/api.md)
- [MCP Frame Specification](docs/mcp-frame-spec.md)
- [Integration Guide](docs/integrations.md)
- [Development Guide](docs/development.md)

## 🤝 Contributing

This project addresses a real need for neurodivergent productivity support. Contributions welcome!

## 📄 License

MIT - Build the future of cognitive augmentation

---

**"Because Executive Function Is a Liar."**

*Turning executive dysfunction into a goddamn data stream.*