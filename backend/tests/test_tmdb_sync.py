import pytest
from datetime import date
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
    client.get_details.side_effect = lambda m, id_, *args, **kwargs: MOCK_MOVIE_DETAILS if m == "movie" else MOCK_SERIES_DETAILS
    client.get_season_details.return_value = MOCK_SEASON_1_DETAILS
    client.get_reviews.return_value = MOCK_REVIEWS_DATA
    client.get_changes.return_value = {"results": []}
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

    # Elenco limitado a 15 actores con personaje y orden
    res_cast = await db_session.execute(
        select(titulos_elenco).where(titulos_elenco.c.titulo_id == movie.id).order_by(titulos_elenco.c.orden.asc())
    )
    cast_rows = res_cast.all()
    assert len(cast_rows) == 15
    assert cast_rows[0].personaje == "Personaje 0"
    assert cast_rows[0].orden == 0
    assert movie.rating_unificado == 8.4


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
async def test_daily_sync_updates_changed_series(db_session, mock_tmdb_client):
    service = TMDBSyncService(db_session, mock_tmdb_client)
    await service.sync_genres()

    # Crear serie local en catálogo
    series = Titulo(tmdb_id=1396, tipo="tv", nombre="Breaking Bad", popularidad=50.0)
    db_session.add(series)
    await db_session.commit()

    # Configurar mock de get_changes reportando la serie 1396 y discover vacío
    mock_tmdb_client.get_changes.return_value = {"results": [{"id": 1396}]}
    mock_tmdb_client.discover.return_value = {"results": []}

    res_sync = await service.run_daily_sync(changes_hours_window=120, releases_days_window=15)
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


@pytest.mark.asyncio
async def test_daily_sync_updates_untracked_titles_from_changes(db_session, mock_tmdb_client):
    service = TMDBSyncService(db_session, mock_tmdb_client)
    await service.sync_genres()

    # 1. Crear una serie en la BD que NADIE sigue
    series = Titulo(tmdb_id=1396, tipo="tv", nombre="Breaking Bad Viejo", popularidad=50.0)
    # 2. Crear una película en la BD
    movie = Titulo(tmdb_id=157336, tipo="movie", nombre="Interstellar Viejo", popularidad=80.0)
    db_session.add_all([series, movie])
    await db_session.commit()

    # Simular que TMDB reporta que cambiaron la serie 1396 y la película 157336 en /changes
    def mock_changes(media_type, start_date=None, end_date=None, page=1):
        if media_type == "tv":
            return {"results": [{"id": 1396}]}
        elif media_type == "movie":
            return {"results": [{"id": 157336}]}
        return {"results": []}

    mock_tmdb_client.get_changes.side_effect = mock_changes
    mock_tmdb_client.discover.return_value = {"results": []}

    res_sync = await service.run_daily_sync()

    # La serie se actualizó porque estaba en /tv/changes aunque nadie la siguiera
    assert res_sync["updated_series"] == 1

    # Verificar que el nombre de la película se refrescó con MOCK_MOVIE_DETAILS
    refreshed_movie = await db_session.execute(select(Titulo).where(Titulo.tmdb_id == 157336))
    assert refreshed_movie.scalar_one().nombre == "Interstellar"


@pytest.mark.asyncio
async def test_recalculate_unified_ratings_formula(db_session, mock_tmdb_client):
    """Verifica que el cálculo del rating unificado pondere correctamente TMDB + reseñas locales."""
    service = TMDBSyncService(db_session, mock_tmdb_client)

    # Crear usuario y título
    user1 = Usuario(nombre_usuario="user1", password_hash="hash")
    user2 = Usuario(nombre_usuario="user2", password_hash="hash")
    # Título con 10 votos y promedio 8.0 de TMDB
    titulo = Titulo(
        tmdb_id=999,
        tipo="movie",
        nombre="Test Film",
        vote_average_tmdb=8.0,
        vote_count_tmdb=10,
        rating_unificado=8.0
    )
    db_session.add_all([user1, user2, titulo])
    await db_session.commit()

    # Agregar dos reseñas de usuarios locales: 10.0 y 6.0 (Suma = 16.0, N = 2)
    # Fórmula esperada: [(8.0 * 10) + 16.0] / [10 + 2] = 96.0 / 12 = 8.0
    res1 = Resena(titulo=titulo, usuario=user1, puntaje=10.0, texto="Excelente")
    res2 = Resena(titulo=titulo, usuario=user2, puntaje=6.0, texto="Regular")
    db_session.add_all([res1, res2])
    await db_session.commit()

    await service.recalculate_unified_ratings(titulo.id)
    await db_session.refresh(titulo)
    assert titulo.rating_unificado == 8.0

    # Agregar una tercera reseña con 10.0: [(80) + 26.0] / 13 = 106.0 / 13 = 8.15
    user3 = Usuario(nombre_usuario="user3", password_hash="hash")
    db_session.add(user3)
    await db_session.commit()

    res3 = Resena(titulo=titulo, usuario=user3, puntaje=10.0, texto="Muy buena")
    db_session.add(res3)
    await db_session.commit()

    await service.recalculate_unified_ratings(titulo.id)
    await db_session.refresh(titulo)
    assert titulo.rating_unificado == 8.15


@pytest.mark.asyncio
async def test_daily_sync_with_custom_hours_window(db_session, mock_tmdb_client):
    """Verifica que run_daily_sync acepte una ventana personalizada en horas sin errores."""
    service = TMDBSyncService(db_session, mock_tmdb_client)
    mock_tmdb_client.get_changes.return_value = {"results": []}
    mock_tmdb_client.discover.return_value = {"results": []}

    res = await service.run_daily_sync(hours_window=72)
    assert "updated_series" in res
    assert "new_movies" in res
    assert "new_series" in res


@pytest.mark.asyncio
async def test_upsert_movie_unreleased_behavior(db_session, mock_tmdb_client):
    """Verifica que películas no estrenadas se omitan por defecto y se permitan con allow_unreleased=True."""
    service = TMDBSyncService(db_session, mock_tmdb_client)
    future_movie_details = dict(MOCK_MOVIE_DETAILS)
    future_movie_details["release_date"] = "2099-01-01"
    future_movie_details["id"] = 999901

    # Con allow_unreleased=False (o default), retorna None y no se guarda
    res_skipped = await service.upsert_movie(999901, details=future_movie_details, allow_unreleased=False)
    assert res_skipped is None

    # Con allow_unreleased=True, sí se guarda
    res_allowed = await service.upsert_movie(999901, details=future_movie_details, allow_unreleased=True)
    assert res_allowed is not None
    assert res_allowed.tmdb_id == 999901


@pytest.mark.asyncio
async def test_upsert_series_unreleased_behavior(db_session, mock_tmdb_client):
    """Verifica que series sin temporadas emitidas se omitan por defecto y se permitan con allow_unreleased=True."""
    service = TMDBSyncService(db_session, mock_tmdb_client)
    future_series_details = dict(MOCK_SERIES_DETAILS)
    future_series_details["first_air_date"] = "2099-01-01"
    future_series_details["id"] = 999902
    future_series_details["seasons"] = [
        {"season_number": 1, "air_date": "2099-01-01", "name": "Temporada 1"}
    ]

    # Con allow_unreleased=False, se omite
    res_skipped = await service.upsert_series(999902, details=future_series_details, allow_unreleased=False)
    assert res_skipped is None

    # Con allow_unreleased=True, se inserta
    res_allowed = await service.upsert_series(999902, details=future_series_details, allow_unreleased=True)
    assert res_allowed is not None
    assert res_allowed.tmdb_id == 999902


@pytest.mark.asyncio
async def test_cleanup_unreleased_titles(db_session, mock_tmdb_client):
    """Verifica que cleanup_unreleased_titles borre títulos no estrenados y conserve los estrenados."""
    service = TMDBSyncService(db_session, mock_tmdb_client)
    from datetime import date

    # Insertar una película estrenada y una futura
    m_released = Titulo(tmdb_id=88801, tipo="movie", nombre="Estrenada", fecha_estreno=date(2020, 1, 1))
    m_unreleased = Titulo(tmdb_id=88802, tipo="movie", nombre="Futura", fecha_estreno=date(2099, 1, 1))
    m_no_date = Titulo(tmdb_id=88803, tipo="movie", nombre="Sin Fecha", fecha_estreno=None)
    db_session.add_all([m_released, m_unreleased, m_no_date])
    await db_session.commit()

    res = await service.cleanup_unreleased_titles()
    assert res["deleted_movies"] == 2

    # Verificar que solo queda la estrenada
    res_check = await db_session.execute(select(Titulo).where(Titulo.tmdb_id.in_([88801, 88802, 88803])))
    remaining = res_check.scalars().all()
    assert len(remaining) == 1
    assert remaining[0].tmdb_id == 88801


@pytest.mark.asyncio
async def test_expand_catalog_by_genres_single_genre(db_session, mock_tmdb_client):
    """Verifica la expansión de catálogo para un género específico pasando los filtros adecuados a discover."""
    service = TMDBSyncService(db_session, mock_tmdb_client)
    await service.sync_genres()

    # Configurar mock de discover para retornar una película y luego terminar
    mock_tmdb_client.discover.return_value = {
        "page": 1,
        "total_pages": 1,
        "results": [{"id": 157336, "title": "Interstellar"}]
    }

    res = await service.expand_catalog_by_genres(
        genre="Ciencia ficción",
        media_type="movie",
        target_per_genre=5,
        min_vote_count=250,
        min_vote_average=7.2,
    )

    assert res["genres_processed"] == 1
    assert res["movies_added"] == 1
    assert res["series_added"] == 0

    # Comprobar llamada a discover con with_genres, vote_count.gte y vote_average.gte
    mock_tmdb_client.discover.assert_called_with(
        media_type="movie",
        sort_by="popularity.desc",
        page=1,
        vote_count_gte=250,
        vote_average_gte=7.2,
        with_genres="878",  # ID de Ciencia ficción en fixtures
        release_date_lte=pytest.approx(date.today().strftime("%Y-%m-%d")),
    )


@pytest.mark.asyncio
async def test_expand_catalog_all_genres(db_session, mock_tmdb_client):
    """Verifica que si no se pasa género, itera sobre todos los géneros registrados."""
    service = TMDBSyncService(db_session, mock_tmdb_client)
    await service.sync_genres()

    # Discover sin resultados nuevos
    mock_tmdb_client.discover.return_value = {
        "page": 1,
        "total_pages": 1,
        "results": []
    }

    res = await service.expand_catalog_by_genres(
        genre=None,
        media_type="both",
        target_per_genre=2,
    )

    # 6 géneros únicos en fixtures
    assert res["genres_processed"] == 6
    assert res["total_added"] == 0


@pytest.mark.asyncio
async def test_expand_catalog_invalid_genre_raises_error(db_session, mock_tmdb_client):
    """Verifica que si se ingresa un género inexistente, lanza ValueError."""
    service = TMDBSyncService(db_session, mock_tmdb_client)
    await service.sync_genres()

    with pytest.raises(ValueError, match="No se encontró ningún género"):
        await service.expand_catalog_by_genres(genre="GeneroInexistenteTotal")


@pytest.mark.asyncio
async def test_refresh_catalog_metrics(db_session, mock_tmdb_client):
    """Verifica que refresh_catalog_metrics actualice popularidad y votos de todos los títulos."""
    service = TMDBSyncService(db_session, mock_tmdb_client)

    # Crear título de prueba con métricas viejas
    t = Titulo(
        tmdb_id=12345,
        tipo="movie",
        nombre="Test Metrics Movie",
        popularidad=1.0,
        vote_average_tmdb=5.0,
        vote_count_tmdb=10,
        rating_unificado=5.0,
    )
    db_session.add(t)
    await db_session.commit()

    # Mock de get_details ligero
    mock_tmdb_client.get_details.side_effect = None
    mock_tmdb_client.get_details.return_value = {
        "popularity": 88.5,
        "vote_average": 8.4,
        "vote_count": 1500,
    }

    res = await service.refresh_catalog_metrics(batch_size=10)
    assert res["total_titles"] >= 1
    assert res["updated"] >= 1

    await db_session.refresh(t)
    assert t.popularidad == pytest.approx(88.5)
    assert t.vote_average_tmdb == pytest.approx(8.4)
    assert t.vote_count_tmdb == 1500
    assert t.rating_unificado == pytest.approx(8.4)
    assert t.popularidad_percentil is not None


@pytest.mark.asyncio
async def test_daily_sync_exhaustive_pagination_and_active_series(db_session, mock_tmdb_client):
    """Verifica que run_daily_sync pagine changes exhaustivamente y consulte series activas."""
    service = TMDBSyncService(db_session, mock_tmdb_client)

    # Crear una serie activa en BD
    s = Titulo(
        tmdb_id=9999,
        tipo="tv",
        nombre="Active Series",
        status_tmdb="Returning Series",
        popularidad=15.0,
    )
    db_session.add(s)
    await db_session.commit()

    # Mock paginación en get_changes (página 1 devuelve total_pages=2, página 2 termina)
    def mock_get_changes(media_type, start_date=None, end_date=None, page=1):
        if page == 1:
            return {"page": 1, "total_pages": 2, "results": [{"id": 1111}]}
        return {"page": 2, "total_pages": 2, "results": [{"id": 2222}]}

    mock_tmdb_client.get_changes.side_effect = mock_get_changes
    mock_tmdb_client.discover.return_value = {"page": 1, "total_pages": 1, "results": []}

    res = await service.run_daily_sync(changes_hours_window=24)
    # Debe haber llamado a upsert de la serie activa (9999) y refrescado métricas
    assert "updated_series" in res
    assert res["updated_series"] >= 1


@pytest.mark.asyncio
async def test_upsert_series_skips_already_completed_seasons(db_session, mock_tmdb_client):
    """Verifica que temporadas ya completadas y finalizadas no vuelvan a consultar get_season_details."""
    service = TMDBSyncService(db_session, mock_tmdb_client)
    await service.sync_genres()

    # Primera ingesta: debe consultar get_season_details
    mock_tmdb_client.get_season_details.reset_mock()
    series = await service.upsert_series(1396, MOCK_SERIES_DETAILS, fetch_episodes=True)
    await db_session.commit()
    assert mock_tmdb_client.get_season_details.call_count == 1

    # Segunda sincronización de la misma serie:
    # Como la serie es 'Ended' y la temporada 1 ya tiene sus 2 episodios completos en BD,
    # debe omitir la llamada a get_season_details.
    mock_tmdb_client.get_season_details.reset_mock()
    series_updated = await service.upsert_series(1396, MOCK_SERIES_DETAILS, fetch_episodes=True)
    await db_session.commit()
    mock_tmdb_client.get_season_details.assert_not_called()


@pytest.mark.asyncio
async def test_upsert_movie_rejects_non_latin_and_incomplete(db_session, mock_tmdb_client):
    """Verifica que upsert_movie descarte obras con caracteres no latinos o metadatos faltantes."""
    service = TMDBSyncService(db_session, mock_tmdb_client)

    # 1. Película no latina
    bad_latin = {
        "title": "丫丫",
        "release_date": "2024-01-01",
        "status": "Released",
        "original_language": "zh",
        "origin_country": ["CN"],
    }
    m1 = await service.upsert_movie(99901, bad_latin)
    assert m1 is None

    # 2. Película sin país
    no_country = {
        "title": "Mystery Film",
        "release_date": "2024-01-01",
        "status": "Released",
        "original_language": "en",
        "origin_country": [],
        "production_countries": [],
    }
    m2 = await service.upsert_movie(99902, no_country)
    assert m2 is None


@pytest.mark.asyncio
async def test_upsert_movie_multi_country_and_fallback(db_session, mock_tmdb_client):
    """Verifica que upsert_movie consolide múltiples países y use el fallback de producción."""
    service = TMDBSyncService(db_session, mock_tmdb_client)

    # Coproducción con origin_country múltiple
    doc_details = {
        "title": "Doc Martin The Movie",
        "release_date": "2020-01-01",
        "status": "Released",
        "original_language": "en",
        "origin_country": ["FR", "GB"],
    }
    m = await service.upsert_movie(88801, doc_details)
    assert m is not None
    assert m.pais == "FR, GB"

    # Fallback a production_countries
    barbie_details = {
        "title": "Barbie Pegasus",
        "release_date": "2005-10-01",
        "status": "Released",
        "original_language": "en",
        "origin_country": [],
        "production_countries": [{"iso_3166_1": "US"}, {"iso_3166_1": "CA"}],
    }
    b = await service.upsert_movie(88802, barbie_details)
    assert b is not None
    assert b.pais == "US, CA"


@pytest.mark.asyncio
async def test_purge_invalid_or_incomplete_titles(db_session, mock_tmdb_client):
    """Verifica que purge_invalid_or_incomplete_titles elimine en cascada solo títulos inválidos."""
    service = TMDBSyncService(db_session, mock_tmdb_client)

    # 1. Título válido
    t_valid = Titulo(
        nombre="Valid Movie",
        tipo="movie",
        tmdb_id=77701,
        fecha_estreno=date(2022, 1, 1),
        idioma_original="en",
        pais="US",
        popularidad=10.0,
    )
    # 2. Título no latino
    t_non_latin = Titulo(
        nombre="名探偵コナン",
        tipo="tv",
        tmdb_id=77702,
        fecha_estreno=date(2022, 1, 1),
        idioma_original="ja",
        pais="JP",
        popularidad=10.0,
    )
    # 3. Título sin fecha
    t_no_date = Titulo(
        nombre="No Date Show",
        tipo="tv",
        tmdb_id=77703,
        fecha_estreno=None,
        idioma_original="en",
        pais="GB",
        popularidad=5.0,
    )
    # 4. Título sin país
    t_no_country = Titulo(
        nombre="No Country Film",
        tipo="movie",
        tmdb_id=77704,
        fecha_estreno=date(2021, 5, 1),
        idioma_original="tr",
        pais=None,
        popularidad=5.0,
    )

    db_session.add_all([t_valid, t_non_latin, t_no_date, t_no_country])
    await db_session.commit()

    res = await service.purge_invalid_or_incomplete_titles()
    assert res["purged_count"] == 3

    # Verificar que el válido sigue existiendo y los inválidos fueron eliminados
    res_check = await db_session.execute(select(Titulo.nombre))
    remaining = res_check.scalars().all()
    assert "Valid Movie" in remaining
    assert "名探偵コナン" not in remaining
    assert "No Date Show" not in remaining
    assert "No Country Film" not in remaining





