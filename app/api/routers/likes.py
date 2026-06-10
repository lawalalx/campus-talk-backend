# app/api/routers/likes.py
from fastapi import APIRouter, Depends, status, HTTPException
import uuid
from sqlmodel import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.session import get_session
from app.core.auth import get_current_user_dependency
from app.db.models import User, Like, Post, Comment
from app.core.config import settings
from app.db.repositories.base import BaseRepository
from app.schemas.auth import TokenUser
from app.services.access_control import can_view_post, get_user_institution_ids

router = APIRouter()
like_repo = BaseRepository(Like)
post_repo = BaseRepository(Post)
comment_repo = BaseRepository(Comment)

@router.post("/post/{post_id}", status_code=status.HTTP_204_NO_CONTENT)
async def toggle_like_post(
    post_id: str,
    session: AsyncSession = Depends(get_session),
    current_user: TokenUser = Depends(get_current_user_dependency(settings))
):
    post = await post_repo.get(session, id=post_id, options=[selectinload(Post.author)])
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")

    user_institution_ids = await get_user_institution_ids(session, current_user.id)
    if not can_view_post(post, current_user, user_institution_ids):
        raise HTTPException(status_code=403, detail="You do not have permission to interact with this post")
        
    # Check if a like already exists
    statement = select(Like).where(Like.user_id == current_user.id, Like.post_id == post_id)
    result = await session.execute(statement)
    existing_like = result.scalars().first()
    
    if existing_like:
        # Unlike
        await session.delete(existing_like)
        await session.commit()
    else:
        # Like
        like = Like(user_id=current_user.id, post_id=post_id)
        await like_repo.create(session, obj_in=like)
    
    return


@router.post("/comment/{comment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def toggle_like_comment(
    comment_id: str,
    session: AsyncSession = Depends(get_session),
    current_user: TokenUser = Depends(get_current_user_dependency(settings=settings))
):
    comment = await comment_repo.get(session, id=comment_id, options=[selectinload(Comment.post)])
    if not comment:
        raise HTTPException(status_code=404, detail="Comment not found")

    if not comment.post:
        raise HTTPException(status_code=404, detail="Parent post not found")

    user_institution_ids = await get_user_institution_ids(session, current_user.id)
    if not can_view_post(comment.post, current_user, user_institution_ids):
        raise HTTPException(status_code=403, detail="You do not have permission to interact with this comment")

    stmt = select(Like).where(Like.user_id == current_user.id, Like.comment_id == comment_id)
    result = await session.execute(stmt)
    existing_like = result.scalars().first()

    if existing_like:
        await session.delete(existing_like)
        await session.commit()
    else:
        like = Like(user_id=current_user.id, comment_id=comment_id)
        await like_repo.create(session, obj_in=like)

    return
