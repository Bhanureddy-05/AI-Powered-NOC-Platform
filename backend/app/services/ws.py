"""
app/services/ws.py
==================
WebSocket Connection Manager Service

WHY THIS FILE EXISTS:
    Allows real-time communication by maintaining a registry of open client socket
    connections and sending JSON broadcast event frames (metrics, alerts, tickets).
"""

from typing import List
from fastapi import WebSocket

class ConnectionManager:
    def __init__(self):
        # Keeps track of all active client websocket channels
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        """
        Accepts and adds a client websocket to the active pool.
        """
        await websocket.accept()
        self.active_connections.append(websocket)
        print(f"[WS] Client connected. Total active connections: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        """
        Removes a client from the active pool.
        """
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            print(f"[WS] Client disconnected. Total active connections: {len(self.active_connections)}")

    async def send_personal_message(self, message: dict, websocket: WebSocket):
        """
        Sends a direct JSON payload to a specific client websocket.
        """
        try:
            await websocket.send_json(message)
        except Exception:
            # Client connection might have dropped
            self.disconnect(websocket)

    async def broadcast(self, message: dict):
        """
        Broadcasts a JSON payload to all active client websockets.
        Cleans up dead connections automatically.
        """
        dead_connections = []
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception:
                dead_connections.append(connection)
                
        for dead in dead_connections:
            self.disconnect(dead)

# Create a singleton manager instance to be shared across routing paths
manager = ConnectionManager()
