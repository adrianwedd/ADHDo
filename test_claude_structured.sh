#!/bin/bash

# Build the context JSON
CONTEXT='{
  "current_state": {
    "time": "14:21",
    "task": "writing code",
    "energy": "moderate",
    "last_break": "45 min ago"
  },
  "upcoming": [
    {"time": "15:00", "event": "team meeting", "prep_needed": true}
  ],
  "environment": {
    "music": "focus playlist",
    "distractions": 3
  }
}'

# Create the message
MESSAGE="I can't start reviewing these documents even though my meeting is soon"

# Build the full prompt
PROMPT="Context: $CONTEXT

User says: $MESSAGE

Respond with specific ADHD support. Include:
1. One immediate micro-action
2. Why this helps ADHD brains
3. When to check in again"

# Send to Claude via our endpoint
curl -s -X POST http://localhost:23444/chat \
  -H "Content-Type: application/json" \
  -d "{\"user_id\": \"test\", \"message\": \"$PROMPT\"}" | python -m json.tool
