# ADHD-Friendly Error Handling System

The MCP ADHD Server implements a comprehensive error handling system specifically designed for users with ADHD. This system transforms technical error messages into supportive, actionable communications that reduce cognitive load and maintain user confidence.

## 🎯 Core Principles

### 1. Clarity Over Technical Detail
- Simple, plain language explanations
- Avoid technical jargon and stack traces
- Focus on what the user can do to fix the issue
- Keep messages concise but helpful

### 2. Supportive Tone
- Encouraging, non-blaming language
- Acknowledge that errors happen and are normal
- Provide reassurance that the issue can be resolved
- Use empathetic, understanding tone

### 3. Actionable Guidance
- Clear next steps the user can take
- Specific instructions rather than vague suggestions
- Links to help resources when appropriate
- Alternative approaches when available

### 4. Cognitive Load Reduction
- Break complex problems into simple steps
- Use bullet points or numbered lists
- Highlight the most important information
- Avoid overwhelming with too many options

## 🏗️ System Architecture

### Core Components

1. **ADHDErrorTransformer** (`src/mcp_server/adhd_errors.py`)
   - Central error transformation engine
   - Pattern matching for error categorization
   - Personalization based on user context
   - Supportive message generation

2. **Exception Handlers** (`src/mcp_server/exception_handlers.py`)
   - FastAPI exception handlers for different error types
   - Custom ADHD-specific exceptions
   - Automatic error response generation

3. **Error Context System**
   - User context tracking (cognitive load, session info)
   - Personalized error responses
   - Adaptive messaging based on user state

### Error Categories

```python
class ErrorCategory(str, Enum):
    AUTHENTICATION = "authentication"
    AUTHORIZATION = "authorization" 
    VALIDATION = "validation"
    RATE_LIMIT = "rate_limit"
    SYSTEM = "system"
    DATABASE = "database"
    EXTERNAL_API = "external_api"
    TIMEOUT = "timeout"
    NOT_FOUND = "not_found"
    ADHD_FEATURE = "adhd_feature"
    COGNITIVE_OVERLOAD = "cognitive_overload"
    CIRCUIT_BREAKER = "circuit_breaker"
    SAFETY = "safety"
```

### Severity Levels

```python
class ErrorSeverity(str, Enum):
    LOW = "low"          # Minor issues, user can continue
    MEDIUM = "medium"    # Moderate issues, some features affected
    HIGH = "high"        # Major issues, significant disruption
    CRITICAL = "critical"  # Critical issues, immediate attention needed
```

## 📝 Error Message Examples

### Before (Traditional)
```json
{
  "detail": "ValidationError: field required",
  "status_code": 422
}
```

### After (ADHD-Friendly)
```json
{
  "error": {
    "title": "Missing Information",
    "message": "Looks like we need a bit more info to complete that request.",
    "next_steps": [
      "Check for any empty required fields",
      "Fill in the highlighted fields",
      "Try submitting again"
    ],
    "severity": "low",
    "category": "validation",
    "support_message": "No worries - these things happen!",
    "user_impact": "Quick fix needed before you can continue"
  }
}
```

## 🔧 Implementation

### Using in Routes

```python
from mcp_server.adhd_errors import create_adhd_error_response, system_error

@app.post("/api/example")
async def example_endpoint(request: Request):
    try:
        # Your endpoint logic here
        pass
    except Exception as e:
        # Return ADHD-friendly error
        return create_adhd_error_response(
            error=e,
            status_code=500,
            request=request
        )
```

### Convenience Functions

```python
from mcp_server.adhd_errors import (
    authentication_error, validation_error, 
    rate_limit_error, system_error, not_found_error
)

# Quick error responses
return authentication_error("Invalid credentials")
return validation_error("Missing required field")
return rate_limit_error(retry_after=60)
return system_error("Database connection failed")
return not_found_error("User")
```

### Custom ADHD Exceptions

```python
from mcp_server.exception_handlers import (
    ADHDFeatureException, CognitiveOverloadException
)

# Raise ADHD-specific errors
raise ADHDFeatureException("nudge", "Failed to send nudge", recoverable=True)
raise CognitiveOverloadException(current_load=0.9, threshold=0.8)
```

## 🧠 Personalization Features

### Cognitive Load Adaptation

The system adapts responses based on user cognitive load:

- **Low Load (0.0-0.3)**: Full details, multiple options
- **Medium Load (0.4-0.6)**: Balanced information, focused guidance
- **High Load (0.7-1.0)**: Simplified messages, limited options

```python
# High cognitive load response
context = ErrorContext(cognitive_load=0.8)
# Results in: simplified message, max 2 next steps
```

### Context-Aware Messaging

Different endpoints receive tailored error messages:

- **Chat endpoints**: Conversational, encouraging tone
- **Auth endpoints**: Security-focused, trust-building
- **ADHD features**: Understanding of executive function challenges

### User Preferences

```python
context = ErrorContext(
    user_preferences={"verbose_errors": True}
)
# Includes more detailed explanations
```

## 🚦 Error Types and Handling

### Authentication Errors
- **Login failures**: "Let's get you signed in! Please check your email and password..."
- **Session expired**: "Your session timed out for security. Just sign in again..."
- **Invalid API key**: "API key not recognized. Double-check your key..."

### Validation Errors
- **Missing fields**: "Looks like we need a bit more info..."
- **Invalid format**: "The format looks a bit off. Here's what we're looking for..."
- **Data conflicts**: "There's a conflict with existing data..."

### System Errors
- **Database issues**: "We're having trouble connecting to our database..."
- **External APIs**: "One of our connected services is taking a break..."
- **Timeouts**: "This is taking longer than usual..."

### ADHD-Specific Features
- **Nudge failures**: "Nudge couldn't be sent right now. We'll try again..."
- **Focus sessions**: "Something interrupted your focus session. No worries..."
- **Context errors**: "We're having trouble gathering your context..."

### Protective Features
- **Circuit breaker**: "Our system is taking a protective break..."
- **Cognitive overload**: "The system detected you might be getting overwhelmed..."

## 🧪 Testing

Run the comprehensive test suite:

```bash
pytest tests/test_adhd_errors.py -v
```

See the demo for interactive examples:

```bash
python docs/adhd_errors_demo.py
```

## 📊 Monitoring and Analytics

The system includes comprehensive monitoring:

- Error frequency and patterns
- User cognitive load trends
- Recovery success rates
- Support message effectiveness

All errors are logged with structured data for analysis and system improvement.

## 🎯 Benefits

### For Users with ADHD
- **Reduced anxiety**: Clear, supportive messaging
- **Maintained focus**: Actionable next steps prevent derailment
- **Cognitive protection**: Load-aware message complexity
- **Confidence building**: Encouraging, non-blaming tone

### For Developers
- **Centralized error handling**: Consistent responses across all endpoints
- **Easy integration**: Drop-in replacement for HTTPException
- **Rich monitoring**: Detailed error analytics and user impact tracking
- **Customizable**: Easy to extend for new error types

### For Product Success
- **Better user retention**: Supportive errors reduce abandonment
- **Reduced support load**: Clear guidance helps users self-resolve
- **Inclusive design**: Accessible to neurodivergent users
- **Competitive advantage**: Best-in-class error experience

## 🚀 Next Steps

The ADHD error handling system is now fully integrated throughout the application. Future enhancements could include:

- Machine learning for error message optimization
- A/B testing for message effectiveness
- Integration with user feedback systems
- Expanded personalization options
- Multi-language support with ADHD considerations

## 📚 Resources

- [ADHD and Technology Design Principles](https://example.com)
- [Cognitive Load Theory](https://example.com)
- [Inclusive Error Message Design](https://example.com)
- [FastAPI Exception Handling](https://fastapi.tiangolo.com/tutorial/handling-errors/)

---

*This error handling system represents a significant step forward in creating technology that truly serves neurodivergent users. By putting user wellbeing first, we create not just better error messages, but a more inclusive and supportive digital environment.*