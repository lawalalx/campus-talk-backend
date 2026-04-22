# app/api/routers/posts.py
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy import and_, or_, true, delete
from sqlmodel import select
from typing import List, Optional
import cloudinary
import cloudinary.uploader

from app.core.config import settings
from app.core.auth import get_current_user_dependency, get_optional_current_user_dependency
from app.db.session import get_session
from app.db.models import (
    Media,
    MediaType,
    PostPrivacy,
    User,
    Post,
    UserRole,
    PostType,
    Comment,
    Like,
    Complaint,
    Sentiment,
)
from app.schemas.auth import TokenUser
from app.schemas.post import PostCreate, PostPublic, PresignedUrlResponse
from app.db.repositories.post_repo import post_repo
from app.services.media_service import media_service
from app.api.deps import pagination_params
from app.tasks.media_tasks import process_video_thumbnail

router = APIRouter()


async def _get_user_institution_ids(session: AsyncSession, user_id: str) -> set[str]:
    """Return institution IDs linked to a user."""
    user = await session.get(
        User,
        user_id,
        options=[
            selectinload(User.student_profile),
            selectinload(User.institution_profile),
        ],
    )

    if not user:
        return set()

    institution_ids: set[str] = set()

    if user.institution_profile:
        if user.institution_profile.institution_id:
            institution_ids.add(user.institution_profile.institution_id)

    if user.student_profile:
        if user.student_profile.institution_id:
            institution_ids.add(user.student_profile.institution_id)

    return institution_ids


def _is_admin(current_user: Optional[TokenUser]) -> bool:
    if not current_user:
        return False
    return current_user.role == UserRole.ADMIN or current_user.role == UserRole.ADMIN.value


async def _build_feed_visibility_filter(
    session: AsyncSession,
    current_user: Optional[TokenUser],
):
    """Build SQL filter for post visibility rules across feed endpoints."""
    if _is_admin(current_user):
        return true()

    if not current_user:
        return Post.privacy == PostPrivacy.PUBLIC

    institution_ids = await _get_user_institution_ids(session, current_user.id)
    visibility_conditions = [
        Post.privacy == PostPrivacy.PUBLIC,
        Post.author_id == current_user.id,
    ]

    if institution_ids:
        visibility_conditions.append(
            and_(
                Post.privacy == PostPrivacy.SCHOOL_ONLY,
                Post.school_scope.in_(institution_ids),
            )
        )

    return or_(*visibility_conditions)


def _can_delete_post(current_user: TokenUser, post: Post) -> bool:
    """Only post author or admin can delete a post."""
    if post.author_id == current_user.id:
        return True
    if current_user.role == UserRole.ADMIN:
        return True
    return False


@router.post("/", response_model=PostPublic, status_code=status.HTTP_201_CREATED)
async def create_post(
    *,
    session: AsyncSession = Depends(get_session),
    background_tasks: BackgroundTasks,
    current_user: TokenUser = Depends(get_current_user_dependency(settings=settings)),

    # form fields
    content: str = Form(...),
    privacy: PostPrivacy = Form(PostPrivacy.PUBLIC),
    post_type: PostType = Form(PostType.POST),
    is_school_scope: bool = Form(False),

    # media
    images: Optional[list[UploadFile]] = File(None),
    video: Optional[UploadFile] = File(None),
):
    """
    Create a new post (regular or reel).

    For posts with media:
    - Get a presigned URL from `/media/presigned-url`.
    - Upload the file to S3.
    - Include the media URL in the `content` or media list.
    """

    # -----------------------------
    # VALIDATION
    # -----------------------------
    if images and video:
        raise HTTPException(400, "Cannot upload images and video together")

    if post_type == PostType.REEL and not video:
        raise HTTPException(400, "Reel post requires a video")

    if post_type == PostType.POST and not (content or images):
        raise HTTPException(400, "Post must have text or image")

    # -----------------------------
    # SCHOOL SCOPE AUTO-SET
    # -----------------------------
    # -----------------------------
    # GET INSTITUTION ID
    # -----------------------------
    final_institution_scope = None
    if is_school_scope:
        user_scopes = await _get_user_institution_ids(session, current_user.id)
        if not user_scopes:
            raise HTTPException(400, "User is not linked to a valid institution")

        # Store school scope as institution_id for consistent filtering.
        final_institution_scope = sorted(user_scopes)[0]

    post = Post(
        author_id=current_user.id,
        content=content,
        post_type=post_type,
        privacy=privacy,
        school_scope=final_institution_scope,
    )

    session.add(post)
    await session.flush()

    # -----------------------------
    # HANDLE MEDIA UPLOADS
    # -----------------------------
    media_objects: list[Media] = []

    if images:
        for img in images:
            if img.content_type not in ["image/jpeg", "image/png"]:
                raise HTTPException(400, "Only JPG and PNG images allowed")

            upload = cloudinary.uploader.upload(
                img.file,
                folder="posts/images",
                resource_type="image",
            )

            media_objects.append(
                Media(
                    post_id=post.id,
                    media_type=MediaType.IMAGE,
                    url=upload["secure_url"],
                    file_metadata={
                        "width": upload.get("width"),
                        "height": upload.get("height"),
                        "format": upload.get("format"),
                        "bytes": upload.get("bytes"),
                    },
                )
            )

    if video:
        if video.content_type not in ["video/mp4", "video/quicktime"]:
            raise HTTPException(400, "Only MP4 or MOV videos allowed")

        upload = cloudinary.uploader.upload(
            video.file,
            folder="posts/videos",
            resource_type="video",
        )

        media_objects.append(
            Media(
                post_id=post.id,
                media_type=MediaType.VIDEO,
                url=upload["secure_url"],
                file_metadata={
                    "duration": upload.get("duration"),
                    "format": upload.get("format"),
                    "bytes": upload.get("bytes"),
                },
            )
        )

    session.add_all(media_objects)

    # -----------------------------
    # COMMIT ONCE (ATOMIC)
    # -----------------------------
    await session.commit()
    await session.refresh(post)

    # -----------------------------
    # BACKGROUND VIDEO PROCESSING
    # -----------------------------
    if post_type == PostType.REEL and media_objects:
        background_tasks.add_task(
            process_video_thumbnail,
            post_id=post.id,
            video_url=media_objects[0].url,
        )

    # -----------------------------
    # RESPONSE
    # -----------------------------
    result = await session.execute(
        select(Post)
        .options(
            selectinload(Post.author),
            selectinload(Post.media),
        )
        .where(Post.id == post.id)
    )

    return result.scalar_one()






@router.get("/media/presigned-url", response_model=PresignedUrlResponse)
async def get_presigned_upload_url(
    *,
    file_name: str,
    file_type: str,  # e.g., "image/jpeg", "video/mp4"
    current_user: TokenUser = Depends(get_current_user_dependency(settings=settings)),
):
    """
    Get a pre-signed S3 upload URL to directly upload media from the client.
    """
    url_data = media_service.generate_presigned_upload_url(file_name, file_type)
    if not url_data:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate upload URL. Please try again later.",
        )
    upload_url = url_data["upload_url"]
    # Fix internal Docker hostname for local dev
    if upload_url.startswith("http://minio:9000"):
        upload_url = upload_url.replace("http://minio:9000", "http://localhost:9000")
    return {"upload_url": upload_url, "file_key": url_data["file_key"]}


@router.get("/", response_model=List[PostPublic])
async def read_posts(
    *,
    session: AsyncSession = Depends(get_session),
    pagination: pagination_params = Depends(),
    current_user: Optional[TokenUser] = Depends(get_optional_current_user_dependency(settings=settings)),
    school_scope: Optional[str] = None,
):
    """
    Retrieve posts for the main feed (type = POST).
    Can filter by school scope.
    """
    stmt = (
        select(Post)
        .where(Post.post_type == PostType.POST)
        .where(await _build_feed_visibility_filter(session, current_user))
        .options(selectinload(Post.author))
        .order_by(Post.created_at.desc())
    )
    if school_scope:
        stmt = stmt.where(Post.school_scope == school_scope)

    stmt = stmt.offset(pagination.skip).limit(pagination.limit)
    posts = (await session.execute(stmt)).scalars().all()
    post_ids = [post.id for post in posts]
    # Get likes for all posts in one query
    likes_query = select(Like.post_id, Like.user_id).where(Like.post_id.in_(post_ids))
    likes_result = await session.execute(likes_query)
    likes = likes_result.fetchall()
    # Build likes_count and is_liked map
    from collections import defaultdict
    likes_count_map = defaultdict(int)
    user_liked_map = defaultdict(set)
    for post_id, user_id in likes:
        likes_count_map[post_id] += 1
        user_liked_map[post_id].add(user_id)

    user_id = getattr(current_user, 'id', None)
    post_list = []
    for post in posts:
        post_dict = post.__dict__.copy()
        post_dict['author'] = post.author
        # Convert ORM media objects to dicts matching MediaCreate
        post_dict['media'] = [
            {
                "media_type": m.media_type,
                "url": m.url,
                "file_metadata": m.file_metadata
            }
            for m in post.media
        ]
        post_dict['likes_count'] = likes_count_map.get(post.id, 0)
        post_dict['is_liked'] = user_id in user_liked_map.get(post.id, set()) if user_id else False
        post_list.append(PostPublic(**post_dict))
    return post_list


@router.get("/reels", response_model=List[PostPublic])
async def read_reels(
    *,
    session: AsyncSession = Depends(get_session),
    pagination: pagination_params = Depends(),
    current_user: Optional[TokenUser] = Depends(get_optional_current_user_dependency(settings=settings)),
):
    """
    Retrieve all posts of type 'reel'.
    """
    stmt = (
        select(Post)
        .where(Post.post_type == PostType.REEL)
        .where(await _build_feed_visibility_filter(session, current_user))
        .options(selectinload(Post.author))
        .order_by(Post.created_at.desc())
        .offset(pagination.skip)
        .limit(pagination.limit)
    )
    result = await session.execute(stmt)
    return result.scalars().all()


@router.get("/{post_id}", response_model=PostPublic)
async def read_post(
    *,
    post_id: str,
    session: AsyncSession = Depends(get_session),
    current_user: Optional[TokenUser] = Depends(get_optional_current_user_dependency(settings=settings)),
):
    """
    Get a single post by its ID, including author info.
    """
    post = await post_repo.get_by_id_with_author(session, id=post_id)
    if not post:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")

    if not _is_admin(current_user):
        visibility_filter = await _build_feed_visibility_filter(session, current_user)
        visibility_stmt = select(Post.id).where(Post.id == post_id).where(visibility_filter)
        visible = (await session.execute(visibility_stmt)).scalars().first()
        if not visible:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You do not have permission to view this post.")

    # Get likes_count and is_liked for this post
    likes_count = await session.scalar(select(Like).where(Like.post_id == post_id).count())
    user_id = getattr(current_user, 'id', None)
    is_liked = False
    if user_id:
        is_liked = await session.scalar(select(Like).where(Like.post_id == post_id, Like.user_id == user_id).exists())
    post_dict = post.__dict__.copy()
    post_dict['author'] = post.author
    post_dict['media'] = [
        {
            "media_type": m.media_type,
            "url": m.url,
            "file_metadata": m.file_metadata
        }
        for m in post.media
    ]
    post_dict['likes_count'] = likes_count or 0
    post_dict['is_liked'] = is_liked
    return PostPublic(**post_dict)





@router.get("/institution/{institution_id}", response_model=List[PostPublic])
async def get_posts_by_institution(
    *,
    institution_id: str,
    session: AsyncSession = Depends(get_session),
    pagination: pagination_params = Depends(),
    current_user: Optional[TokenUser] = Depends(get_optional_current_user_dependency(settings=settings)),
    post_type: Optional[PostType] = None
):
    """
    Fetch all posts belonging to a specific institution by ID.
    """
    stmt = (
        select(Post)
        .where(Post.school_scope == institution_id)
        .where(await _build_feed_visibility_filter(session, current_user))
        .options(
            selectinload(Post.author),
            selectinload(Post.media)
        )
        .order_by(Post.created_at.desc())
    )
    
    if post_type:
        stmt = stmt.where(Post.post_type == post_type)

    stmt = stmt.offset(pagination.skip).limit(pagination.limit)
    
    result = await session.execute(stmt)
    return result.scalars().all()




@router.delete("/{post_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_post(
    *,
    session: AsyncSession = Depends(get_session),
    post_id: str,
    current_user: TokenUser = Depends(get_current_user_dependency(settings=settings)),
):
    """Delete a post if the caller is the author or an admin."""
    post = await post_repo.get(session, id=post_id)
    if not post:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")

    if not _can_delete_post(current_user, post):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to delete this post.",
        )

    # Delete dependent rows explicitly to avoid FK violations in schemas
    # where DB-level ON DELETE CASCADE is not configured.
    comment_ids = (
        await session.execute(select(Comment.id).where(Comment.post_id == post.id))
    ).scalars().all()

    await session.execute(delete(Media).where(Media.post_id == post.id))

    if comment_ids:
        await session.execute(
            delete(Like).where(
                or_(
                    Like.post_id == post.id,
                    Like.comment_id.in_(comment_ids),
                )
            )
        )
        await session.execute(
            delete(Complaint).where(
                or_(
                    Complaint.reported_post_id == post.id,
                    Complaint.reported_comment_id.in_(comment_ids),
                )
            )
        )
        await session.execute(delete(Sentiment).where(Sentiment.comment_id.in_(comment_ids)))
    else:
        await session.execute(delete(Like).where(Like.post_id == post.id))
        await session.execute(delete(Complaint).where(Complaint.reported_post_id == post.id))

    await session.execute(delete(Sentiment).where(Sentiment.post_id == post.id))
    await session.execute(delete(Comment).where(Comment.post_id == post.id))

    await session.delete(post)
    await session.commit()
