import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import create_access_token
from app.models.usuario import Usuario


@pytest.mark.asyncio
async def test_admin_sync_unauthorized(async_client: AsyncClient):
    """Petición a endpoint administrativo sin credenciales debe retornar 401."""
    response = await async_client.post("/api/v1/admin/sync/genres")
    assert response.status_code == 401
    assert "Credenciales administrativas requeridas" in response.json()["detail"]


@pytest.mark.asyncio
async def test_admin_sync_forbidden_for_regular_user(async_client: AsyncClient, db_session: AsyncSession):
    """Petición con usuario estándar (no admin) debe retornar 403."""
    user = Usuario(
        nombre_usuario="regular_user",
        password_hash="hash",
        es_admin=False
    )
    db_session.add(user)
    await db_session.commit()

    token = create_access_token(subject=user.id)
    headers = {"Authorization": f"Bearer {token}"}

    response = await async_client.post("/api/v1/admin/sync/genres", headers=headers)
    assert response.status_code == 403
    assert "se requieren privilegios de administrador" in response.json()["detail"]


@pytest.mark.asyncio
async def test_admin_sync_allowed_with_admin_user_token(async_client: AsyncClient, db_session: AsyncSession):
    """Petición con usuario administrador (es_admin=True) debe retornar 202 Accepted."""
    admin_user = Usuario(
        nombre_usuario="admin_master",
        password_hash="hash",
        es_admin=True
    )
    db_session.add(admin_user)
    await db_session.commit()

    token = create_access_token(subject=admin_user.id)
    headers = {"Authorization": f"Bearer {token}"}

    response = await async_client.post("/api/v1/admin/sync/genres", headers=headers)
    assert response.status_code == 202
    data = response.json()
    assert data["status"] == "accepted"
    assert data["job"] == "sync_genres"


@pytest.mark.asyncio
async def test_admin_sync_allowed_with_admin_api_key_header(async_client: AsyncClient):
    """Petición con header X-Admin-Key válido debe retornar 202 Accepted sin necesidad de usuario."""
    headers = {"X-Admin-Key": settings.ADMIN_API_KEY}
    response = await async_client.post("/api/v1/admin/sync/genres", headers=headers)
    assert response.status_code == 202
    assert response.json()["job"] == "sync_genres"


@pytest.mark.asyncio
async def test_admin_sync_jobs_with_parameters(async_client: AsyncClient):
    """Verifica que todos los endpoints administrativos acepten sus parámetros de entrada."""
    headers = {"X-Admin-Key": settings.ADMIN_API_KEY}

    # Initial ingest con parámetros
    initial_payload = {
        "priority": "toprated_first",
        "movies_target": 100,
        "series_target": 50
    }
    resp_init = await async_client.post("/api/v1/admin/sync/initial", json=initial_payload, headers=headers)
    assert resp_init.status_code == 202
    assert resp_init.json()["job"] == "initial_ingest"

    # Daily sync con ventana personalizada de horas
    daily_payload = {"hours_window": 72}
    resp_daily = await async_client.post("/api/v1/admin/sync/daily", json=daily_payload, headers=headers)
    assert resp_daily.status_code == 202
    assert resp_daily.json()["job"] == "daily_sync"

    # Percentiles y ratings
    resp_pct = await async_client.post("/api/v1/admin/sync/percentiles", headers=headers)
    assert resp_pct.status_code == 202
    assert resp_pct.json()["job"] == "recalculate_metrics"

    # Reviews con límite por título
    reviews_payload = {"limit_per_title": 10}
    resp_rev = await async_client.post("/api/v1/admin/sync/reviews", json=reviews_payload, headers=headers)
    assert resp_rev.status_code == 202
    assert resp_rev.json()["job"] == "sync_reviews"

    # Import TMDB ID
    import_payload = {"tmdb_id": 550, "type": "movie"}
    resp_tmdb = await async_client.post("/api/v1/admin/sync/import-tmdb", json=import_payload, headers=headers)
    assert resp_tmdb.status_code == 202
    assert resp_tmdb.json()["job"] == "import_tmdb"

    # Import JSON vacío -> 400 Bad Request
    resp_empty_json = await async_client.post("/api/v1/admin/sync/import-json", json=[], headers=headers)
    assert resp_empty_json.status_code == 400

    # Import JSON con items -> 202 Accepted
    resp_json = await async_client.post(
        "/api/v1/admin/sync/import-json",
        json=[{"tipo": "pelicula", "titulo": "Matrix"}],
        headers=headers
    )
    assert resp_json.status_code == 202
    assert resp_json.json()["job"] == "import_json"


@pytest.mark.asyncio
async def test_admin_background_workers_execution(monkeypatch):
    """Verifica que todas las funciones wrapper de BackgroundTasks se ejecuten sin errores de firma o invocación."""
    from unittest.mock import AsyncMock
    from app.api.v1 import admin

    mock_client = AsyncMock()
    mock_client.close = AsyncMock()
    monkeypatch.setattr("app.api.v1.admin.TMDBClient", lambda: mock_client)

    # Mock de TMDBSyncService para verificar que todas las llamadas de los wrappers correspondan exactamente a los métodos del servicio
    mock_service = AsyncMock()
    monkeypatch.setattr("app.api.v1.admin.TMDBSyncService", lambda db, client: mock_service)

    await admin._run_job_genres()
    assert mock_service.sync_genres.called

    await admin._run_job_initial(priority="popular_first", movies_target=10, series_target=10)
    assert mock_service.run_initial_ingest.called

    await admin._run_job_daily(hours_window=48)
    assert mock_service.run_daily_sync.called

    await admin._run_job_percentiles()
    assert mock_service.recalculate_percentiles.called
    assert mock_service.recalculate_unified_ratings.called

    # Aquí se verifica especialmente _run_job_reviews(limit_per_title)
    await admin._run_job_reviews(limit_per_title=15)
    assert mock_service.sync_all_missing_reviews.called

    await admin._run_job_import_tmdb(tmdb_id=123, media_type="movie")
    assert mock_service.upsert_movie.called

    await admin._run_job_import_tmdb(tmdb_id=456, media_type="tv")
    assert mock_service.upsert_series.called

    await admin._run_job_import_json(items=[{"tipo": "pelicula", "titulo": "Avatar"}])
    assert mock_service.import_from_json_data.called
