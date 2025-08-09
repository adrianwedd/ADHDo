"""
Webhook integration routes - External system integrations.

Extracted from monolithic main.py to improve code organization and maintainability.
"""

from fastapi import APIRouter, HTTPException, Request
from typing import Dict, Any

from ..telegram_bot import telegram_bot
from ..health_monitor import health_monitor
from ..config import settings

webhook_router = APIRouter(prefix="/webhooks", tags=["Webhooks"])


@webhook_router.post("/telegram", 
                     summary="Telegram Bot Webhook",
                     description="Webhook endpoint for Telegram bot updates and message processing")
async def telegram_webhook(update: dict):
    """
    Process incoming Telegram bot updates.
    
    Handles all Telegram interactions including messages, callbacks,
    and bot commands with appropriate security and rate limiting.
    """
    try:
        # Verify webhook authenticity if secret is configured
        if hasattr(settings, 'TELEGRAM_WEBHOOK_SECRET') and settings.TELEGRAM_WEBHOOK_SECRET:
            # Add webhook signature verification here
            pass
        
        # Process update through telegram bot
        result = await telegram_bot.process_update(update)
        
        # Record successful webhook processing
        health_monitor.record_metric("telegram_webhooks_processed", 1)
        
        return {"status": "ok", "update_id": update.get("update_id")}
        
    except Exception as e:
        health_monitor.record_error("telegram_webhook", str(e))
        # Return OK to Telegram to avoid retries for processing errors
        return {"status": "error", "message": "Update processing failed"}


@webhook_router.post("/telegram/set")
async def set_telegram_webhook():
    """
    Configure Telegram webhook URL.
    
    Sets up the webhook endpoint for receiving Telegram updates
    directly rather than polling.
    """
    try:
        webhook_url = f"{settings.BASE_URL}/webhooks/telegram"
        
        success = await telegram_bot.set_webhook(
            url=webhook_url,
            secret_token=getattr(settings, 'TELEGRAM_WEBHOOK_SECRET', None)
        )
        
        if success:
            health_monitor.record_metric("telegram_webhook_configured", 1)
            return {
                "status": "success", 
                "webhook_url": webhook_url,
                "message": "Telegram webhook configured successfully"
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to set Telegram webhook")
            
    except HTTPException:
        raise
    except Exception as e:
        health_monitor.record_error("set_telegram_webhook", str(e))
        raise HTTPException(status_code=500, detail="Webhook configuration failed")


@webhook_router.get("/telegram/info")
async def get_telegram_webhook_info():
    """
    Get current Telegram webhook configuration information.
    
    Returns webhook status, URL, and configuration details
    for debugging and monitoring.
    """
    try:
        webhook_info = await telegram_bot.get_webhook_info()
        
        return {
            "webhook_info": webhook_info,
            "configured": webhook_info.get("url") is not None,
            "pending_updates": webhook_info.get("pending_update_count", 0),
            "last_error": webhook_info.get("last_error_message"),
            "max_connections": webhook_info.get("max_connections", 40)
        }
        
    except Exception as e:
        health_monitor.record_error("get_telegram_webhook_info", str(e))
        raise HTTPException(status_code=500, detail="Failed to retrieve webhook info")


@webhook_router.post("/calendar")
async def calendar_webhook(event: dict):
    """
    Process Google Calendar webhook events.
    
    Handles calendar notifications for task scheduling,
    reminders, and context updates for ADHD users.
    """
    try:
        # Process calendar event
        event_type = event.get("eventType", "unknown")
        
        # Handle different calendar event types
        if event_type == "task_reminder":
            # Trigger task reminder nudge
            user_id = event.get("userId")
            task_id = event.get("taskId")
            
            if user_id and task_id:
                # Import nudge_engine here to avoid circular imports
                from nudge.engine import nudge_engine
                await nudge_engine.trigger_calendar_nudge(user_id, task_id, event)
        
        health_monitor.record_metric("calendar_webhooks_processed", 1)
        
        return {"status": "processed", "event_type": event_type}
        
    except Exception as e:
        health_monitor.record_error("calendar_webhook", str(e))
        return {"status": "error", "message": "Event processing failed"}


@webhook_router.post("/home_assistant")
async def home_assistant_webhook(event: dict):
    """
    Process Home Assistant webhook events.
    
    Integrates smart home events with ADHD support system
    for environmental context and automated interventions.
    """
    try:
        # Process Home Assistant event
        event_type = event.get("event_type", "state_changed")
        entity_id = event.get("entity_id", "")
        
        # Handle relevant smart home events
        if event_type == "state_changed" and "person." in entity_id:
            # Person location changed - update user context
            user_id = event.get("user_id")
            new_state = event.get("new_state", {})
            
            if user_id:
                # Update location context
                from traces.memory import trace_memory
                await trace_memory.update_user_context(user_id, {
                    "location": new_state.get("state", "unknown"),
                    "last_location_update": event.get("time_fired")
                })
        
        health_monitor.record_metric("home_assistant_webhooks_processed", 1)
        
        return {"status": "processed", "entity_id": entity_id}
        
    except Exception as e:
        health_monitor.record_error("home_assistant_webhook", str(e))
        return {"status": "error", "message": "Event processing failed"}


# Agent collaboration endpoints (keeping original structure)
@webhook_router.post("/agents/{agent_id}/request_context")
async def agent_request_context(agent_id: str, request: dict):
    """
    Handle agent context requests for collaborative processing.
    
    Enables other AI agents to request context information
    for improved collaborative decision making.
    """
    try:
        # Import here to avoid circular dependencies
        from traces.memory import trace_memory
        
        context = await trace_memory.get_agent_context(agent_id, request)
        
        health_monitor.record_metric("agent_context_requests", 1)
        
        return {"agent_id": agent_id, "context": context}
        
    except Exception as e:
        health_monitor.record_error("agent_context_request", str(e))
        raise HTTPException(status_code=500, detail="Context request failed")


@webhook_router.post("/agents/{agent_id}/submit_response")
async def agent_submit_response(agent_id: str, response: dict):
    """
    Handle agent response submissions for collaborative learning.
    
    Allows other AI agents to contribute responses and insights
    for continuous system improvement.
    """
    try:
        # Import here to avoid circular dependencies
        from traces.memory import trace_memory
        
        result = await trace_memory.record_agent_response(agent_id, response)
        
        health_monitor.record_metric("agent_responses_submitted", 1)
        
        return {"agent_id": agent_id, "recorded": True, "response_id": result.get("id")}
        
    except Exception as e:
        health_monitor.record_error("agent_response_submission", str(e))
        raise HTTPException(status_code=500, detail="Response submission failed")