# app/main.py
import logging
import json
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from sqlmodel import select
from prometheus_fastapi_instrumentator import Instrumentator

from app.core.config import settings
from app.core.manager import manager
from app.core.auth import decode_token
from app.core.middleware import register_middleware
from app.errors import register_all_errors
from app.db.session import create_tables
from app.db.session import get_async_session_maker
from app.db.models import ConversationUserLink
from app.utils.cache import connect_redis, disconnect_redis
from app.api.routers import (
    auth,
    users,
    posts,
    comments,
    likes,
    channels,
    communities,
    complaints,
    notifications,
    admin,
    messages,
    student_portal,
    institutions,
    chat,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Lifespan manager for startup and shutdown events
@asynccontextmanager
async def lifespan(app: FastAPI):
    # On startup
    logger.info("Starting up...")
    await create_tables()
    await connect_redis()
    yield
    # On shutdown
    logger.info("Shutting down...")
    await disconnect_redis()


app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Backend for the LagTALK microblogging platform.",
    version="0.1.0",
    lifespan=lifespan,
    openapi_url=f"{settings.API_V1_STR}/openapi.json"
)


# Prometheus Metrics Integration
Instrumentator().instrument(app).expose(app)


# CORS Middleware
register_middleware(app)
register_all_errors(app)





# Include API Routers
api_prefix = settings.API_V1_STR
app.include_router(auth.router, prefix=f"{api_prefix}/auth", tags=["Auth"])
app.include_router(admin.router, prefix=f"{api_prefix}/admin", tags=["Admin"])
app.include_router(users.router, prefix=f"{api_prefix}/users", tags=["Users"])

app.include_router(chat.router, prefix=f"{api_prefix}/chats", tags=["Chats"])

app.include_router(posts.router, prefix=f"{api_prefix}/posts", tags=["Posts & Reels"])
app.include_router(comments.router, prefix=f"{api_prefix}/posts/{{post_id}}/comments", tags=["Comments"])
app.include_router(likes.router, prefix=f"{api_prefix}/likes", tags=["Likes"])
app.include_router(channels.router, prefix=f"{api_prefix}/channels", tags=["Channels"])
app.include_router(communities.router, prefix=f"{api_prefix}/communities", tags=["Communities"])
app.include_router(complaints.router, prefix=f"{api_prefix}/complaints", tags=["Complaints"])
app.include_router(notifications.router, prefix=f"{api_prefix}/notifications", tags=["Notifications"])
app.include_router(messages.router, prefix=f"{api_prefix}/messages", tags=["Messages"])
app.include_router(student_portal.router, prefix=f"{api_prefix}/student-portal", tags=["Student Portal"])
app.include_router(institutions.router, prefix=f"{api_prefix}/institutions", tags=["Institutions"])



@app.get("/", tags=["Health Check"])
async def root():
    """Health check endpoint."""
    return {"message": "LagTALK API is running!"}

@app.websocket("/ws/notifications/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: str):
    await manager.connect(websocket, user_id)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket, user_id)


@app.websocket("/ws/messages/{conversation_id}")
async def websocket_messages_endpoint(websocket: WebSocket, conversation_id: str):
    token = websocket.query_params.get("token")
    if not token:
        await websocket.close(code=1008)
        return

    payload = decode_token(token, settings)
    if not payload or not payload.get("id"):
        await websocket.close(code=1008)
        return

    user_id = payload.get("id")

    session_maker = get_async_session_maker()
    async with session_maker() as session:
        membership_stmt = select(ConversationUserLink).where(
            ConversationUserLink.conversation_id == conversation_id,
            ConversationUserLink.user_id == user_id,
        )
        member_row = (await session.execute(membership_stmt)).scalars().first()
        if not member_row:
            await websocket.close(code=1008)
            return

    await manager.connect_conversation(websocket, conversation_id)
    try:
        while True:
            raw_message = await websocket.receive_text()
            await manager.send_conversation_message(
                json.dumps({
                    "type": "message.echo",
                    "conversation_id": conversation_id,
                    "sender_id": user_id,
                    "content": raw_message,
                }),
                conversation_id,
            )
    except WebSocketDisconnect:
        manager.disconnect_conversation(websocket, conversation_id)



if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=10000, reload=True)
