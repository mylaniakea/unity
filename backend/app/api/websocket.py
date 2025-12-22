"""
WebSocket API for Real-Time Metrics

Streams plugin metrics, status updates, and execution events in real-time.
"""
import logging
import asyncio
import json
from typing import Set
from datetime import datetime
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from fastapi.websockets import WebSocketState

logger = logging.getLogger(__name__)

router = APIRouter()


class ConnectionManager:
    """Manage WebSocket connections and broadcasting."""
    
    def __init__(self):
        self.active_connections: Set[WebSocket] = set()
        self._lock = asyncio.Lock()
    
    async def connect(self, websocket: WebSocket):
        """Accept and register a new WebSocket connection."""
        await websocket.accept()
        async with self._lock:
            self.active_connections.add(websocket)
        logger.info(f"WebSocket connected. Total connections: {len(self.active_connections)}")
    
    async def disconnect(self, websocket: WebSocket):
        """Remove a WebSocket connection."""
        async with self._lock:
            self.active_connections.discard(websocket)
        logger.info(f"WebSocket disconnected. Total connections: {len(self.active_connections)}")
    
    async def broadcast(self, message: dict):
        """
        Broadcast message to all connected clients.
        
        Args:
            message: Dict to send as JSON
        """
        if not self.active_connections:
            return
        
        json_message = json.dumps(message, default=str)
        
        # Send to all connections, remove dead ones
        dead_connections = set()
        
        async with self._lock:
            for connection in self.active_connections:
                try:
                    if connection.client_state == WebSocketState.CONNECTED:
                        await connection.send_text(json_message)
                    else:
                        dead_connections.add(connection)
                except Exception as e:
                    logger.warning(f"Failed to send to WebSocket: {e}")
                    dead_connections.add(connection)
            
            # Remove dead connections
            self.active_connections -= dead_connections
    
    async def send_personal(self, message: dict, websocket: WebSocket):
        """
        Send message to a specific client.
        
        Args:
            message: Dict to send as JSON
            websocket: Target WebSocket connection
        """
        try:
            json_message = json.dumps(message, default=str)
            await websocket.send_text(json_message)
        except Exception as e:
            logger.error(f"Failed to send personal message: {e}")


# Global connection manager instance
manager = ConnectionManager()


@router.websocket("/ws/metrics")
async def websocket_metrics(websocket: WebSocket):
    """
    WebSocket endpoint for real-time metrics streaming.
    
    Message types:
    - metrics:update - New metrics collected
    - plugin:status - Plugin status change
    - execution:complete - Plugin execution finished
    - heartbeat - Keep-alive ping
    """
    await manager.connect(websocket)
    
    try:
        # Send welcome message
        await manager.send_personal({
            "type": "connected",
            "message": "Connected to Unity metrics stream",
            "timestamp": datetime.now().isoformat()
        }, websocket)
        
        # Send heartbeat every 30 seconds
        heartbeat_task = asyncio.create_task(send_heartbeat(websocket))
        
        # Listen for client messages (optional, for future features like filtering)
        while True:
            try:
                data = await asyncio.wait_for(websocket.receive_text(), timeout=60.0)
                
                # Handle client messages
                try:
                    message = json.loads(data)
                    await handle_client_message(websocket, message)
                except json.JSONDecodeError:
                    await manager.send_personal({
                        "type": "error",
                        "message": "Invalid JSON"
                    }, websocket)
                    
            except asyncio.TimeoutError:
                # No message received in 60s, continue (heartbeat keeps connection alive)
                continue
                
    except WebSocketDisconnect:
        logger.info("WebSocket disconnected normally")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    finally:
        heartbeat_task.cancel()
        await manager.disconnect(websocket)


async def send_heartbeat(websocket: WebSocket):
    """Send periodic heartbeat to keep connection alive."""
    try:
        while True:
            await asyncio.sleep(30)
            if websocket.client_state == WebSocketState.CONNECTED:
                await manager.send_personal({
                    "type": "heartbeat",
                    "timestamp": datetime.now().isoformat()
                }, websocket)
    except asyncio.CancelledError:
        pass
    except Exception as e:
        logger.error(f"Heartbeat error: {e}")


async def handle_client_message(websocket: WebSocket, message: dict):
    """
    Handle messages from client.
    
    Future features:
    - Subscribe to specific plugins
    - Filter by metric names
    - Adjust update frequency
    """
    msg_type = message.get("type")
    
    if msg_type == "ping":
        await manager.send_personal({
            "type": "pong",
            "timestamp": datetime.now().isoformat()
        }, websocket)
    
    elif msg_type == "subscribe":
        # Future: Subscribe to specific plugins
        plugin_ids = message.get("plugin_ids", [])
        await manager.send_personal({
            "type": "subscribed",
            "plugin_ids": plugin_ids,
            "message": "Subscription feature coming soon"
        }, websocket)
    
    else:
        await manager.send_personal({
            "type": "error",
            "message": f"Unknown message type: {msg_type}"
        }, websocket)


# Helper functions for broadcasting events (called by scheduler)

async def broadcast_metrics_update(plugin_id: str, metrics: dict):
    """
    Broadcast new metrics to all connected clients.
    
    Args:
        plugin_id: Plugin identifier
        metrics: Metrics data
    """
    await manager.broadcast({
        "type": "metrics:update",
        "plugin_id": plugin_id,
        "metrics": metrics,
        "timestamp": datetime.now().isoformat()
    })


async def broadcast_status_change(plugin_id: str, status: dict):
    """
    Broadcast plugin status change to all connected clients.
    
    Args:
        plugin_id: Plugin identifier
        status: Status data
    """
    await manager.broadcast({
        "type": "plugin:status",
        "plugin_id": plugin_id,
        "status": status,
        "timestamp": datetime.now().isoformat()
    })


async def broadcast_execution_complete(plugin_id: str, execution: dict):
    """
    Broadcast plugin execution completion to all connected clients.
    
    Args:
        plugin_id: Plugin identifier
        execution: Execution data
    """
    await manager.broadcast({
        "type": "execution:complete",
        "plugin_id": plugin_id,
        "execution": execution,
        "timestamp": datetime.now().isoformat()
    })
