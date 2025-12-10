from fastapi import WebSocket, WebSocketDisconnect
from typing import Dict, List
from logger_config import logger

class ConnectionManager:
    def __init__(self):
        # Store active connections: user_id -> List[WebSocket]
        self.active_connections: Dict[str, List[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, user_id: str):
        await websocket.accept()
        if user_id not in self.active_connections:
            self.active_connections[user_id] = []
        self.active_connections[user_id].append(websocket)
        logger.info(f"User {user_id} connected via WebSocket")

    def disconnect(self, websocket: WebSocket, user_id: str):
        if user_id in self.active_connections:
            self.active_connections[user_id].remove(websocket)
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]

    async def send_personal_message(self, message: dict, user_id: str):
        # Send data ONLY to this specific user's open tabs
        if user_id in self.active_connections:
            for connection in self.active_connections[user_id]:
                await connection.send_json(message)