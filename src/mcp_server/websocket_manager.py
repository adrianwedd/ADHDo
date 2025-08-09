"""
WebSocket connection management for real-time system monitoring.

Centralized WebSocket management for evolution observatory,
health monitoring, and real-time system updates.
"""

from fastapi import WebSocket
from typing import Dict, Any, List, Optional
import asyncio
import json
from datetime import datetime
import logging

from .health_monitor import health_monitor

logger = logging.getLogger(__name__)


class WebSocketConnectionManager:
    """
    Centralized WebSocket connection manager.
    
    Handles connections, broadcasting, and connection lifecycle
    for all real-time system monitoring features.
    """
    
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.connection_info: Dict[WebSocket, Dict] = {}
        self.subscriptions: Dict[WebSocket, List[str]] = {}
        self.connection_groups: Dict[str, List[WebSocket]] = {
            "evolution": [],
            "health": [],
            "chat": [],
            "general": []
        }
    
    async def connect(self, websocket: WebSocket, group: str = "general", client_info: Dict = None):
        """
        Accept new WebSocket connection and categorize it.
        
        Args:
            websocket: The WebSocket connection
            group: Connection group (evolution, health, chat, general)
            client_info: Additional client information
        """
        try:
            await websocket.accept()
            
            # Store connection
            self.active_connections.append(websocket)
            self.connection_info[websocket] = {
                "group": group,
                "connected_at": datetime.utcnow().isoformat(),
                "client_info": client_info or {}
            }
            self.subscriptions[websocket] = []
            
            # Add to group
            if group not in self.connection_groups:
                self.connection_groups[group] = []
            self.connection_groups[group].append(websocket)
            
            # Record connection metric
            health_monitor.record_metric(f"websocket_connections_{group}", 1)
            
            logger.info(f"WebSocket connected: group={group}, total_connections={len(self.active_connections)}")
            
        except Exception as e:
            logger.error(f"Failed to connect WebSocket: {e}")
            health_monitor.record_error("websocket_connect", str(e))
            raise
    
    def disconnect(self, websocket: WebSocket):
        """
        Remove WebSocket connection and clean up.
        
        Args:
            websocket: The WebSocket connection to remove
        """
        try:
            # Get connection info before cleanup
            conn_info = self.connection_info.get(websocket, {})
            group = conn_info.get("group", "general")
            
            # Remove from all tracking structures
            if websocket in self.active_connections:
                self.active_connections.remove(websocket)
            
            if websocket in self.connection_info:
                del self.connection_info[websocket]
            
            if websocket in self.subscriptions:
                del self.subscriptions[websocket]
            
            # Remove from group
            if group in self.connection_groups and websocket in self.connection_groups[group]:
                self.connection_groups[group].remove(websocket)
            
            # Record disconnection metric
            health_monitor.record_metric(f"websocket_disconnections_{group}", 1)
            
            logger.info(f"WebSocket disconnected: group={group}, remaining_connections={len(self.active_connections)}")
            
        except Exception as e:
            logger.error(f"Error during WebSocket disconnect: {e}")
            health_monitor.record_error("websocket_disconnect", str(e))
    
    async def send_to_connection(self, websocket: WebSocket, message: Dict[str, Any]):
        """
        Send message to specific WebSocket connection.
        
        Args:
            websocket: Target WebSocket connection
            message: Message to send
        """
        try:
            await websocket.send_text(json.dumps(message))
        except Exception as e:
            logger.warning(f"Failed to send message to WebSocket: {e}")
            # Connection might be dead, schedule for removal
            self.disconnect(websocket)
    
    async def broadcast_to_group(self, group: str, message: Dict[str, Any]):
        """
        Broadcast message to all connections in a specific group.
        
        Args:
            group: Target connection group
            message: Message to broadcast
        """
        if group not in self.connection_groups:
            return
        
        connections = self.connection_groups[group].copy()  # Copy to avoid modification during iteration
        dead_connections = []
        
        for websocket in connections:
            try:
                await websocket.send_text(json.dumps(message))
            except Exception as e:
                logger.warning(f"Failed to send to WebSocket in group {group}: {e}")
                dead_connections.append(websocket)
        
        # Clean up dead connections
        for dead_conn in dead_connections:
            self.disconnect(dead_conn)
    
    async def broadcast_to_all(self, message: Dict[str, Any]):
        """
        Broadcast message to all active connections.
        
        Args:
            message: Message to broadcast
        """
        connections = self.active_connections.copy()  # Copy to avoid modification during iteration
        dead_connections = []
        
        for websocket in connections:
            try:
                await websocket.send_text(json.dumps(message))
            except Exception as e:
                logger.warning(f"Failed to broadcast to WebSocket: {e}")
                dead_connections.append(websocket)
        
        # Clean up dead connections
        for dead_conn in dead_connections:
            self.disconnect(dead_conn)
    
    async def subscribe_to_topic(self, websocket: WebSocket, topics: List[str]):
        """
        Subscribe WebSocket connection to specific topics.
        
        Args:
            websocket: WebSocket connection
            topics: List of topics to subscribe to
        """
        if websocket in self.subscriptions:
            self.subscriptions[websocket].extend(topics)
            # Remove duplicates
            self.subscriptions[websocket] = list(set(self.subscriptions[websocket]))
        
        logger.info(f"WebSocket subscribed to topics: {topics}")
    
    async def unsubscribe_from_topic(self, websocket: WebSocket, topics: List[str]):
        """
        Unsubscribe WebSocket connection from specific topics.
        
        Args:
            websocket: WebSocket connection
            topics: List of topics to unsubscribe from
        """
        if websocket in self.subscriptions:
            for topic in topics:
                if topic in self.subscriptions[websocket]:
                    self.subscriptions[websocket].remove(topic)
        
        logger.info(f"WebSocket unsubscribed from topics: {topics}")
    
    async def broadcast_to_subscribers(self, topic: str, message: Dict[str, Any]):
        """
        Broadcast message to all connections subscribed to a specific topic.
        
        Args:
            topic: Message topic
            message: Message to send
        """
        message["topic"] = topic
        dead_connections = []
        
        for websocket, topics in self.subscriptions.items():
            if topic in topics:
                try:
                    await websocket.send_text(json.dumps(message))
                except Exception as e:
                    logger.warning(f"Failed to send to subscriber for topic {topic}: {e}")
                    dead_connections.append(websocket)
        
        # Clean up dead connections
        for dead_conn in dead_connections:
            self.disconnect(dead_conn)
    
    def get_connection_stats(self) -> Dict[str, Any]:
        """
        Get current connection statistics.
        
        Returns:
            Dictionary with connection statistics
        """
        return {
            "total_connections": len(self.active_connections),
            "connections_by_group": {
                group: len(connections) 
                for group, connections in self.connection_groups.items()
            },
            "subscription_stats": {
                "total_subscriptions": sum(len(subs) for subs in self.subscriptions.values()),
                "unique_topics": len(set(topic for subs in self.subscriptions.values() for topic in subs))
            },
            "timestamp": datetime.utcnow().isoformat()
        }
    
    async def health_check(self) -> Dict[str, Any]:
        """
        Perform health check on all WebSocket connections.
        
        Returns:
            Health status of WebSocket system
        """
        try:
            # Ping all connections to check health
            ping_message = {
                "type": "ping",
                "timestamp": datetime.utcnow().isoformat()
            }
            
            healthy_connections = 0
            dead_connections = []
            
            for websocket in self.active_connections.copy():
                try:
                    await websocket.send_text(json.dumps(ping_message))
                    healthy_connections += 1
                except Exception:
                    dead_connections.append(websocket)
            
            # Clean up dead connections
            for dead_conn in dead_connections:
                self.disconnect(dead_conn)
            
            return {
                "status": "healthy",
                "total_connections": len(self.active_connections),
                "healthy_connections": healthy_connections,
                "dead_connections_cleaned": len(dead_connections),
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            health_monitor.record_error("websocket_health_check", str(e))
            return {
                "status": "error",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }


# Global WebSocket manager instance
websocket_manager = WebSocketConnectionManager()


async def start_periodic_health_check():
    """
    Background task for periodic WebSocket health checks.
    
    Regularly checks connection health and cleans up dead connections.
    """
    while True:
        try:
            if websocket_manager.active_connections:
                health_status = await websocket_manager.health_check()
                
                # Log health status
                if health_status["status"] == "healthy":
                    logger.debug(f"WebSocket health check: {health_status['healthy_connections']} healthy connections")
                else:
                    logger.warning(f"WebSocket health check failed: {health_status}")
            
            # Wait before next health check (5 minutes)
            await asyncio.sleep(300)
            
        except Exception as e:
            logger.error(f"Error in WebSocket health check: {e}")
            health_monitor.record_error("websocket_health_check_task", str(e))
            await asyncio.sleep(60)  # Wait before retrying