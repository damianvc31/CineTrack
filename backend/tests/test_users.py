import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_update_profile(async_client: AsyncClient):
    """Verifica actualización exitosa de perfil (bio, país, ciudad, avatar)."""
    reg_resp = await async_client.post("/api/v1/auth/register", json={
        "nombre_usuario": "user_profile_test",
        "password": "password123",
        "pais": "Uruguay"
    })
    assert reg_resp.status_code == 201
    token = reg_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    patch_resp = await async_client.patch("/api/v1/users/me", headers=headers, json={
        "pais": "Argentina",
        "ciudad": "Buenos Aires",
        "descripcion": "Film enthusiast and reviewer",
        "avatar_url": "https://example.com/avatar.jpg"
    })
    assert patch_resp.status_code == 200
    updated = patch_resp.json()
    assert updated["nombre_usuario"] == "user_profile_test"
    assert updated["pais"] == "Argentina"
    assert updated["ciudad"] == "Buenos Aires"
    assert updated["descripcion"] == "Film enthusiast and reviewer"
    assert updated["avatar_url"] == "https://example.com/avatar.jpg"


@pytest.mark.asyncio
async def test_change_password(async_client: AsyncClient):
    """Verifica cambio de contraseña seguro validando la contraseña actual."""
    reg_resp = await async_client.post("/api/v1/auth/register", json={
        "nombre_usuario": "pwd_test_user",
        "password": "oldpassword123"
    })
    assert reg_resp.status_code == 201
    token = reg_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Intento con contraseña actual incorrecta
    fail_resp = await async_client.post("/api/v1/users/me/change-password", headers=headers, json={
        "current_password": "wrongpassword",
        "new_password": "newpassword123"
    })
    assert fail_resp.status_code == 400
    assert "incorrecta" in fail_resp.json()["detail"]

    # Cambio exitoso
    ok_resp = await async_client.post("/api/v1/users/me/change-password", headers=headers, json={
        "current_password": "oldpassword123",
        "new_password": "newpassword123"
    })
    assert ok_resp.status_code == 200

    # Verificar que el login funciona con la nueva clave y falla con la vieja
    login_old = await async_client.post("/api/v1/auth/login", json={
        "nombre_usuario": "pwd_test_user",
        "password": "oldpassword123"
    })
    assert login_old.status_code == 401

    login_new = await async_client.post("/api/v1/auth/login", json={
        "nombre_usuario": "pwd_test_user",
        "password": "newpassword123"
    })
    assert login_new.status_code == 200


@pytest.mark.asyncio
async def test_user_stats_extended_fields(async_client: AsyncClient):
    """Verifica que /users/me/stats exponga avg_movies_per_week y seasons_completed_count."""
    reg_resp = await async_client.post("/api/v1/auth/register", json={
        "nombre_usuario": "stats_user_test",
        "password": "password123"
    })
    assert reg_resp.status_code == 201
    token = reg_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    stats_resp = await async_client.get("/api/v1/users/me/stats", headers=headers)
    assert stats_resp.status_code == 200
    data = stats_resp.json()
    assert "avg_movies_per_week" in data
    assert "seasons_completed_count" in data
    assert isinstance(data["avg_movies_per_week"], (int, float))
    assert isinstance(data["seasons_completed_count"], int)
