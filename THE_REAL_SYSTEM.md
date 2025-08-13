# THE REAL ADHD SUPPORT SYSTEM

## What Actually Works Right Now

### Music Status:
```json
{
  "is_playing": true,
  "current_track": "kontra by Microstoria",
  "chromecast_connected": true,
  "volume": 0.75
}
```
**The system thinks music IS playing on your Chromecast!**

### Available Tools That Work:

1. **Music Control**
   - `POST /music/focus` - Start focus music
   - `POST /music/stop` - Stop music
   - `GET /music/status` - Check what's playing
   - Music auto-play loop running 8am-10pm

2. **Nudge System**
   - `POST /nudge/send?message=X&urgency=Y` - Send to Nest devices
   - Calendar nudge scheduler with context awareness
   - Bedtime nagging with escalation

3. **NEW Claude Tools Endpoint** (needs server restart)
   - `POST /claude/tools` - Can control music, check calendar, send nudges
   - Simple intent parsing - "play music", "stop music", "what's on my calendar"

4. **Real Cognitive Loop**
   - `real_cognitive_loop.py` - The simple one that works
   - Checks music, calendar, sends contextual nudges
   - Panics appropriately when needed

## The Problem You're Having:

**Music IS playing according to the system**, but you can't hear it because:
- Chromecast volume might be muted
- Wrong Chromecast selected
- Physical speakers off/disconnected

## How to Fix Everything:

### 1. Check Your Speakers
```bash
# See what Chromecast devices are available
curl http://localhost:23444/music/devices

# Check current volume
curl http://localhost:23444/music/status | grep volume

# Set volume higher
curl -X POST http://localhost:23444/music/volume/1.0
```

### 2. Restart Server with New Endpoints
```bash
# Kill current server
pkill -f minimal_main

# Start with new Claude tools
PYTHONPATH=/home/pi/repos/ADHDo/src PORT=23444 python -m mcp_server.minimal_main
```

### 3. Test the New Tools Endpoint
```bash
# Play music
curl -X POST http://localhost:23444/claude/tools \
  -H "Content-Type: application/json" \
  -d '{"message": "play focus music"}'

# Check calendar
curl -X POST http://localhost:23444/claude/tools \
  -H "Content-Type: application/json" \
  -d '{"message": "what is on my calendar"}'

# Add event
curl -X POST http://localhost:23444/claude/tools \
  -H "Content-Type: application/json" \
  -d '{"message": "remind me meeting at 3:30pm"}'
```

### 4. Run the Real Cognitive Loop
```bash
python real_cognitive_loop.py
```

## What This System ACTUALLY Does:

1. **Maintains Music** - Ensures focus music plays 8am-10pm
2. **Monitors Calendar** - Checks for urgent events
3. **Sends Smart Nudges** - Context-aware reminders
4. **Panics Appropriately** - Escalates when you're about to miss something

## What It DOESN'T Do (Yet):

1. **Chat with Claude** - Needs auth configuration
2. **Complex reasoning** - It's simple and rule-based
3. **Learn from you** - No fancy ML, just timers

## The Truth:

This is a **timer-based reminder system with music control**. That's it. And that's actually useful for ADHD! The complex "cognitive loop" was overthinking it. This simple system:
- Plays music when you need focus
- Reminds you of important stuff
- Nags you to go to bed
- Panics when you're late

That's a real, functional ADHD support system.