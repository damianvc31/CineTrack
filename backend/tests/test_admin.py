import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import create_access_token
from app.models.usuario import Usuario
from fastapi import BackgroundTasks


@pytest.fixture(autouse=True)
def prevent_real_background_tasks(monkeypatch):
    """Evita que los endpoints administrativos ejecuten jobs reales de TMDB contra internet durante los tests."""
    monkeypatch.setattr(BackgroundTasks, "add_task", lambda self, *args, **kwargs: None)



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

    # Expand catalog
    expand_payload = {
        "genre": "Crime",
        "media_type": "movie",
        "min_vote_count": 300,
        "min_vote_average": 7.0,
        "target_per_genre": 15,
        "allow_unreleased": False
    }
    resp_expand = await async_client.post("/api/v1/admin/sync/expand", json=expand_payload, headers=headers)
    assert resp_expand.status_code == 202
    assert resp_expand.json()["job"] == "expand_catalog"

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

    # Actor photos sync
    resp_photos = await async_client.post(
        "/api/v1/admin/sync/actor-photos",
        json={"limit": 100},
        headers=headers
    )
    assert resp_photos.status_code == 202
    assert resp_photos.json()["job"] == "sync_actor_photos"


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

    await admin._run_job_expand(
        genre="Crime",
        media_type="movie",
        target_per_genre=10,
        min_vote_count=200,
        min_vote_average=7.0,
        allow_unreleased=False
    )
    assert mock_service.expand_catalog_by_genres.called


@pytest.mark.asyncio
async def test_admin_clear_catalog_requires_confirmation(async_client: AsyncClient):
    """Petición para vaciar catálogo sin confirm=true debe retornar 400."""
    headers = {"X-Admin-Key": settings.ADMIN_API_KEY}
    res = await async_client.delete("/api/v1/admin/catalog", headers=headers)
    assert res.status_code == 400
    assert "confirm=true" in res.json()["detail"]


@pytest.mark.asyncio
async def test_admin_clear_catalog_execution(async_client: AsyncClient, db_session: AsyncSession):
    """Vaciado de catálogo con confirm=true elimina títulos y relaciones pero preserva géneros y usuarios."""
    from app.models import Genero, Titulo, Usuario

    headers = {"X-Admin-Key": settings.ADMIN_API_KEY}

    # Crear género, usuario y título
    g = Genero(id=99, nombre="Sci-Fi")
    u = Usuario(nombre_usuario="persistent_user", password_hash="hash")
    t = Titulo(id=999, tmdb_id=9999, tipo="movie", nombre="Matrix", rating_unificado=9.0)
    db_session.add_all([g, u, t])
    await db_session.commit()

    # Ejecutar vaciado
    res = await async_client.delete("/api/v1/admin/catalog?confirm=true", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    assert data["deleted"]["titulos"] >= 1

    # Verificar que el usuario y el género siguen existiendo
    from sqlalchemy import select
    user_check = (await db_session.execute(select(Usuario).where(Usuario.nombre_usuario == "persistent_user"))).scalar_one_or_none()
    assert user_check is not None
    genre_check = (await db_session.execute(select(Genero).where(Genero.id == 99))).scalar_one_or_none()
    assert genre_check is not None

    # Verificar que el título ya no existe
    title_check = (await db_session.execute(select(Titulo).where(Titulo.id == 999))).scalar_one_or_none()
    assert title_check is None


@pytest.mark.asyncio
async def test_admin_sync_job_status_endpoints(async_client: AsyncClient):
    """Verifica la consulta de estado de jobs individuales y todos los jobs en /sync/jobs."""
    headers = {"X-Admin-Key": settings.ADMIN_API_KEY}

    # 1. Consultar job individual existente
    res = await async_client.get("/api/v1/admin/sync/jobs/daily_sync/status", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["job"] == "daily_sync"
    assert data["status"] in ("idle", "running", "completed", "failed")

    # 2. Consultar todos los jobs
    res_all = await async_client.get("/api/v1/admin/sync/jobs/status", headers=headers)
    assert res_all.status_code == 200
    all_data = res_all.json()
    assert "daily_sync" in all_data
    assert "actor_photos" in all_data
    assert "sync_reviews" in all_data


