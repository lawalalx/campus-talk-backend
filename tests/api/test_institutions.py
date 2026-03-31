"""
Integration tests for institution endpoints (timeline, posts, uploads, chatbot).
"""
import pytest
from httpx import AsyncClient
from sqlmodel import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import User, Institution, StudentProfile, InstitutionProfile, Post
from app.core.auth import create_access_token, get_password_hash


@pytest.mark.asyncio
async def test_institution_timeline_student(
    client: AsyncClient,
    db_session: AsyncSession,
):
    """Test that a student can fetch their institution's timeline."""
    # Create institution
    inst = Institution(
        id="test-inst",
        institution_name="Test University",
        institution_email="test@uni.edu",
        institution_description="A test university",
        institution_location="Test Location",
        institution_website="https://test.edu",
        institution_profile_picture="https://example.com/logo.jpg",
    )
    db_session.add(inst)
    await db_session.commit()
    await db_session.refresh(inst)

    # Create student user
    student = User(
        email="student@test.edu",
        full_name="Test Student",
        hashed_password=get_password_hash("testpass"),
        role="student",
        is_verified=True,
    )
    db_session.add(student)
    await db_session.commit()
    await db_session.refresh(student)

    # Link student to institution
    student_profile = StudentProfile(
        user_id=student.id,
        institution_id=inst.id,
        institution_name=inst.institution_name,
        matric_number="12345",
        faculty="Engineering",
        department="CS",
    )
    db_session.add(student_profile)
    await db_session.commit()

    # Create a post for the institution
    admin = User(
        email="admin@test.edu",
        full_name="Test Admin",
        hashed_password=get_password_hash("testpass"),
        role="institution",
        is_verified=True,
    )
    db_session.add(admin)
    await db_session.commit()
    await db_session.refresh(admin)

    post = Post(
        author_id=admin.id,
        content="Welcome to Test University!",
        post_type="post",
        privacy="school_only",
        school_scope=inst.id,
    )
    db_session.add(post)
    await db_session.commit()

    # Generate token for student
    token = create_access_token(student)

    # Fetch timeline
    response = await client.get(
        "/api/v1/institutions/timeline/my-institution",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["institution"]["id"] == "test-inst"
    assert data["institution"]["institution_name"] == "Test University"
    assert len(data["posts"]) == 1
    assert data["posts"][0]["content"] == "Welcome to Test University!"


@pytest.mark.asyncio
async def test_institution_post_creation_admin_only(
    client: AsyncClient,
    db_session: AsyncSession,
):
    """Test that only institution admins can create institution posts."""
    # Create institution
    inst = Institution(
        id="test-inst2",
        institution_name="Test University 2",
        institution_email="test2@uni.edu",
        institution_description="Another test university",
        institution_location="Test Location 2",
        institution_website="https://test2.edu",
    )
    db_session.add(inst)
    await db_session.commit()
    await db_session.refresh(inst)

    # Create general user (non-admin)
    general_user = User(
        email="general@test.edu",
        full_name="General User",
        hashed_password=get_password_hash("testpass"),
        role="general",
        is_verified=True,
    )
    db_session.add(general_user)
    await db_session.commit()
    await db_session.refresh(general_user)

    token = create_access_token(general_user)

    # Try to create post as general user (should fail)
    response = await client.post(
        "/api/v1/institutions/test-inst2/posts",
        params={"content": "This should fail", "post_type": "post"},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 403
    assert "Only institution accounts" in response.json()["detail"]


@pytest.mark.asyncio
async def test_institution_post_mirror_to_general(
    client: AsyncClient,
    db_session: AsyncSession,
):
    """Test that admin can mirror posts to general feed."""
    # Create institution
    inst = Institution(
        id="test-inst3",
        institution_name="Mirror Test Uni",
        institution_email="mirror@uni.edu",
        institution_description="Mirror test",
        institution_location="Test",
        institution_website="https://mirror.edu",
    )
    db_session.add(inst)
    await db_session.commit()
    await db_session.refresh(inst)

    # Create admin user
    admin = User(
        email="admin2@test.edu",
        full_name="Admin User",
        hashed_password=get_password_hash("testpass"),
        role="institution",
        is_verified=True,
    )
    db_session.add(admin)
    await db_session.commit()
    await db_session.refresh(admin)

    # Link admin to institution
    admin_profile = InstitutionProfile(
        user_id=admin.id,
        institution_id=inst.id,
        institution_name=inst.institution_name,
        institution_email=inst.institution_email or "",
    )
    db_session.add(admin_profile)
    await db_session.commit()

    token = create_access_token(admin)

    # Create post with mirror_to_general=true
    response = await client.post(
        "/api/v1/institutions/test-inst3/posts",
        params={
            "content": "This is a mirrored post",
            "post_type": "post",
            "mirror_to_general": True,
        },
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 201
    post_data = response.json()
    assert post_data["privacy"] == "public"
    assert post_data["school_scope"] is None

    # Create post without mirroring (school-only)
    response2 = await client.post(
        "/api/v1/institutions/test-inst3/posts",
        params={
            "content": "School-only post",
            "post_type": "post",
            "mirror_to_general": False,
        },
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response2.status_code == 201
    post_data2 = response2.json()
    assert post_data2["privacy"] == "school_only"
    assert post_data2["school_scope"] == "test-inst3"


@pytest.mark.asyncio
async def test_institution_chatbot_query(
    client: AsyncClient,
    db_session: AsyncSession,
):
    """Test that users can query the institution chatbot."""
    # Create institution
    inst = Institution(
        id="chat-inst",
        institution_name="ChatBot Test Uni",
        institution_email="chat@uni.edu",
        institution_description="Chatbot test",
        institution_location="Test",
        institution_website="https://chat.edu",
    )
    db_session.add(inst)
    await db_session.commit()
    await db_session.refresh(inst)

    # Create a user
    user = User(
        email="user@test.edu",
        full_name="Test User",
        hashed_password=get_password_hash("testpass"),
        role="general",
        is_verified=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    token = create_access_token(user)

    # Query chatbot (should work even without documents, returning a message)
    response = await client.post(
        "/api/v1/institutions/chat-inst/chatbot",
        params={"query": "What are your programs?"},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["institution_id"] == "chat-inst"
