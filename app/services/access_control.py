from typing import Optional, Set

from sqlalchemy import and_, or_, true
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models import Post, PostPrivacy, User, UserRole
from app.schemas.auth import TokenUser


async def get_user_institution_ids(session: AsyncSession, user_id: str) -> Set[str]:
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

    institution_ids: Set[str] = set()

    if user.student_profile and user.student_profile.institution_id:
        institution_ids.add(user.student_profile.institution_id)

    if user.institution_profile and user.institution_profile.institution_id:
        institution_ids.add(user.institution_profile.institution_id)

    return institution_ids


def is_admin(current_user: Optional[TokenUser]) -> bool:
    if not current_user:
        return False
    return current_user.role in (UserRole.ADMIN, UserRole.ADMIN.value)


def can_view_post(
    post: Post,
    current_user: Optional[TokenUser],
    user_institution_ids: Set[str],
) -> bool:
    if is_admin(current_user):
        return True

    if post.privacy == PostPrivacy.PUBLIC:
        return True

    if not current_user:
        return False

    if post.author_id == current_user.id:
        return True

    if post.privacy == PostPrivacy.SCHOOL_ONLY:
        return bool(post.school_scope and post.school_scope in user_institution_ids)

    return False


async def build_post_visibility_filter(
    session: AsyncSession,
    current_user: Optional[TokenUser],
):
    if is_admin(current_user):
        return true()

    if not current_user:
        return Post.privacy == PostPrivacy.PUBLIC

    institution_ids = await get_user_institution_ids(session, current_user.id)
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
