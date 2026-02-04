import json
from datetime import datetime, timezone

from fastapi import WebSocket


class WebSocketManager:
    """Manages WebSocket connections and message broadcasting."""

    def __init__(self):
        self.active_connections: dict[int, WebSocket] = {}

    async def connect(self, user_id: int, websocket: WebSocket):
        await websocket.accept()
        self.active_connections[user_id] = websocket

    def disconnect(self, user_id: int):
        self.active_connections.pop(user_id, None)

    def is_connected(self, user_id: int) -> bool:
        return user_id in self.active_connections

    async def send_message(self, user_id: int, msg_type: str, payload: dict):
        ws = self.active_connections.get(user_id)
        if ws:
            try:
                await ws.send_json(
                    {
                        "type": msg_type,
                        "payload": payload,
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    }
                )
            except Exception:
                self.disconnect(user_id)

    async def send_status(self, user_id: int, status_type: str, data: dict):
        await self.send_message(
            user_id,
            "status_update",
            {"status_type": status_type, **data},
        )

    async def send_chat_response(self, user_id: int, message: str):
        await self.send_message(
            user_id,
            "chat_response",
            {"content": message, "role": "assistant"},
        )

    async def send_error(self, user_id: int, error: str):
        await self.send_message(user_id, "error", {"message": error})

    async def broadcast(self, msg_type: str, payload: dict):
        for user_id in list(self.active_connections.keys()):
            await self.send_message(user_id, msg_type, payload)


# Singleton instance
ws_manager = WebSocketManager()


def get_ws_manager() -> WebSocketManager:
    return ws_manager
