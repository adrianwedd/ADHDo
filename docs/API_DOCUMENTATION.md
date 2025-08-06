# MCP ADHD Server API Documentation

> **TL;DR for ADHD minds**: Complete REST API for building ADHD support apps. Authentication, chat, onboarding, all documented with examples. Auto-generated docs at `/docs` endpoint! 🚀

**Version**: 1.0.0 Beta  
**Base URL**: `http://localhost:8000` (development) | `https://your-domain.com` (production)  
**Interactive Docs**: Visit `/docs` for auto-generated OpenAPI documentation

A production-ready REST API for ADHD executive function support, featuring secure authentication, ADHD-optimized onboarding, real-time chat, and Telegram bot integration.

## Table of Contents

1. [Authentication](#authentication)
2. [Onboarding System](#onboarding-system)
3. [Core Chat API](#core-chat-api)
4. [User Management](#user-management)
5. [Health & Monitoring](#health--monitoring)
6. [Telegram Integration](#telegram-integration)
7. [Error Handling](#error-handling)
8. [Rate Limiting](#rate-limiting)
9. [ADHD-Specific Features](#adhd-specific-features)

---

## Authentication

> **TL;DR**: POST to `/api/auth/register` or `/api/auth/login`, get session cookie, make authenticated requests. Rate limited to prevent overwhelm.

All endpoints (except health checks) require authentication via secure session cookies. ADHD-optimized with friendly error messages and reasonable rate limits.

### Register New User

```http
POST /api/auth/register
Content-Type: application/json

{
  "name": "Jane Smith",
  "email": "jane@example.com", 
  "password": "securepassword123"
}
```

**Response (201 Created):**
```json
{
  "success": true,
  "message": "Welcome to MCP ADHD Server, Jane! Your account has been created successfully.",
  "user": {
    "user_id": "abc123def456",
    "name": "Jane Smith",
    "email": "jane@example.com",
    "created_at": "2024-01-15T10:30:00Z"
  }
}
```

**ADHD Optimization**: Clear success messages, immediate feedback, password requirements explained upfront.

### Login User

```http
POST /api/auth/login
Content-Type: application/json

{
  "email": "jane@example.com",
  "password": "securepassword123"
}
```

**Response (200 OK):**
```json
{
  "success": true,
  "message": "Welcome back, Jane! You've been logged in successfully.",
  "user": {
    "user_id": "abc123def456",
    "name": "Jane Smith",
    "email": "jane@example.com",
    "last_login": "2024-01-15T14:45:00Z"
  },
  "session_id": "session_token_here",
  "expires_at": "2024-01-16T14:45:00Z"
}
```

Sets secure HTTP-only cookie for session management.

### Get Current User

```http
GET /api/auth/me
Authorization: session cookie (automatic)
```

**Response (200 OK):**
```json
{
  "user_id": "abc123def456",
  "name": "Jane Smith", 
  "email": "jane@example.com",
  "timezone": "UTC",
  "preferred_nudge_methods": ["web", "telegram"],
  "energy_patterns": {
    "peak_hours": [9, 10, 11, 14, 15, 16],
    "low_hours": [12, 13, 17, 18, 19]
  },
  "hyperfocus_indicators": ["long_sessions"],
  "nudge_timing_preferences": {
    "morning": "09:00",
    "afternoon": "14:00", 
    "evening": "18:00"
  },
  "created_at": "2024-01-15T10:30:00Z"
}
```

### Logout User

```http
POST /api/auth/logout
```

**Response (200 OK):**
```json
{
  "success": true,
  "message": "You've been logged out successfully. Thank you for using MCP ADHD Server!"
}
```

---

## Onboarding System

> **TL;DR**: Optional ADHD customization flow. Check `/api/onboarding/status`, run multi-step setup, or skip entirely. All ADHD-friendly with clear opt-outs.

ADHD-optimized onboarding flow to customize user experience.

### Get Onboarding Status

```http
GET /api/onboarding/status
```

**Response (200 OK):**
```json
{
  "user_id": "abc123def456",
  "current_step": "welcome",
  "is_completed": false,
  "started_at": "2024-01-15T10:35:00Z",
  "completed_at": null
}
```

### Start Onboarding

```http
POST /api/onboarding/start
```

**Response (200 OK):**
```json
{
  "status": "started",
  "onboarding_id": "abc123def456", 
  "current_step": "welcome",
  "step": "welcome",
  "title": "Welcome to MCP ADHD Server! 🎉",
  "message": "I'm your AI-powered executive function support system, specifically designed for ADHD minds like yours...",
  "action": {
    "type": "button",
    "text": "Let's do this! 🚀",
    "value": {"ready": true}
  }
}
```

### Process Onboarding Step

```http
POST /api/onboarding/step
Content-Type: application/json

{
  "ready": true
}
```

**Response for ADHD Profile Step:**
```json
{
  "status": "next_step",
  "step": "adhd_profile", 
  "title": "Let's Learn About Your ADHD 🧠",
  "message": "Understanding your unique ADHD patterns helps me provide better support...",
  "questions": [
    {
      "id": "primary_challenges",
      "type": "multi_select",
      "question": "What are your biggest ADHD challenges? (Select all that apply)",
      "options": [
        "Staying focused on tasks",
        "Getting started (procrastination)",
        "Time management",
        "Organization",
        "Remembering tasks/appointments",
        "Managing overwhelm", 
        "Emotional regulation",
        "Task switching"
      ]
    },
    {
      "id": "strengths",
      "type": "multi_select",
      "question": "What are some of your ADHD superpowers? (Select all that apply)",
      "options": [
        "Creativity and out-of-box thinking",
        "Hyperfocus abilities",
        "Problem-solving skills",
        "High energy and enthusiasm",
        "Ability to think quickly",
        "Entrepreneurial mindset",
        "Empathy and emotional intelligence",
        "Seeing the big picture"
      ]
    }
  ]
}
```

### Complete Onboarding Step

```http
POST /api/onboarding/step
Content-Type: application/json

{
  "primary_challenges": ["Staying focused on tasks", "Time management"],
  "strengths": ["Creativity and out-of-box thinking", "Hyperfocus abilities"]
}
```

### Skip Onboarding

```http
POST /api/onboarding/skip
```

**Response (200 OK):**
```json
{
  "status": "completed",
  "title": "Welcome, Jane! 🎉",
  "message": "No problem! You can customize your preferences anytime in settings...",
  "next_action": {
    "type": "start_chat",
    "initial_message": "I'm ready to get started!",
    "task_focus": null
  }
}
```

---

## Core Chat API

> **TL;DR**: POST messages to `/api/chat`, get AI responses optimized for ADHD. Includes performance metrics, context awareness, and crisis detection.

The main interaction endpoint for ADHD support.

### Chat with System

```http
POST /chat
Content-Type: application/json

{
  "message": "I'm feeling overwhelmed with my project deadline",
  "task_focus": "Complete quarterly report", 
  "nudge_tier": 0
}
```

**Parameters:**
- `message` (string, required): User's input message
- `task_focus` (string, optional): Current task/project focus
- `nudge_tier` (integer, 0-2): Response style (0=Gentle, 1=Sarcastic, 2=Sergeant)

**Response (200 OK):**
```json
{
  "success": true,
  "response": "I hear you! Project deadlines can feel massive. Let's break this down into smaller, manageable chunks. What's the very next small step you could take on that quarterly report?",
  "actions_taken": ["overwhelm_detection", "task_breakdown_suggestion"],
  "cognitive_load": 0.7,
  "processing_time_ms": 1250,
  "frame_id": "frame_abc123",
  "error": null
}
```

**ADHD Optimizations:**
- ⚡ Ultra-fast responses (target <3s)
- 🧠 Context-aware support 
- 🎯 Task-focused assistance
- 📊 Cognitive load monitoring
- 🚨 Crisis intervention detection

---

## User Management

> **TL;DR**: Update user profiles, manage ADHD preferences, energy patterns, and nudge settings. All optional, all skippable.

### Update User Profile

```http
PUT /api/auth/me
Content-Type: application/json

{
  "name": "Jane Smith-Updated",
  "timezone": "America/New_York",
  "preferred_nudge_methods": ["web", "telegram", "email"],
  "energy_patterns": {
    "peak_hours": [9, 10, 14, 15],
    "primary_challenges": ["focus", "time_management"],
    "strengths": ["creativity", "hyperfocus"]
  },
  "nudge_timing_preferences": {
    "morning": "08:30",
    "afternoon": "13:00",
    "evening": "17:30"
  }
}
```

**Response (200 OK):**
```json
{
  "success": true,
  "message": "Your profile has been updated successfully!",
  "user": {
    "user_id": "abc123def456",
    "name": "Jane Smith-Updated",
    "email": "jane@example.com",
    "timezone": "America/New_York",
    "preferred_nudge_methods": ["web", "telegram", "email"]
  }
}
```

---

## Health & Monitoring

> **TL;DR**: GET `/health` for quick check, GET `/health/detailed` for full system status, GET `/metrics` for Prometheus monitoring.

### Basic Health Check

```http
GET /health
```

**Response (200 OK):**
```json
{
  "status": "healthy",
  "version": "1.0.0", 
  "message": "Executive function orchestrator online",
  "timestamp": "2024-01-15T15:30:00Z"
}
```

### Detailed Health Check

```http
GET /health/detailed
```

**Response (200 OK):**
```json
{
  "status": "healthy",
  "components": {
    "database": {
      "status": "healthy",
      "response_time_ms": 12,
      "last_check": "2024-01-15T15:30:00Z"
    },
    "redis": {
      "status": "healthy", 
      "response_time_ms": 3,
      "last_check": "2024-01-15T15:30:00Z"
    },
    "llm": {
      "status": "healthy",
      "response_time_ms": 850,
      "last_check": "2024-01-15T15:30:00Z"
    }
  },
  "performance": {
    "avg_response_time_ms": 1200,
    "requests_per_minute": 45,
    "adhd_performance_target_met": true
  }
}
```

### Metrics (Prometheus Format)

```http
GET /metrics
```

Returns metrics in Prometheus format for monitoring ADHD-specific KPIs:

```
# HELP adhd_response_time_seconds Response time for ADHD users
# TYPE adhd_response_time_seconds histogram
adhd_response_time_seconds_bucket{le="1.0"} 1250
adhd_response_time_seconds_bucket{le="3.0"} 1800
adhd_response_time_seconds_bucket{le="+Inf"} 2000

# HELP adhd_user_registrations_total Total ADHD user registrations
# TYPE adhd_user_registrations_total counter
adhd_user_registrations_total 157

# HELP adhd_cognitive_load_current Current cognitive load assessment
# TYPE adhd_cognitive_load_current gauge  
adhd_cognitive_load_current 0.65
```

---

## Telegram Integration

> **TL;DR**: POST to `/api/telegram/webhook` for bot messages. Internal use mostly, but webhook management endpoints available for setup.

### Telegram Webhook (Internal Use)

```http
POST /webhooks/telegram
Content-Type: application/json

{
  "update_id": 123456,
  "message": {
    "message_id": 789,
    "from": {
      "id": 987654321,
      "first_name": "Jane",
      "username": "janesmith"
    },
    "chat": {
      "id": 987654321,
      "type": "private"
    },
    "date": 1642267800,
    "text": "/start"
  }
}
```

### Set Telegram Webhook

```http
POST /webhooks/telegram/set
```

**Response (200 OK):**
```json
{
  "status": "success",
  "webhook_url": "https://your-domain.com/webhooks/telegram"
}
```

### Get Webhook Info

```http
GET /webhooks/telegram/info
```

**Response (200 OK):**
```json
{
  "webhook_url": "https://your-domain.com/webhooks/telegram",
  "has_custom_certificate": false,
  "pending_update_count": 0,
  "last_error_date": null,
  "last_error_message": null,
  "max_connections": 40,
  "allowed_updates": ["message", "callback_query"]
}
```

---

## Error Handling

### Standard Error Response

```json
{
  "detail": "Authentication required. Use session cookie, API key, or X-User-ID header in debug mode.",
  "status_code": 401,
  "error_type": "authentication_error"
}
```

### Common Error Codes

| Code | Description | ADHD-Friendly Message |
|------|-------------|----------------------|
| 400 | Bad Request | "I didn't quite understand that. Could you try again?" |
| 401 | Unauthorized | "Please sign in to continue your productivity journey." |
| 422 | Validation Error | "Almost there! Just need to fix: [specific field]" |
| 429 | Rate Limited | "Whoa there, speedy! Take a breath and try again in a moment." |
| 500 | Server Error | "Oops! I had a brief brain fog. Please try that again." |

---

## Rate Limiting

### Default Limits

| Endpoint Category | Limit | Window | ADHD Consideration |
|------------------|-------|--------|-------------------|
| Authentication | 10 requests | 1 hour | Accommodates memory issues |
| Chat API | 100 requests | 1 hour | Supports hyperfocus sessions |
| Registration | 5 requests | 1 hour | Prevents abuse while allowing retries |
| General API | 1000 requests | 1 hour | Generous for ADHD usage patterns |

### Rate Limit Headers

```http
HTTP/1.1 200 OK
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1642271400
X-ADHD-Friendly: true
```

---

## ADHD-Specific Features

### 🚀 Performance Targets

- **Primary Goal**: <3 second response times
- **Reasoning**: ADHD minds lose focus quickly with delays
- **Monitoring**: Real-time performance metrics tracked

### 🧠 Cognitive Load Management

```json
{
  "cognitive_load": 0.7,
  "load_factors": {
    "complexity": 0.6,
    "urgency": 0.8,
    "user_energy": 0.9
  },
  "recommendations": [
    "Consider breaking this into smaller steps",
    "Maybe take a 5-minute break first?"
  ]
}
```

### 🎯 Context Awareness

The system maintains context across requests:

```json
{
  "context": {
    "current_task": "Complete quarterly report",
    "session_duration": "45 minutes",
    "focus_level": "high",
    "recent_wins": ["Finished email responses", "Organized desk"],
    "energy_pattern": "afternoon_peak"
  }
}
```

### 🚨 Crisis Detection

Automatic detection of overwhelming situations:

```json
{
  "crisis_detected": true,
  "crisis_level": "moderate",
  "interventions": [
    "Breathing exercise suggestion",
    "Task simplification", 
    "Break recommendation"
  ],
  "support_message": "Hey, I notice you might be feeling overwhelmed. Let's take this one step at a time."
}
```

### 🏆 Celebration System

Built-in win recognition and celebration:

```json
{
  "celebration": {
    "trigger": "task_completion",
    "message": "🎉 Amazing! You just finished that email. That's executive function in action!",
    "reward_earned": "focus_streak_3",
    "next_milestone": "Complete 5 tasks today"
  }
}
```

---

## Development & Testing

### Debug Mode Headers

In development mode, you can use debug headers:

```http
GET /api/auth/me
X-User-ID: debug-user-123
```

### Example Client Code (JavaScript)

```javascript
// Register new user
const registerUser = async (name, email, password) => {
  const response = await fetch('/api/auth/register', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    credentials: 'include',
    body: JSON.stringify({ name, email, password })
  });
  
  return await response.json();
};

// Chat with the system
const chatWithAI = async (message, taskFocus = null) => {
  const response = await fetch('/chat', {
    method: 'POST', 
    headers: { 'Content-Type': 'application/json' },
    credentials: 'include',
    body: JSON.stringify({ 
      message, 
      task_focus: taskFocus,
      nudge_tier: 0 
    })
  });
  
  return await response.json();
};

// Check onboarding status
const checkOnboarding = async () => {
  const response = await fetch('/api/onboarding/status', {
    credentials: 'include'
  });
  
  return await response.json();
};
```

---

## Production Deployment

### Environment Variables

```bash
# Required
DATABASE_URL=postgresql://user:pass@localhost/mcp_adhd
REDIS_URL=redis://localhost:6379
OPENAI_API_KEY=sk-your-key-here

# Optional but Recommended  
TELEGRAM_BOT_TOKEN=123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11
TELEGRAM_CHAT_ID=987654321

# Security
JWT_SECRET=your-super-secret-jwt-key
SESSION_DURATION_HOURS=24

# Performance
ADHD_RESPONSE_TARGET_MS=3000
DEBUG=false
```

### Docker Deployment

```yaml
version: '3.8'
services:
  adhd-server:
    image: mcp-adhd-server:latest
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://postgres:password@db:5432/mcp_adhd
      - REDIS_URL=redis://redis:6379
    depends_on:
      - db
      - redis
      
  db:
    image: postgres:15
    environment:
      POSTGRES_DB: mcp_adhd
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: password
      
  redis:
    image: redis:7-alpine
```

---

## Support & Community

- **GitHub Issues**: [Report bugs & request features](https://github.com/your-org/mcp-adhd-server/issues)
- **Documentation**: This API guide + README.md
- **ADHD-Friendly**: Built by neurodivergent developers for neurodivergent users
- **Privacy First**: Your data stays with you

---

*Built with 🧠 for ADHD minds everywhere. Because executive function is a liar, but we're here to help.*