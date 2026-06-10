# app/core/manager.py
from typing import Dict, List
from fastapi import WebSocket
import logging

logger = logging.getLogger(__name__)

class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, List[WebSocket]] = {}
        self.conversation_connections: Dict[str, List[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, user_id: str):
        await websocket.accept()
        if user_id not in self.active_connections:
            self.active_connections[user_id] = []
        self.active_connections[user_id].append(websocket)
        logger.info(f"WebSocket connected for user {user_id}")

    def disconnect(self, websocket: WebSocket, user_id: str):
        if user_id in self.active_connections:
            self.active_connections[user_id].remove(websocket)
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]
        logger.info(f"WebSocket disconnected for user {user_id}")

    async def send_personal_message(self, message: str, user_id: str):
        if user_id in self.active_connections:
            for connection in self.active_connections[user_id]:
                await connection.send_text(message)

    async def connect_conversation(self, websocket: WebSocket, conversation_id: str):
        await websocket.accept()
        if conversation_id not in self.conversation_connections:
            self.conversation_connections[conversation_id] = []
        self.conversation_connections[conversation_id].append(websocket)
        logger.info("WebSocket connected for conversation %s", conversation_id)

    def disconnect_conversation(self, websocket: WebSocket, conversation_id: str):
        if conversation_id in self.conversation_connections:
            if websocket in self.conversation_connections[conversation_id]:
                self.conversation_connections[conversation_id].remove(websocket)
            if not self.conversation_connections[conversation_id]:
                del self.conversation_connections[conversation_id]
        logger.info("WebSocket disconnected for conversation %s", conversation_id)

    async def send_conversation_message(self, message: str, conversation_id: str):
        if conversation_id in self.conversation_connections:
            stale_connections: List[WebSocket] = []
            for connection in self.conversation_connections[conversation_id]:
                try:
                    await connection.send_text(message)
                except Exception:
                    stale_connections.append(connection)

            if stale_connections:
                self.conversation_connections[conversation_id] = [
                    conn for conn in self.conversation_connections[conversation_id]
                    if conn not in stale_connections
                ]

# Single global instance
manager = ConnectionManager()
