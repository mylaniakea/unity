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
        # Track subscriptions per connection: {websocket: {'plugin_ids': [...], 'metric_names': [...]}}
        self.subscriptions: dict = {}
        self._lock = asyncio.Lock()
    
    async def connect(self, websocket: WebSocket):
        """Accept and register a new WebSocket connection."""
        await websocket.accept()
        async with self._lock:
            self.active_connections.add(websocket)
            self.subscriptions[websocket] = {
                'plugin_ids': set(),  # Empty set = subscribe to all
                'metric_names': set()  # Empty set = subscribe to all metrics
            }
        logger.info(f"WebSocket connected. Total connections: {len(self.active_connections)}")
    
    async def disconnect(self, websocket: WebSocket):
        """Remove a WebSocket connection."""
        async with self._lock:
            self.active_connections.discard(websocket)
            self.subscriptions.pop(websocket, None)
        logger.info(f"WebSocket disconnected. Total connections: {len(self.active_connections)}")
    
    async def broadcast(self, message: dict, plugin_id: str = None, metric_name: str = None):
        """
        Broadcast message to all connected clients (respecting subscriptions).
        
        Args:
            message: Dict to send as JSON
            plugin_id: Optional plugin ID for subscription filtering
            metric_name: Optional metric name for subscription filtering
        """
        if not self.active_connections:
            return
        
        json_message = json.dumps(message, default=str)
        
        # Send to connections that match subscription, remove dead ones
        dead_connections = set()
        
        async with self._lock:
            for connection in self.active_connections:
                # Check if connection is subscribed to this message
                subs = self.subscriptions.get(connection, {'plugin_ids': set(), 'metric_names': set()})
                
                # If plugin_id specified, check subscription
                if plugin_id:
                    plugin_ids = subs.get('plugin_ids', set())
                    # Empty set means subscribe to all, otherwise check if in set
                    if plugin_ids and plugin_id not in plugin_ids:
                        continue
                
                # If metric_name specified, check subscription
                if metric_name:
                    metric_names = subs.get('metric_names', set())
                    if metric_names and metric_name not in metric_names:
                        continue
                
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
            for conn in dead_connections:
                self.subscriptions.pop(conn, None)
    
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
    
    Supported message types:
    - ping: Heartbeat from client
    - subscribe: Subscribe to specific plugins/metrics
    - unsubscribe: Unsubscribe from plugins/metrics
    """
    msg_type = message.get("type")
    
    if msg_type == "ping":
        await manager.send_personal({
            "type": "pong",
            "timestamp": datetime.now().isoformat()
        }, websocket)
    
    elif msg_type == "subscribe":
        # Subscribe to specific plugins and/or metrics
        plugin_ids = message.get("plugin_ids", [])
        metric_names = message.get("metric_names", [])
        
        async with manager._lock:
            if websocket in manager.subscriptions:
                subs = manager.subscriptions[websocket]
                if plugin_ids:
                    subs['plugin_ids'].update(plugin_ids)
                if metric_names:
                    subs['metric_names'].update(metric_names)
        
        await manager.send_personal({
            "type": "subscribed",
            "plugin_ids": list(plugin_ids) if plugin_ids else "all",
            "metric_names": list(metric_names) if metric_names else "all",
            "message": "Subscription updated"
        }, websocket)
    
    elif msg_type == "unsubscribe":
        # Unsubscribe from specific plugins/metrics
        plugin_ids = message.get("plugin_ids", [])
        metric_names = message.get("metric_names", [])
        
        async with manager._lock:
            if websocket in manager.subscriptions:
                subs = manager.subscriptions[websocket]
                if plugin_ids:
                    subs['plugin_ids'].difference_update(plugin_ids)
                if metric_names:
                    subs['metric_names'].difference_update(metric_names)
        
        await manager.send_personal({
            "type": "unsubscribed",
            "plugin_ids": list(plugin_ids) if plugin_ids else "none",
            "metric_names": list(metric_names) if metric_names else "none",
            "message": "Unsubscribed successfully"
        }, websocket)
    
    elif msg_type == "get_subscriptions":
        # Get current subscriptions
        async with manager._lock:
            subs = manager.subscriptions.get(websocket, {'plugin_ids': set(), 'metric_names': set()})
        
        await manager.send_personal({
            "type": "subscriptions",
            "plugin_ids": list(subs.get('plugin_ids', set())) or "all",
            "metric_names": list(subs.get('metric_names', set())) or "all"
        }, websocket)
    
    else:
        await manager.send_personal({
            "type": "error",
            "message": f"Unknown message type: {msg_type}"
        }, websocket)


# Helper functions for broadcasting events (called by scheduler)

async def broadcast_metrics_update(plugin_id: str, metrics: dict):
    """
    Broadcast new metrics to all connected clients (respecting subscriptions).
    
    Args:
        plugin_id: Plugin identifier
        metrics: Metrics data
    """
    await manager.broadcast({
        "type": "metrics:update",
        "plugin_id": plugin_id,
        "metrics": metrics,
        "timestamp": datetime.now().isoformat()
    }, plugin_id=plugin_id)


async def broadcast_status_change(plugin_id: str, status: dict):
    """
    Broadcast plugin status change to all connected clients (respecting subscriptions).
    
    Args:
        plugin_id: Plugin identifier
        status: Status data
    """
    await manager.broadcast({
        "type": "plugin:status",
        "plugin_id": plugin_id,
        "status": status,
        "timestamp": datetime.now().isoformat()
    }, plugin_id=plugin_id)


async def broadcast_execution_complete(plugin_id: str, execution: dict):
    """
    Broadcast plugin execution completion to all connected clients (respecting subscriptions).
    
    Args:
        plugin_id: Plugin identifier
        execution: Execution data
    """
    await manager.broadcast({
        "type": "execution:complete",
        "plugin_id": plugin_id,
        "execution": execution,
        "timestamp": datetime.now().isoformat()
    }, plugin_id=plugin_id)


async def broadcast_alert(alert_data: dict):
    """
    Broadcast alert events to all connected clients.
    
    Args:
        alert_data: Alert data including id, severity, message, status, etc.
    """
    await manager.broadcast({
        "type": "alert:update",
        "alert": alert_data,
        "timestamp": datetime.now().isoformat()
    })
