import json
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from typing import List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select
from sqlalchemy.orm import selectinload
from sqlalchemy import func

from app.db.session import get_session
from app.core.auth import get_current_user_dependency
from app.core.config import settings
from app.db.models import Conversation, ConversationUserLink, Message, User
from app.schemas.messages import ConversationCreate, ConversationPublic, MessageCreate, MessagePublic
from app.schemas.auth import TokenUser
from app.db.repositories.base import BaseRepository
from app.core.manager import manager
from app.services.access_control import get_user_institution_ids
from app.services.sentiment_service import store_message_sentiment

router = APIRouter()
conversation_repo = BaseRepository(Conversation)
message_repo = BaseRepository(Message)


class DirectMessageCreate(BaseModel):
    to: str
    content: str


async def _ensure_conversation_member(session: AsyncSession, conversation_id: str, user_id: str) -> None:
    stmt = select(ConversationUserLink).where(
        ConversationUserLink.conversation_id == conversation_id,
        ConversationUserLink.user_id == user_id,
    )
    res = await session.execute(stmt)
    if not res.scalars().first():
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You are not a member of this conversation")


async def _get_or_create_direct_conversation(
    session: AsyncSession,
    *,
    current_user_id: str,
    other_user_id: str,
) -> Conversation:
    if current_user_id == other_user_id:
        raise HTTPException(status_code=400, detail="You cannot message yourself")

    other_user = await session.get(User, other_user_id)
    if not other_user:
        raise HTTPException(status_code=404, detail="Recipient user not found")

    stmt = (
        select(Conversation)
        .join(ConversationUserLink, Conversation.id == ConversationUserLink.conversation_id)
        .where(ConversationUserLink.user_id == current_user_id)
        .where(Conversation.is_group == False)
        .options(selectinload(Conversation.members))
    )
    current_user_conversations = (await session.execute(stmt)).scalars().all()
    for conv in current_user_conversations:
        member_ids = {member.id for member in conv.members}
        if member_ids == {current_user_id, other_user_id}:
            return conv

    conv = Conversation(is_group=False, created_by=current_user_id)
    session.add(conv)
    await session.commit()
    await session.refresh(conv)

    session.add(ConversationUserLink(user_id=current_user_id, conversation_id=conv.id))
    session.add(ConversationUserLink(user_id=other_user_id, conversation_id=conv.id))
    await session.commit()

    conv = await session.get(conv.__class__, conv.id, options=[selectinload(Conversation.members)])
    return conv


async def _resolve_institution_scope_for_conversation(
    session: AsyncSession,
    conversation: Conversation,
    fallback_user_id: str,
) -> str | None:
    member_ids = [member.id for member in conversation.members]
    if not member_ids:
        member_ids = [fallback_user_id]

    member_scopes: list[set[str]] = []
    for member_id in member_ids:
        member_scopes.append(await get_user_institution_ids(session, member_id))

    if member_scopes:
        intersection = set.intersection(*member_scopes) if all(member_scopes) else set()
        if intersection:
            return sorted(intersection)[0]

    fallback_scopes = await get_user_institution_ids(session, fallback_user_id)
    if fallback_scopes:
        return sorted(fallback_scopes)[0]

    return None


async def _persist_message_with_side_effects(
    *,
    session: AsyncSession,
    conversation: Conversation,
    sender_id: str,
    content: str,
    attachments: dict | None = None,
) -> Message:
    msg = Message(
        conversation_id=conversation.id,
        sender_id=sender_id,
        content=content,
        attachments=attachments or {},
    )
    new_msg = await message_repo.create(session, obj_in=msg)

    institution_id = await _resolve_institution_scope_for_conversation(
        session,
        conversation=conversation,
        fallback_user_id=sender_id,
    )
    await store_message_sentiment(
        session,
        message_id=new_msg.id,
        conversation_id=conversation.id,
        institution_id=institution_id,
        content=content,
    )

    await manager.send_conversation_message(
        json.dumps({
            "type": "message.created",
            "conversation_id": conversation.id,
            "message": {
                "id": new_msg.id,
                "sender_id": new_msg.sender_id,
                "content": new_msg.content,
                "attachments": new_msg.attachments,
                "created_at": str(new_msg.created_at),
            },
        }),
        conversation.id,
    )

    return new_msg


@router.post("/", response_model=ConversationPublic, status_code=status.HTTP_201_CREATED)
async def create_conversation(
    conversation_in: ConversationCreate,
    session: AsyncSession = Depends(get_session),
    current_user: TokenUser = Depends(get_current_user_dependency(settings=settings)),
):
    """Create a new conversation and add members."""
    conv = Conversation(title=conversation_in.title, is_group=conversation_in.is_group, created_by=current_user.id)
    session.add(conv)
    await session.commit()
    await session.refresh(conv)

    # Add current user as member
    link = ConversationUserLink(user_id=current_user.id, conversation_id=conv.id)
    session.add(link)

    # Add additional members if provided
    if conversation_in.member_ids:
        for uid in conversation_in.member_ids:
            # skip if trying to add self again
            if uid == current_user.id:
                continue
            user = await session.get(User, uid)
            if user:
                session.add(ConversationUserLink(user_id=uid, conversation_id=conv.id))

    await session.commit()
    await session.refresh(conv)
    return conv


@router.get("/", response_model=List[ConversationPublic])
async def list_conversations(
    session: AsyncSession = Depends(get_session),
    current_user: TokenUser = Depends(get_current_user_dependency(settings=settings)),
):
    stmt = (
        select(Conversation)
        .join(ConversationUserLink, Conversation.id == ConversationUserLink.conversation_id)
        .where(ConversationUserLink.user_id == current_user.id)
        .options(selectinload(Conversation.members), selectinload(Conversation.messages))
        .order_by(Conversation.created_at.desc())
    )
    result = await session.execute(stmt)
    return result.scalars().all()


@router.get("/me", response_model=List[ConversationPublic])
async def get_my_conversations(
    session: AsyncSession = Depends(get_session),
    current_user: TokenUser = Depends(get_current_user_dependency(settings=settings)),
):
    stmt = (
        select(Conversation)
        .join(ConversationUserLink, Conversation.id == ConversationUserLink.conversation_id)
        .where(ConversationUserLink.user_id == current_user.id)
        .options(selectinload(Conversation.members), selectinload(Conversation.messages))
        .order_by(Conversation.created_at.desc())
    )
    result = await session.execute(stmt)
    convs = result.scalars().all()
    return convs


@router.post("/{conversation_id}/messages", response_model=MessagePublic, status_code=status.HTTP_201_CREATED)
async def send_message(
    conversation_id: str,
    message_in: MessageCreate,
    session: AsyncSession = Depends(get_session),
    current_user: TokenUser = Depends(get_current_user_dependency(settings=settings)),
):
    await _ensure_conversation_member(session, conversation_id, current_user.id)

    conversation = await session.get(
        Conversation,
        conversation_id,
        options=[selectinload(Conversation.members)],
    )
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    new_msg = await _persist_message_with_side_effects(
        session=session,
        conversation=conversation,
        sender_id=current_user.id,
        content=message_in.content,
        attachments=message_in.attachments,
    )
    return new_msg


@router.get("/{conversation_id}/messages", response_model=List[MessagePublic])
async def get_messages(
    conversation_id: str,
    session: AsyncSession = Depends(get_session),
    current_user: TokenUser = Depends(get_current_user_dependency(settings=settings)),
    limit: int = 50,
    offset: int = 0,
):
    await _ensure_conversation_member(session, conversation_id, current_user.id)

    stmt = (
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.created_at.desc())
        .options(selectinload(Message.sender))
        .offset(offset)
        .limit(limit)
    )
    result = await session.execute(stmt)
    messages = result.scalars().all()
    return list(reversed(messages))  # return chronological order


@router.get("/conversation/{user_id}", response_model=List[MessagePublic])
async def get_conversation_with_user(
    user_id: str,
    session: AsyncSession = Depends(get_session),
    current_user: TokenUser = Depends(get_current_user_dependency(settings=settings)),
):
    conversation = await _get_or_create_direct_conversation(
        session,
        current_user_id=current_user.id,
        other_user_id=user_id,
    )

    stmt = (
        select(Message)
        .where(Message.conversation_id == conversation.id)
        .order_by(Message.created_at.asc())
        .options(selectinload(Message.sender))
    )
    result = await session.execute(stmt)
    return result.scalars().all()


@router.post("/", response_model=MessagePublic, status_code=status.HTTP_201_CREATED)
async def send_direct_message(
    payload: DirectMessageCreate,
    session: AsyncSession = Depends(get_session),
    current_user: TokenUser = Depends(get_current_user_dependency(settings=settings)),
):
    conversation = await _get_or_create_direct_conversation(
        session,
        current_user_id=current_user.id,
        other_user_id=payload.to,
    )

    return await _persist_message_with_side_effects(
        session=session,
        conversation=conversation,
        sender_id=current_user.id,
        content=payload.content,
    )


@router.put("/{message_id}/read", response_model=MessagePublic)
async def mark_message_as_read(
    message_id: str,
    session: AsyncSession = Depends(get_session),
    current_user: TokenUser = Depends(get_current_user_dependency(settings=settings)),
):
    message = await session.get(Message, message_id)
    if not message:
        raise HTTPException(status_code=404, detail="Message not found")

    await _ensure_conversation_member(session, message.conversation_id, current_user.id)

    message.is_read = True
    session.add(message)
    await session.commit()
    await session.refresh(message)
    return message
