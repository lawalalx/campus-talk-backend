# tests/api/test_auth.py
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import status

@pytest.mark.asyncio
async def test_register_user(client: AsyncClient, db_session: AsyncSession):
    user_data = {
        "full_name": "Test User",
        "email": "test@example.com",
        "password": "strongpassword",
        "role": "general"
    }
    response = await client.post("/api/v1/auth/register", json=user_data)
    if response.status_code != status.HTTP_201_CREATED:
        print("Register response:", response.status_code, response.text)
    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()["data"]
    assert data["email"] == user_data["email"]
    assert "id" in data

@pytest.mark.asyncio
async def test_login_for_access_token(client: AsyncClient, db_session: AsyncSession):
    # First, register a user
    user_data = {
        "full_name": "loginuser User",
        "email": "login@example.com",
        "password": "strongpassword",
        "role": "general"
    }
    await client.post("/api/v1/auth/register", json=user_data)

    # Then, try to log in
    login_data = {
        "email": "login@example.com",
        "password": "strongpassword"
    }
    response = await client.post("/api/v1/auth/login", json=login_data)
    if response.status_code != status.HTTP_200_OK:
        print("Login response:", response.status_code, response.text)
    assert response.status_code == status.HTTP_200_OK
    data = response.json()["data"]
    assert "campustalk_access_token" in data
    assert data["token_type"] == "bearer"
