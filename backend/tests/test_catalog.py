from datetime import date, timedelta
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Actor, Episodio, Genero, Resena, Temporada, Titulo, TituloElenco, titulos_generos


async def create_user_and_token(client: AsyncClient, username: str) -> tuple[int, str]:
    res = await client.post(
        "/api/v1/auth/register",
        json={"nombre_usuario": username, "password": "password123"}
    )
    data = res.json()
    return data["user"]["id"], data["access_token"]


@pytest.fixture
async def sample_catalog(db_session: AsyncSession):
    today = date.today()

    # Generos
    g_action = Genero(id=28, nombre="Action")
    g_drama = Genero(id=18, nombre="Drama")
    db_session.add_all([g_action, g_drama])
    await db_session.flush()

    # Actores
    act1 = Actor(id=1, nombre="Tom Cruise")
    act2 = Actor(id=2, nombre="Bryan Cranston")
    db_session.add_all([act1, act2])
    await db_session.flush()

    # Película (estreno reciente dentro de los 60 días para New Releases / Trending)
    m1 = Titulo(
        id=1,
        tmdb_id=101,
        tipo="movie",
        nombre="Top Gun",
        fecha_estreno=today - timedelta(days=10),
        duracion=130,
        popularidad=150.0,
        vote_average_tmdb=8.3,
        vote_count_tmdb=500,
        rating_unificado=8.3
    )
    # Serie
    s1 = Titulo(
        id=2,
        tmdb_id=202,
        tipo="tv",
        nombre="Breaking Bad",
        fecha_estreno=date(2008, 1, 20),
        fecha_fin=date(2013, 9, 29),
        popularidad=250.0,
        vote_average_tmdb=8.9,
        vote_count_tmdb=1200,
        rating_unificado=8.9,
        status_tmdb="Ended"
    )
    db_session.add_all([m1, s1])
    await db_session.flush()

    # Vincular generos
    await db_session.execute(titulos_generos.insert().values(titulo_id=m1.id, genero_id=g_action.id))
    await db_session.execute(titulos_generos.insert().values(titulo_id=s1.id, genero_id=g_drama.id))

    # Vincular elenco
    elenco1 = TituloElenco(titulo_id=m1.id, actor_id=act1.id, personaje="Maverick", orden=0)
    elenco2 = TituloElenco(titulo_id=s1.id, actor_id=act2.id, personaje="Walter White", orden=0)
    db_session.add_all([elenco1, elenco2])

    # Temporada y Episodios para la serie
    temp1 = Temporada(id=1, titulo_id=s1.id, numero=1, sinopsis="Temporada 1")
    db_session.add(temp1)
    await db_session.flush()

    ep1 = Episodio(id=1, temporada_id=temp1.id, numero=1, nombre="Pilot", duracion=58)
    ep2 = Episodio(id=2, temporada_id=temp1.id, numero=2, nombre="Cat's in the Bag", duracion=48)
    db_session.add_all([ep1, ep2])

    # Reseña pública de TMDB
    r1 = Resena(
        id=1,
        titulo_id=m1.id,
        usuario_id=None,
        autor_tmdb="cinematic_fan",
        puntaje=9.0,
        texto="Incredible aviation action!"
    )
    db_session.add(r1)

    await db_session.commit()
    return {"movie": m1, "series": s1, "genre_action": g_action}


@pytest.mark.asyncio
async def test_get_home_sections(async_client: AsyncClient, sample_catalog):
    res = await async_client.get("/api/v1/home")
    assert res.status_code == 200
    data = res.json()
    assert "trending" in data
    assert "new_releases" in data
    assert "classics" in data
    assert "top_rated" in data
    assert "by_genre" in data
    assert "others" in data
    assert len(data["trending"]) >= 1
    assert len(data["new_releases"]) >= 1
    assert len(data["top_rated"]) >= 1



@pytest.mark.asyncio
async def test_list_titles_with_filters_and_search(async_client: AsyncClient, sample_catalog):
    # 1. Filtro por tipo=movie
    res_m = await async_client.get("/api/v1/titles?tipo=movie")
    assert res_m.status_code == 200
    data_m = res_m.json()
    assert data_m["total"] == 1
    assert data_m["items"][0]["nombre"] == "Top Gun"

    # 2. Búsqueda por texto "Breaking"
    res_q = await async_client.get("/api/v1/titles?q=Breaking")
    assert res_q.status_code == 200
    data_q = res_q.json()
    assert data_q["total"] == 1
    assert data_q["items"][0]["nombre"] == "Breaking Bad"
    assert "popularidad_percentil" in data_q["items"][0]

    # 3. Búsqueda por nombre de actor "Cranston"
    res_actor_q = await async_client.get("/api/v1/titles?q=Cranston")
    assert res_actor_q.status_code == 200
    data_actor_q = res_actor_q.json()
    assert data_actor_q["total"] == 1
    assert data_actor_q["items"][0]["nombre"] == "Breaking Bad"

    # 4. Filtro por actor_id=1 (Tom Cruise -> Top Gun)
    res_act_id = await async_client.get("/api/v1/titles?actor_id=1")
    assert res_act_id.status_code == 200
    data_act_id = res_act_id.json()
    assert data_act_id["total"] == 1
    assert data_act_id["items"][0]["nombre"] == "Top Gun"

    # 5. Filtro por nombre de género en string (genero=Action)
    res_gen_str = await async_client.get("/api/v1/titles?genero=Action")
    assert res_gen_str.status_code == 200
    data_gen_str = res_gen_str.json()
    assert data_gen_str["total"] == 1
    assert data_gen_str["items"][0]["nombre"] == "Top Gun"

    # 6. Filtro por nombre de actor en string (actor=Cruise)
    res_act_str = await async_client.get("/api/v1/titles?actor=Cruise")
    assert res_act_str.status_code == 200
    data_act_str = res_act_str.json()
    assert data_act_str["total"] == 1
    assert data_act_str["items"][0]["nombre"] == "Top Gun"

    # 7. Filtro por sección (section=top_rated) y ordenamiento dentro del pool
    res_sec_tr = await async_client.get("/api/v1/titles?section=top_rated")
    assert res_sec_tr.status_code == 200
    data_sec_tr = res_sec_tr.json()
    assert data_sec_tr["total"] >= 2
    # Por defecto, el pool de top_rated se ordena por rating descendente (Breaking Bad 8.9 > Top Gun 8.3)
    assert data_sec_tr["items"][0]["nombre"] == "Breaking Bad"
    assert data_sec_tr["items"][1]["nombre"] == "Top Gun"

    # Ordenamiento por popularidad ascendente dentro del pool de top_rated (Top Gun 150.0 < Breaking Bad 250.0)
    res_sec_tr_pop_asc = await async_client.get("/api/v1/titles?section=top_rated&sort_by=popularity&order=asc")
    assert res_sec_tr_pop_asc.status_code == 200
    data_sec_tr_pop_asc = res_sec_tr_pop_asc.json()
    assert data_sec_tr_pop_asc["items"][0]["nombre"] == "Top Gun"
    assert data_sec_tr_pop_asc["items"][1]["nombre"] == "Breaking Bad"

    # 8. Filtro por sección (section=new_releases) con ordenamiento (sort_by=popularity)
    res_sec_nr = await async_client.get("/api/v1/titles?section=new_releases&sort_by=popularity")
    assert res_sec_nr.status_code == 200
    data_sec_nr = res_sec_nr.json()
    assert data_sec_nr["total"] >= 1

    # 9. Ordenamiento por fecha ascendente (order=asc)
    res_ord_asc = await async_client.get("/api/v1/titles?sort_by=release_date&order=asc")
    assert res_ord_asc.status_code == 200
    data_ord_asc = res_ord_asc.json()
    assert data_ord_asc["total"] >= 2
    # El más antiguo (Breaking Bad, 2008) debe venir antes que Top Gun (2026)
    assert data_ord_asc["items"][0]["nombre"] == "Breaking Bad"

    # 10. Listar géneros
    res_g = await async_client.get("/api/v1/genres")
    assert res_g.status_code == 200
    assert len(res_g.json()) >= 2

    # 11. Filtro por sección (section=others) con All types (tipo=None) y tipo=tv
    res_sec_oth = await async_client.get("/api/v1/titles?section=others")
    assert res_sec_oth.status_code == 200
    assert res_sec_oth.json()["total"] >= 1

    res_sec_oth_tv = await async_client.get("/api/v1/titles?section=others&tipo=tv")
    assert res_sec_oth_tv.status_code == 200
    assert res_sec_oth_tv.json()["total"] >= 1


@pytest.mark.asyncio
async def test_get_title_detail(async_client: AsyncClient, sample_catalog):
    # Detalle de Serie
    res = await async_client.get("/api/v1/titles/2")
    assert res.status_code == 200
    data = res.json()
    assert data["nombre"] == "Breaking Bad"
    assert data["tipo"] == "tv"
    assert len(data["elenco"]) == 1
    assert data["elenco"][0]["nombre"] == "Bryan Cranston"
    assert data["elenco"][0]["personaje"] == "Walter White"
    assert len(data["temporadas"]) == 1
    assert len(data["temporadas"][0]["episodios"]) == 2

    # 404 para título inexistente
    res_404 = await async_client.get("/api/v1/titles/999")
    assert res_404.status_code == 404


@pytest.mark.asyncio
async def test_reviews_listing_and_creation(async_client: AsyncClient, sample_catalog):
    # Listar reseñas de Top Gun (debe tener la de TMDB)
    res = await async_client.get("/api/v1/titles/1/reviews")
    assert res.status_code == 200
    reviews = res.json()
    assert len(reviews) == 1
    assert reviews[0]["autor_tmdb"] == "cinematic_fan"

    # Crear reseña con usuario autenticado
    _, token = await create_user_and_token(async_client, "reviewer_1")
    headers = {"Authorization": f"Bearer {token}"}

    post_res = await async_client.post(
        "/api/v1/titles/1/reviews",
        json={"puntaje": 10.0, "texto": "Masterpiece in modern cinema!"},
        headers=headers
    )
    assert post_res.status_code == 201
    new_rev = post_res.json()
    assert new_rev["nombre_usuario"] == "reviewer_1"
    assert new_rev["puntaje"] == 10.0


@pytest.mark.asyncio
async def test_user_library_and_stats(async_client: AsyncClient, sample_catalog):
    uid, token = await create_user_and_token(async_client, "stats_user")
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Marcar película Top Gun como favorita y vista
    await async_client.post("/api/v1/titles/1/favorite", headers=headers)
    await async_client.post("/api/v1/titles/1/watched", headers=headers)

    # 2. Marcar episodios 1 y 2 de Breaking Bad como vistos -> pone serie en 'siguiendo'
    await async_client.post("/api/v1/titles/2/seasons/1/episodes/1/watch", headers=headers)
    await async_client.post("/api/v1/titles/2/seasons/1/episodes/2/watch", headers=headers)

    # Consultar Biblioteca (al ver todos los episodios de la serie, pasa de siguiendo a vista)
    lib_res = await async_client.get("/api/v1/users/me/library", headers=headers)
    assert lib_res.status_code == 200
    lib = lib_res.json()
    assert len(lib["favorites"]) == 1
    assert lib["favorites"][0]["id"] == 1
    assert len(lib["recently_watched"]) >= 1

    # Consultar Estadísticas
    stats_res = await async_client.get("/api/v1/users/me/stats", headers=headers)
    assert stats_res.status_code == 200
    stats = stats_res.json()
    assert stats["movies_watched_count"] == 1
    assert stats["episodes_watched_count"] == 2
    assert stats["series_watched_count"] == 1
    assert stats["total_hours"] > 0
    assert stats["genres_distribution"]["Action"] == 1
    # Verifica que los 2 episodios de la misma serie solo sumen 1 al género Drama (por título único)
    assert stats["genres_distribution"]["Drama"] == 1


@pytest.mark.asyncio
async def test_home_watched_exclusion_and_type_toggle(async_client: AsyncClient, sample_catalog, db_session: AsyncSession):
    """Verifica que los títulos vistos se mantengan en Home (evitando vaciar o desvirtuar carruseles) y el comportamiento de toggles tipo=tv/movie."""
    uid, token = await create_user_and_token(async_client, "home_user")
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Antes de marcar como visto: Top Gun (id=1) aparece en new_releases y trending
    res_before = await async_client.get("/api/v1/home", headers=headers)
    assert res_before.status_code == 200
    ids_before = [t["id"] for t in res_before.json()["new_releases"]]
    assert 1 in ids_before

    # 2. Marcar Top Gun como visto
    await async_client.post("/api/v1/titles/1/watched", headers=headers)

    # 3. Después de marcar como visto: Top Gun se mantiene en Home (no se vacían ni desvirtúan listas)
    res_after = await async_client.get("/api/v1/home", headers=headers)
    data_after = res_after.json()
    all_home_ids = (
        [t["id"] for t in data_after["trending"]]
        + [t["id"] for t in data_after["new_releases"]]
        + [t["id"] for t in data_after["classics"]]
        + [t["id"] for t in data_after["top_rated"]]
        + [t["id"] for t in data_after["others"]]
    )
    for g_items in data_after["by_genre"].values():
        all_home_ids.extend([t["id"] for t in g_items])
    assert 1 in all_home_ids

    # 4. Toggle tipo=tv: Classics debe ser lista vacía
    res_tv = await async_client.get("/api/v1/home?tipo=tv")
    assert res_tv.status_code == 200
    assert res_tv.json()["classics"] == []

    # 5. Toggle tipo=movie: Solo películas
    res_mv = await async_client.get("/api/v1/home?tipo=movie")
    assert res_mv.status_code == 200
    assert all(t["tipo"] == "movie" for t in res_mv.json()["new_releases"])


@pytest.mark.asyncio
async def test_home_classics_filtering(async_client: AsyncClient, db_session: AsyncSession):
    """Verifica que Classics filtre por >20 años, rating >= 7.5 y votos >= 500."""
    # Película clásica válida (> 20 años, rating 8.2, votos 600)
    classic_valid = Titulo(
        id=90,
        tmdb_id=9001,
        tipo="movie",
        nombre="Pulp Fiction",
        fecha_estreno=date(1994, 10, 14),
        duracion=154,
        popularidad=180.0,
        vote_average_tmdb=8.5,
        vote_count_tmdb=600,
        rating_unificado=8.5
    )
    # Película antigua pero con pocos votos (< 500)
    classic_low_votes = Titulo(
        id=91,
        tmdb_id=9002,
        tipo="movie",
        nombre="Rare Indie 1990",
        fecha_estreno=date(1990, 5, 10),
        popularidad=40.0,
        vote_average_tmdb=8.8,
        vote_count_tmdb=50,
        rating_unificado=8.8
    )
    # Película reciente con buen rating (no es clásico)
    recent_movie = Titulo(
        id=92,
        tmdb_id=9003,
        tipo="movie",
        nombre="Oppenheimer",
        fecha_estreno=date.today() - timedelta(days=20),
        popularidad=300.0,
        vote_average_tmdb=8.9,
        vote_count_tmdb=1500,
        rating_unificado=8.9
    )
    db_session.add_all([classic_valid, classic_low_votes, recent_movie])
    await db_session.commit()

    res = await async_client.get("/api/v1/home")
    assert res.status_code == 200
    data = res.json()
    classic_ids = [t["id"] for t in data["classics"]]
    assert 90 in classic_ids
    assert 91 not in classic_ids
    assert 92 not in classic_ids


@pytest.mark.asyncio
async def test_get_countries_and_languages_endpoints(async_client: AsyncClient, db_session: AsyncSession):
    """Verifica que los endpoints de países e idiomas devuelvan datos agrupados correctamente."""
    t1 = Titulo(id=301, tmdb_id=3001, tipo="movie", nombre="Film US", pais="US", idioma_original="en")
    t2 = Titulo(id=302, tmdb_id=3002, tipo="movie", nombre="Film JP", pais="JP", idioma_original="ja")
    t3 = Titulo(id=303, tmdb_id=3003, tipo="tv", nombre="Series US 2", pais="US", idioma_original="en")
    db_session.add_all([t1, t2, t3])
    await db_session.commit()

    # Países
    res_c = await async_client.get("/api/v1/countries")
    assert res_c.status_code == 200
    countries = res_c.json()
    us_item = next((c for c in countries if c["code"] == "US"), None)
    assert us_item is not None
    assert us_item["count"] >= 2

    # Idiomas
    res_l = await async_client.get("/api/v1/languages")
    assert res_l.status_code == 200
    languages = res_l.json()
    en_item = next((l for l in languages if l["code"] == "en"), None)
    assert en_item is not None
    assert en_item["count"] >= 2


@pytest.mark.asyncio
async def test_catalog_multi_filter_country_and_language(async_client: AsyncClient, db_session: AsyncSession):
    """Verifica filtrado por múltiples países e idiomas."""
    t1 = Titulo(id=401, tmdb_id=4001, tipo="movie", nombre="Film US", pais="US", idioma_original="en")
    t2 = Titulo(id=402, tmdb_id=4002, tipo="movie", nombre="Film JP", pais="JP", idioma_original="ja")
    t3 = Titulo(id=403, tmdb_id=4003, tipo="movie", nombre="Film ES", pais="ES", idioma_original="es")
    db_session.add_all([t1, t2, t3])
    await db_session.commit()

    # Filtro por países (US o JP)
    res_p = await async_client.get("/api/v1/titles?paises=US,JP")
    assert res_p.status_code == 200
    ids = [item["id"] for item in res_p.json()["items"]]
    assert 401 in ids
    assert 402 in ids
    assert 403 not in ids

    # Filtro por idioma (ja o es)
    res_i = await async_client.get("/api/v1/titles?idiomas=ja,es")
    assert res_i.status_code == 200
    ids_i = [item["id"] for item in res_i.json()["items"]]
    assert 402 in ids_i
    assert 403 in ids_i
    assert 401 not in ids_i


@pytest.mark.asyncio
async def test_catalog_genre_canonical_expansion_and_and_or_toggle(async_client: AsyncClient, db_session: AsyncSession):
    """Verifica la expansión de duplas TMDB y los operadores OR y AND para géneros."""
    # Generos en BD
    g_scifi_movie = Genero(id=878, nombre="Science Fiction")
    g_scifi_tv = Genero(id=10765, nombre="Sci-Fi & Fantasy")
    g_comedy = Genero(id=35, nombre="Comedy")
    db_session.add_all([g_scifi_movie, g_scifi_tv, g_comedy])
    await db_session.flush()

    # Película Sci-Fi pura
    m_scifi = Titulo(id=501, tmdb_id=5001, tipo="movie", nombre="Interstellar 2")
    # Película Comedia pura
    m_comedy = Titulo(id=502, tmdb_id=5002, tipo="movie", nombre="Superbad")
    # Serie Sci-Fi & Fantasy + Comedy
    s_scifi_comedy = Titulo(id=503, tmdb_id=5003, tipo="tv", nombre="Rick and Morty")
    db_session.add_all([m_scifi, m_comedy, s_scifi_comedy])
    await db_session.flush()

    await db_session.execute(titulos_generos.insert().values(titulo_id=501, genero_id=878))
    await db_session.execute(titulos_generos.insert().values(titulo_id=502, genero_id=35))
    await db_session.execute(titulos_generos.insert().values(titulo_id=503, genero_id=10765))
    await db_session.execute(titulos_generos.insert().values(titulo_id=503, genero_id=35))
    await db_session.commit()

    # 1. Expansión canónica: buscar "Science Fiction" debe traer tanto la película (878) como la serie (10765)
    res_exp = await async_client.get("/api/v1/titles?generos=Science Fiction")
    assert res_exp.status_code == 200
    ids_exp = [t["id"] for t in res_exp.json()["items"]]
    assert 501 in ids_exp
    assert 503 in ids_exp
    assert 502 not in ids_exp

    # 2. Multi-género con OR (default): Science Fiction O Comedy -> trae 501, 502 y 503
    res_or = await async_client.get("/api/v1/titles?generos=Science Fiction,Comedy&genre_op=or")
    assert res_or.status_code == 200
    ids_or = [t["id"] for t in res_or.json()["items"]]
    assert 501 in ids_or
    assert 502 in ids_or
    assert 503 in ids_or

    # 3. Multi-género con AND: Science Fiction Y Comedy -> solo 503 tiene ambos
    res_and = await async_client.get("/api/v1/titles?generos=Science Fiction,Comedy&genre_op=and")
    assert res_and.status_code == 200
    ids_and = [t["id"] for t in res_and.json()["items"]]
    assert 503 in ids_and
    assert 501 not in ids_and
    assert 502 not in ids_and

    # 4. Verificar que GET /genres no exponga "Sci-Fi & Fantasy" ni "Action & Adventure"
    res_g = await async_client.get("/api/v1/genres")
    assert res_g.status_code == 200
    genre_names = [g["nombre"] for g in res_g.json()]
    assert "Sci-Fi & Fantasy" not in genre_names
    assert "Action & Adventure" not in genre_names
    assert "Science Fiction" in genre_names
    assert "Comedy" in genre_names

