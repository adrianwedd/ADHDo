#!/usr/bin/env python3
"""
ADHD-Friendly Error Handling Demo

This script demonstrates the ADHD-friendly error handling system
by showing how various error types are transformed into supportive,
actionable messages optimized for users with ADHD.

Run this script to see examples of error transformations:
    python docs/adhd_errors_demo.py
"""

import sys
import os
import json
from datetime import datetime
from fastapi import HTTPException

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from mcp_server.adhd_errors import (
    error_transformer, ErrorContext, ErrorCategory, ErrorSeverity,
    create_adhd_error_response
)
from mcp_server.exception_handlers import (
    ADHDFeatureException, CognitiveOverloadException, 
    CircuitBreakerOpenException
)


def print_separator():
    """Print a visual separator."""
    print("=" * 80)


def print_error_demo(title, error, context=None, status_code=500):
    """Demonstrate error transformation."""
    print(f"\n📋 {title}")
    print(f"Original error: {error}")
    if context:
        print(f"Context: {context.__dict__}")
    
    # Transform the error
    friendly_error = error_transformer.transform_error(error, context, status_code)
    
    # Display the friendly version
    print(f"\n✨ ADHD-Friendly Response:")
    print(f"   Title: {friendly_error.title}")
    print(f"   Category: {friendly_error.category.value}")
    print(f"   Severity: {friendly_error.severity.value}")
    print(f"   Message: {friendly_error.message}")
    print(f"   Next Steps:")
    for i, step in enumerate(friendly_error.next_steps, 1):
        print(f"     {i}. {step}")
    print(f"   Support: {friendly_error.support_message}")
    if friendly_error.user_impact:
        print(f"   Impact: {friendly_error.user_impact}")
    if friendly_error.estimated_fix_time:
        print(f"   Fix Time: {friendly_error.estimated_fix_time}")
    
    print("-" * 60)


def main():
    """Run the ADHD error handling demonstration."""
    print("🧠 ADHD-Friendly Error Handling System Demo")
    print("This shows how technical errors become supportive, actionable messages.")
    print_separator()
    
    # Authentication Errors
    print("\n🔐 AUTHENTICATION ERRORS")
    print_error_demo(
        "Login Failure",
        "Invalid credentials provided",
        ErrorContext(endpoint="/api/auth/login"),
        401
    )
    
    print_error_demo(
        "Session Expired",
        "Token expired or invalid",
        ErrorContext(user_id="adhd_user"),
        401
    )
    
    # Validation Errors
    print("\n✅ VALIDATION ERRORS")
    print_error_demo(
        "Missing Required Fields",
        "Field required: email",
        ErrorContext(endpoint="/api/auth/register"),
        422
    )
    
    print_error_demo(
        "Invalid Format",
        "Invalid email format provided",
        ErrorContext(cognitive_load=0.3),
        422
    )
    
    # Rate Limiting
    print("\n⏱️ RATE LIMITING")
    print_error_demo(
        "Too Many Requests",
        "Rate limit exceeded",
        ErrorContext(
            user_id="busy_user",
            is_repeat_error=False
        ),
        429
    )
    
    # System Errors
    print("\n🛠️ SYSTEM ERRORS")
    print_error_demo(
        "Database Connection",
        "Database connection failed",
        ErrorContext(endpoint="/api/users"),
        500
    )
    
    print_error_demo(
        "External API Failure",
        "External service unavailable",
        ErrorContext(),
        503
    )
    
    print_error_demo(
        "Request Timeout",
        "Request timeout after 30 seconds",
        ErrorContext(endpoint="/api/chat"),
        504
    )
    
    # ADHD-Specific Features
    print("\n🧠 ADHD-SPECIFIC FEATURE ERRORS")
    print_error_demo(
        "Nudge System Failure",
        "Nudge delivery failed",
        ErrorContext(
            user_id="adhd_user",
            endpoint="/api/nudge"
        ),
        500
    )
    
    print_error_demo(
        "Context Building Error", 
        "Context frame creation failed",
        ErrorContext(
            user_id="adhd_user",
            endpoint="/api/frames",
            cognitive_load=0.4
        ),
        500
    )
    
    # High Cognitive Load Scenarios
    print("\n🧩 HIGH COGNITIVE LOAD ADAPTATION")
    print_error_demo(
        "Complex Error with High Load",
        "Multiple system failures detected",
        ErrorContext(
            user_id="overwhelmed_user",
            cognitive_load=0.8,
            session_duration=7200,  # 2 hours
            is_repeat_error=True
        ),
        500
    )
    
    # Circuit Breaker Protection
    print("\n🔄 PROTECTIVE CIRCUIT BREAKER")
    print_error_demo(
        "Circuit Breaker Engaged",
        "Circuit breaker open for user protection",
        ErrorContext(
            user_id="protected_user",
            cognitive_load=0.9
        ),
        503
    )
    
    # Demonstrate personalization
    print("\n👤 PERSONALIZATION EXAMPLES")
    
    # Same error, different contexts
    base_error = "Internal server error"
    
    contexts = [
        ("New User", ErrorContext(user_id="new_user", cognitive_load=0.2)),
        ("Experienced User", ErrorContext(
            user_id="experienced_user", 
            cognitive_load=0.1,
            user_preferences={"verbose_errors": True}
        )),
        ("Overwhelmed User", ErrorContext(
            user_id="overwhelmed_user",
            cognitive_load=0.8,
            is_repeat_error=True,
            session_duration=10800  # 3 hours
        )),
        ("Long Session User", ErrorContext(
            user_id="long_session_user",
            session_duration=14400,  # 4 hours
            cognitive_load=0.5
        ))
    ]
    
    for context_name, context in contexts:
        print(f"\n--- {context_name} ---")
        friendly_error = error_transformer.transform_error(base_error, context, 500)
        print(f"Message: {friendly_error.message}")
        print(f"Next Steps: {len(friendly_error.next_steps)} steps")
        print(f"Support: {friendly_error.support_message}")
    
    # Demonstrate JSON response format
    print("\n📡 JSON RESPONSE FORMAT EXAMPLE")
    print_separator()
    
    mock_request = type('MockRequest', (), {
        'url': type('MockURL', (), {'path': '/api/demo'})(),
        'headers': {'X-User-ID': 'demo_user', 'X-Cognitive-Load': '0.3'}
    })()
    
    response = create_adhd_error_response(
        HTTPException(status_code=400, detail="Validation failed"),
        400,
        mock_request
    )
    
    print("HTTP Response:")
    print(f"Status Code: {response.status_code}")
    print("Headers:")
    for key, value in response.headers.items():
        if key.startswith('X-'):
            print(f"  {key}: {value}")
    
    print("\nResponse Body (formatted):")
    # Note: In real use, response.body would be bytes
    sample_response = {
        "error": {
            "title": "Form Check Needed",
            "message": "Some information isn't in the expected format. Let's get that sorted out quickly.",
            "next_steps": [
                "Double-check your input for any errors",
                "Make sure all required fields are filled",
                "Try refreshing and submitting again"
            ],
            "severity": "medium",
            "category": "validation",
            "user_impact": "Form submission blocked until corrections are made",
            "support_message": "Forms can be tricky sometimes - you're doing great!",
            "timestamp": datetime.utcnow().isoformat()
        }
    }
    print(json.dumps(sample_response, indent=2))
    
    # Show comparison with traditional error
    print("\n⚖️ BEFORE & AFTER COMPARISON")
    print_separator()
    
    print("🔴 Traditional Error Response:")
    traditional = {
        "detail": "ValidationError: field required",
        "status_code": 422
    }
    print(json.dumps(traditional, indent=2))
    
    print("\n🟢 ADHD-Friendly Error Response:")
    adhd_friendly = {
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
    print(json.dumps(adhd_friendly, indent=2))
    
    print("\n✨ Key Improvements:")
    print("• Clear, non-technical language")
    print("• Specific actionable steps")
    print("• Encouraging, supportive tone")
    print("• Explains impact on user workflow")
    print("• Reduces cognitive load and anxiety")
    print("• Maintains user confidence and momentum")
    
    print_separator()
    print("🎯 ADHD-Friendly Error Handling Complete!")
    print("All errors are now transformed into supportive, actionable guidance.")
    print("Users receive clear next steps instead of technical jargon.")
    print("The system protects cognitive resources and maintains positive UX.")


if __name__ == "__main__":
    main()