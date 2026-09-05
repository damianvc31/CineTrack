import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_register_user_success(async_client: AsyncClient):
    """Verifica registro exitoso de un usuario nuevo."""
    payload = {
        "nombre_usuario": "alice",
        "password": "secretpassword",
        "pais": "Argentina",
        "ciudad": "Córdoba",
        "descripcion": "Amante del cine clásico"
    }
    response = await async_client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["user"]["nombre_usuario"] == "alice"
    assert data["user"]["pais"] == "Argentina"


@pytest.mark.asyncio
async def test_register_duplicate_username_fails(async_client: AsyncClient):
    """Verifica que no se permita registrar dos veces el mismo nombre de usuario."""
    payload = {"nombre_usuario": "bob", "password": "password123"}
    resp1 = await async_client.post("/api/v1/auth/register", json=payload)
    assert resp1.status_code == 201

    resp2 = await async_client.post("/api/v1/auth/register", json=payload)
    assert resp2.status_code == 400
    assert "ya se encuentra registrado" in resp2.json()["detail"]


@pytest.mark.asyncio
async def test_login_success_and_invalid_credentials(async_client: AsyncClient):
    """Verifica login con credenciales válidas e inválidas."""
    # Registrar usuario
    await async_client.post("/api/v1/auth/register", json={
        "nombre_usuario": "charlie",
        "password": "correctpassword"
    })

    # Login exitoso
    resp_ok = await async_client.post("/api/v1/auth/login", json={
        "nombre_usuario": "charlie",
        "password": "correctpassword"
    })
    assert resp_ok.status_code == 200
    data = resp_ok.json()
    assert "access_token" in data
    assert data["user"]["nombre_usuario"] == "charlie"

    # Password incorrecto
    resp_wrong = await async_client.post("/api/v1/auth/login", json={
        "nombre_usuario": "charlie",
        "password": "wrongpassword"
    })
    assert resp_wrong.status_code == 401
    assert "Credenciales inválidas" in resp_wrong.json()["detail"]

    # Usuario inexistente
    resp_nonexistent = await async_client.post("/api/v1/auth/login", json={
        "nombre_usuario": "nonexistent",
        "password": "anypassword"
    })
    assert resp_nonexistent.status_code == 401


@pytest.mark.asyncio
async def test_get_me_endpoint(async_client: AsyncClient):
    """Verifica acceso a /api/v1/auth/me con token válido e inválido."""
    # Sin autenticación -> 401
    resp_unauth = await async_client.get("/api/v1/auth/me")
    assert resp_unauth.status_code == 401

    # Con token inválido -> 401
    resp_bad = await async_client.get(
        "/api/v1/auth/me",
        headers={"Authorization": "Bearer token_invalido_123"}
    )
    assert resp_bad.status_code == 401

    # Registrar e iniciar sesión
    reg_resp = await async_client.post("/api/v1/auth/register", json={
        "nombre_usuario": "diana",
        "password": "secretpassword"
    })
    token = reg_resp.json()["access_token"]

    # Con token válido -> 200
    resp_me = await async_client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert resp_me.status_code == 200
    user_data = resp_me.json()
    assert user_data["nombre_usuario"] == "diana"
