import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import create_access_token, get_password_hash
from app.db.models import Institution, InstitutionProfile, Post, PostPrivacy, User, UserRole


async def _create_user(
    session: AsyncSession,
    *,
    email: str,
    full_name: str,
    role: UserRole,
) -> User:
    user = User(
        email=email,
        full_name=full_name,
        hashed_password=get_password_hash("testpass"),
        role=role,
        is_verified=True,
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


async def _create_institution(
    session: AsyncSession,
    *,
    institution_id: str,
    name: str,
    email: str,
) -> Institution:
    institution = Institution(
        id=institution_id,
        institution_name=name,
        institution_email=email,
        institution_description=f"{name} description",
        institution_location="Test City",
        institution_website="https://example.edu",
    )
    session.add(institution)
    await session.commit()
    await session.refresh(institution)
    return institution


async def _link_institution_admin(
    session: AsyncSession,
    *,
    user: User,
    institution: Institution,
) -> None:
    profile = InstitutionProfile(
        user_id=user.id,
        institution_id=institution.id,
        institution_name=institution.institution_name,
        institution_email=institution.institution_email or "",
    )
    session.add(profile)
    await session.commit()


async def _create_post(
    session: AsyncSession,
    *,
    author_id: str,
    content: str,
    privacy: PostPrivacy,
    school_scope: str | None = None,
) -> Post:
    post = Post(
        author_id=author_id,
        content=content,
        post_type="post",
        privacy=privacy,
        school_scope=school_scope,
    )
    session.add(post)
    await session.commit()
    await session.refresh(post)
    return post


def _auth_headers(user: User) -> dict[str, str]:
    token = create_access_token(user)
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_delete_post_author_allowed(client: AsyncClient, db_session: AsyncSession):
    author = await _create_user(
        db_session,
        email="author.delete@example.com",
        full_name="Author Delete",
        role=UserRole.GENERAL,
    )
    post = await _create_post(
        db_session,
        author_id=author.id,
        content="author can delete",
        privacy=PostPrivacy.PUBLIC,
    )

    response = await client.delete(f"/api/v1/posts/{post.id}", headers=_auth_headers(author))
    assert response.status_code == 204


@pytest.mark.asyncio
async def test_delete_post_admin_allowed(client: AsyncClient, db_session: AsyncSession):
    author = await _create_user(
        db_session,
        email="author2.delete@example.com",
        full_name="Author 2",
        role=UserRole.GENERAL,
    )
    admin = await _create_user(
        db_session,
        email="admin.delete@example.com",
        full_name="Admin",
        role=UserRole.ADMIN,
    )
    post = await _create_post(
        db_session,
        author_id=author.id,
        content="admin can delete",
        privacy=PostPrivacy.PUBLIC,
    )

    response = await client.delete(f"/api/v1/posts/{post.id}", headers=_auth_headers(admin))
    assert response.status_code == 204


@pytest.mark.asyncio
async def test_delete_post_same_institution_non_author_forbidden(client: AsyncClient, db_session: AsyncSession):
    institution = await _create_institution(
        db_session,
        institution_id="inst-delete-same",
        name="Delete Same University",
        email="same@uni.edu",
    )

    author = await _create_user(
        db_session,
        email="inst.author@example.com",
        full_name="Institution Author",
        role=UserRole.INSTITUTION,
    )
    same_scope_user = await _create_user(
        db_session,
        email="inst.other@example.com",
        full_name="Institution Other",
        role=UserRole.INSTITUTION,
    )

    await _link_institution_admin(db_session, user=author, institution=institution)
    await _link_institution_admin(db_session, user=same_scope_user, institution=institution)

    post = await _create_post(
        db_session,
        author_id=author.id,
        content="same institution should not delete",
        privacy=PostPrivacy.SCHOOL_ONLY,
        school_scope=institution.id,
    )

    response = await client.delete(f"/api/v1/posts/{post.id}", headers=_auth_headers(same_scope_user))
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_delete_post_other_institution_non_author_forbidden(client: AsyncClient, db_session: AsyncSession):
    institution_a = await _create_institution(
        db_session,
        institution_id="inst-delete-a",
        name="Delete A University",
        email="a@uni.edu",
    )
    institution_b = await _create_institution(
        db_session,
        institution_id="inst-delete-b",
        name="Delete B University",
        email="b@uni.edu",
    )

    author = await _create_user(
        db_session,
        email="inst.author2@example.com",
        full_name="Institution Author 2",
        role=UserRole.INSTITUTION,
    )
    other_scope_user = await _create_user(
        db_session,
        email="inst.other2@example.com",
        full_name="Institution Other 2",
        role=UserRole.INSTITUTION,
    )

    await _link_institution_admin(db_session, user=author, institution=institution_a)
    await _link_institution_admin(db_session, user=other_scope_user, institution=institution_b)

    post = await _create_post(
        db_session,
        author_id=author.id,
        content="other institution should not delete",
        privacy=PostPrivacy.SCHOOL_ONLY,
        school_scope=institution_a.id,
    )

    response = await client.delete(f"/api/v1/posts/{post.id}", headers=_auth_headers(other_scope_user))
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_read_posts_visibility_school_and_followers_rules(client: AsyncClient, db_session: AsyncSession):
    institution = await _create_institution(
        db_session,
        institution_id="inst-visibility",
        name="Visibility University",
        email="visibility@uni.edu",
    )

    author = await _create_user(
        db_session,
        email="visibility.author@example.com",
        full_name="Visibility Author",
        role=UserRole.GENERAL,
    )
    school_member = await _create_user(
        db_session,
        email="visibility.member@example.com",
        full_name="Visibility Member",
        role=UserRole.STUDENT,
    )
    outsider = await _create_user(
        db_session,
        email="visibility.outsider@example.com",
        full_name="Visibility Outsider",
        role=UserRole.GENERAL,
    )

    await _create_post(
        db_session,
        author_id=author.id,
        content="public post",
        privacy=PostPrivacy.PUBLIC,
    )
    await _create_post(
        db_session,
        author_id=author.id,
        content="school-only post",
        privacy=PostPrivacy.SCHOOL_ONLY,
        school_scope=institution.id,
    )
    await _create_post(
        db_session,
        author_id=author.id,
        content="followers-only post",
        privacy=PostPrivacy.FOLLOWERS_ONLY,
    )

    # Link the student to institution via profile data expected by scope checks.
    from app.db.models import StudentProfile

    student_profile = StudentProfile(
        user_id=school_member.id,
        institution_id=institution.id,
        institution_name=institution.institution_name,
    )
    db_session.add(student_profile)
    await db_session.commit()

    anon_response = await client.get("/api/v1/posts/")
    assert anon_response.status_code == 200
    anon_contents = {post["content"] for post in anon_response.json()}
    assert "public post" in anon_contents
    assert "school-only post" not in anon_contents
    assert "followers-only post" not in anon_contents

    member_response = await client.get("/api/v1/posts/", headers=_auth_headers(school_member))
    assert member_response.status_code == 200
    member_contents = {post["content"] for post in member_response.json()}
    assert "public post" in member_contents
    assert "school-only post" in member_contents
    assert "followers-only post" not in member_contents

    outsider_response = await client.get("/api/v1/posts/", headers=_auth_headers(outsider))
    assert outsider_response.status_code == 200
    outsider_contents = {post["content"] for post in outsider_response.json()}
    assert "public post" in outsider_contents
    assert "school-only post" not in outsider_contents
    assert "followers-only post" not in outsider_contents
