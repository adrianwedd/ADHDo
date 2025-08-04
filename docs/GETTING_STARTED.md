# Getting Started with MCP ADHD Server

## 🚀 Quick Start

### 1. Clone and Setup

```bash
cd ~/repos
git clone <your-repo-url> mcp-adhd-server  # or use existing directory
cd mcp-adhd-server

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configuration

```bash
# Copy environment template
cp .env.example .env

# Edit .env with your credentials
nano .env
```

**Required Configuration:**
- `OPENAI_API_KEY`: Your OpenAI API key
- `TELEGRAM_BOT_TOKEN`: Create a bot via @BotFather on Telegram
- `TELEGRAM_CHAT_ID`: Your Telegram chat ID (send a message to your bot, then check `https://api.telegram.org/bot<TOKEN>/getUpdates`)

**Optional but Recommended:**
- `HOME_ASSISTANT_URL`: Your Home Assistant instance URL
- `HOME_ASSISTANT_TOKEN`: Long-lived access token from HA
- `REDIS_URL`: Redis instance (defaults to localhost)

### 3. Start the Server

```bash
# Development mode (auto-reload)
python -m uvicorn src.mcp_server.main:app --reload --port 8000

# Or using the installed command
mcp-server
```

Visit `http://localhost:8000/docs` to see the API documentation.

## 🧠 Core Concepts

### MCP Frames
The heart of the system - standardized context packages that contain:
- Current user state (energy, mood, focus)
- Recent task history and intentions
- Environmental context
- Suggested actions for LLM agents

### Trace Memory
Persistent memory that tracks:
- What you said you'd do vs. what you actually did
- Patterns in your productivity cycles
- Effectiveness of different nudging strategies
- Environmental factors that affect your focus

### Nudge Escalation
Three-tier system that progressively increases accountability:
- **Tier 0 (Gentle)**: "Ready to tackle that task?" 🌱
- **Tier 1 (Sarcastic)**: "Still avoiding that thing, huh?" 🙄  
- **Tier 2 (Sergeant)**: "GET UP AND DO IT RIGHT NOW!" ⚡

## 🏠 Home Assistant Integration

### Setup TTS and Media Players

1. **Configure Google TTS** in your `configuration.yaml`:
```yaml
tts:
  - platform: google_translate

# Media players for announcements
media_player:
  - platform: cast
    host: YOUR_GOOGLE_NEST_IP
```

2. **Create Automation Templates**:
```yaml
# Example: Office focus lighting
light:
  - platform: template
    lights:
      focus_mode:
        friendly_name: "Focus Mode"
        turn_on:
          - service: light.turn_on
            target:
              entity_id: light.office_lights
            data:
              brightness_pct: 75
              color_temp: 154  # Cool white for focus
```

3. **Set up Webhook** (optional):
```yaml
# automation.yaml
automation:
  - alias: "MCP ADHD Motion Detection"
    trigger:
      - platform: state
        entity_id: binary_sensor.office_motion
    action:
      - service: rest_command.mcp_context_update
        data:
          user_id: "your_user_id"
          context_type: "motion"
          data: "{{ trigger.to_state.state }}"
```

## 📱 Telegram Bot Setup

1. **Create Bot**: Message @BotFather on Telegram
   - `/newbot`
   - Choose name and username
   - Copy the token to `.env`

2. **Get Chat ID**: 
   - Send a message to your bot
   - Visit: `https://api.telegram.org/bot<YOUR_TOKEN>/getUpdates`
   - Copy your chat ID to `.env`

3. **Test Integration**:
```bash
curl -X POST "http://localhost:8000/nudge/your_user_id" \
  -H "Content-Type: application/json" \
  -d '{"task_id": "test", "message": "Testing nudge system"}'
```

## 🧪 Example Usage Scenarios

### Morning Startup Routine
1. Coffee machine turns on → HA detects → MCP receives context
2. System pulls your calendar, sees "Write proposal" at 9am
3. LLM agent generates warm-up tasks: "☕ Brew checklist ✨ Review notes 🎵 Focus playlist"
4. Telegram message: "Morning! Choose your warm-up: [buttons]"
5. You select "Review notes" → system boosts readiness for main task

### Task Avoidance Detection
1. You tell MCP "I'll write the email after lunch"
2. 2pm: No email activity detected
3. Gentle nudge: "Ready to tackle that email? I can help draft it"
4. 2:30pm: Still avoiding
5. Sarcastic nudge: "The email called. It misses you 📧"
6. 3pm: Sergeant mode: Lights flash red, all music stops, Nest Hub shows "DO THE EMAIL NOW"

### Completion Celebration
1. Email sent → MCP detects completion
2. Lights turn green, success sound plays
3. "+1 Dopamine Achievement: Email Warrior! 🏆"
4. Pattern recorded: "Emails work best after lunch for you"

## 🔧 Development

### Running Tests
```bash
pytest tests/
```

### Code Quality
```bash
black src/
ruff check src/
mypy src/
```

### Adding New Nudge Methods
1. Create class inheriting from `NudgeMethod`
2. Implement `send_nudge()` method
3. Register in `NudgeEngine.__init__()`
4. Add configuration to settings

### Database Migrations
```bash
# Generate migration
alembic revision --autogenerate -m "Add new feature"

# Run migrations  
alembic upgrade head
```

## 🎯 Next Steps

1. **Start Simple**: Set up Telegram nudging first
2. **Add Home Assistant**: Begin with TTS announcements
3. **Expand Gradually**: Add environmental controls as you get comfortable
4. **Customize Messages**: Modify nudge templates to match your style
5. **Monitor Patterns**: Use the trace memory to understand your productivity cycles

## 🆘 Troubleshooting

### Common Issues
- **Telegram not working**: Check token and chat ID
- **Home Assistant connection failed**: Verify URL and token
- **Redis connection error**: Make sure Redis is running
- **No nudges being sent**: Check user preferences and time restrictions

### Debug Mode
Set `DEBUG=true` in `.env` to enable detailed logging and API docs.

### Support
This is a personal productivity tool - customize it to match your ADHD brain! The system learns your patterns over time, so give it a few days to understand your workflow.

---

**Remember**: The goal isn't to eliminate ADHD behaviors, but to work *with* your neurodivergent brain patterns to create sustainable productivity systems. 🧠⚡