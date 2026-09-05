import pytest
from unittest.mock import AsyncMock, patch
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.models import (
    Actor,
    Episodio,
    Genero,
    Resena,
    Temporada,
    Titulo,
    titulos_elenco,
    EstadoUsuarioTitulo,
    Usuario,
)
from app.services.tmdb_client import TMDBClient
from app.services.tmdb_sync_service import TMDBSyncService
from tests.mocks.tmdb_fixtures import (
    MOCK_MOVIE_GENRES,
    MOCK_TV_GENRES,
    MOCK_MOVIE_DETAILS,
    MOCK_SERIES_DETAILS,
    MOCK_SEASON_1_DETAILS,
    MOCK_REVIEWS_DATA,
)


@pytest.fixture
def mock_tmdb_client():
    client = AsyncMock(spec=TMDBClient)
    client.get_genres.side_effect = lambda m: MOCK_MOVIE_GENRES if m == "movie" else MOCK_TV_GENRES
    client.get_details.side_effect = lambda m, id_: MOCK_MOVIE_DETAILS if m == "movie" else MOCK_SERIES_DETAILS
    client.get_season_details.return_value = MOCK_SEASON_1_DETAILS
    client.get_reviews.return_value = MOCK_REVIEWS_DATA
    client.search.return_value = {"results": [{"id": 157336, "title": "Interstellar"}]}
    return client


@pytest.mark.asyncio
async def test_sync_genres(db_session, mock_tmdb_client):
    service = TMDBSyncService(db_session, mock_tmdb_client)
    count = await service.sync_genres()

    # En fixtures tenemos 4 de movie y 3 de tv (Drama repetido -> 6 únicos)
    assert count == 6

    # Idempotencia: si sincronizamos de nuevo, no agrega repetidos
    count_second = await service.sync_genres()
    assert count_second == 0

    res = await db_session.execute(select(Genero))
    all_genres = res.scalars().all()
    assert len(all_genres) == 6


@pytest.mark.asyncio
async def test_upsert_movie_enriches_credits_and_cast_limit(db_session, mock_tmdb_client):
    service = TMDBSyncService(db_session, mock_tmdb_client)
    await service.sync_genres()

    movie = await service.upsert_movie(157336, MOCK_MOVIE_DETAILS)
    await db_session.commit()

    assert movie.tmdb_id == 157336
    assert movie.nombre == "Interstellar"
    assert movie.director == "Christopher Nolan"
    # Máximo 3 guionistas concatenados
    guionistas = [g.strip() for g in movie.guionista.split(",")]
    assert len(guionistas) <= 3
    assert "Jonathan Nolan" in guionistas
    assert "Christopher Nolan" in guionistas

    # Elenco limitado a 15 actores
    res_cast = await db_session.execute(
        select(titulos_elenco).where(titulos_elenco.c.titulo_id == movie.id)
    )
    cast_rows = res_cast.all()
    assert len(cast_rows) == 15


@pytest.mark.asyncio
async def test_upsert_series_creates_seasons_and_episodes(db_session, mock_tmdb_client):
    service = TMDBSyncService(db_session, mock_tmdb_client)
    await service.sync_genres()

    series = await service.upsert_series(1396, MOCK_SERIES_DETAILS, fetch_episodes=True)
    await db_session.commit()

    assert series.tmdb_id == 1396
    assert series.nombre == "Breaking Bad"
    assert series.tipo == "tv"
    assert series.status_tmdb == "Ended"

    # Temporadas creadas (ignora temp 0)
    res_temp = await db_session.execute(
        select(Temporada).where(Temporada.titulo_id == series.id)
    )
    temporadas = res_temp.scalars().all()
    assert len(temporadas) == 1
    assert temporadas[0].numero == 1

    # Episodios creados
    res_ep = await db_session.execute(
        select(Episodio).where(Episodio.temporada_id == temporadas[0].id)
    )
    episodios = res_ep.scalars().all()
    assert len(episodios) == 2
    assert episodios[0].numero == 1
    assert episodios[0].nombre == "Pilot"


@pytest.mark.asyncio
async def test_recalculate_percentiles(db_session):
    service = TMDBSyncService(db_session)

    # Insertar títulos con popularidades conocidas
    t1 = Titulo(nombre="T1", tipo="movie", tmdb_id=1, popularidad=10.0)
    t2 = Titulo(nombre="T2", tipo="movie", tmdb_id=2, popularidad=50.0)
    t3 = Titulo(nombre="T3", tipo="movie", tmdb_id=3, popularidad=100.0)
    db_session.add_all([t1, t2, t3])
    await db_session.commit()

    await service.recalculate_percentiles()

    await db_session.refresh(t1)
    await db_session.refresh(t2)
    await db_session.refresh(t3)

    # Con 3 títulos: percentiles son 0.0, 0.5, 1.0
    assert pytest.approx(t1.popularidad_percentil, 0.01) == 0.0
    assert pytest.approx(t2.popularidad_percentil, 0.01) == 0.5
    assert pytest.approx(t3.popularidad_percentil, 0.01) == 1.0


@pytest.mark.asyncio
async def test_import_manual_from_json_without_id_uses_search(db_session, mock_tmdb_client):
    service = TMDBSyncService(db_session, mock_tmdb_client)
    await service.sync_genres()

    # JSON sin id_tmdb
    json_data = [
        {
            "titulo": "Interstellar",
            "tipo": "movie",
            "fecha_estreno": "2014-11-05",
        }
    ]

    res = await service.import_from_json_data(json_data)
    assert res["imported"] == 1
    assert len(res["errors"]) == 0

    # Verificamos que llamó a search y luego guardó con el ID resuelto
    mock_tmdb_client.search.assert_called_once()
    saved = await db_session.execute(select(Titulo).where(Titulo.tmdb_id == 157336))
    assert saved.scalar_one_or_none() is not None


@pytest.mark.asyncio
async def test_import_manual_without_tmdb_match_fails_with_error(db_session, mock_tmdb_client):
    mock_tmdb_client.search.return_value = {"results": []}
    service = TMDBSyncService(db_session, mock_tmdb_client)

    json_data = [
        {
            "titulo": "Titulo Inexistente En TMDB",
            "tipo": "movie",
            "fecha_estreno": "2023-01-01",
        }
    ]

    res = await service.import_from_json_data(json_data)
    assert res["imported"] == 0
    assert len(res["errors"]) == 1
    assert "No se encontró coincidencia en TMDB" in res["errors"][0]

    # Verificar que NO se insertó en la base de datos
    saved = await db_session.execute(select(Titulo).where(Titulo.nombre == "Titulo Inexistente En TMDB"))
    assert saved.scalar_one_or_none() is None


@pytest.mark.asyncio
async def test_daily_sync_updates_tracked_series(db_session, mock_tmdb_client):
    service = TMDBSyncService(db_session, mock_tmdb_client)
    await service.sync_genres()

    # Crear usuario y serie seguida
    user = Usuario(nombre_usuario="syncuser", password_hash="hashed_secret")
    db_session.add(user)
    await db_session.flush()

    series = Titulo(tmdb_id=1396, tipo="tv", nombre="Breaking Bad", popularidad=50.0)
    db_session.add(series)
    await db_session.flush()

    estado = EstadoUsuarioTitulo(usuario_id=user.id, titulo_id=series.id, estado="siguiendo")
    db_session.add(estado)
    await db_session.commit()

    # Configurar mock de discover para estrenos (vacío)
    mock_tmdb_client.discover.return_value = {"results": []}

    res_sync = await service.run_daily_sync()
    assert res_sync["updated_series"] == 1


@pytest.mark.asyncio
async def test_sync_reviews_caps_at_limit(db_session, mock_tmdb_client):
    service = TMDBSyncService(db_session, mock_tmdb_client)
    await service.sync_genres()

    # MOCK_REVIEWS_DATA tiene 25 reseñas, debe recortar al límite configurado (20)
    movie = await service.upsert_movie(157336, MOCK_MOVIE_DETAILS)
    await db_session.commit()

    res = await db_session.execute(
        select(Resena).where(Resena.titulo_id == movie.id)
    )
    reviews = res.scalars().all()
    assert len(reviews) == 20
    assert all(r.usuario_id is None for r in reviews)
    assert all(r.autor_tmdb is not None for r in reviews)
    assert all(r.tmdb_review_id is not None for r in reviews)

    # Si volvemos a correr la sincronización de reseñas, no agrega ninguna porque ya llegó a 20
    added_second = await service.sync_reviews_for_title(movie)
    assert added_second == 0

