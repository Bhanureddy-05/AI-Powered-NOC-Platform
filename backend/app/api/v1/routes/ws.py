"""
app/api/v1/routes/ws.py
=======================
WebSocket Live Ingestion & Distribution Router

WHY THIS FILE EXISTS:
    Accepts WebSocket socket requests under the '/api/v1/ws' endpoint context.
    Passes channels to the centralized ConnectionManager for active broadcasting.
"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.services.ws import manager

router = APIRouter(prefix="/ws", tags=["Real-time WebSockets"])

@router.websocket("/live")
async def websocket_live_feed(websocket: WebSocket):
    """
    Accepts incoming websocket channels, adding them to the broadcast pool.
    Listens for ping/pong heartbeat messages.
    """
    await manager.connect(websocket)
    try:
        while True:
            # We keep the connection open by reading client messages (if any)
            # Typically, clients might send ping heartbeats or subscriptions
            data = await websocket.receive_text()
            # Respond back to the client as a simple echo/ack
            await websocket.send_json({"event": "ack", "message": f"Message received: {data}"})
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        print(f"[WS] WebSocket error: {e}")
        manager.disconnect(websocket)
