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

    # Película
    m1 = Titulo(
        id=1,
        tmdb_id=101,
        tipo="movie",
        nombre="Top Gun",
        anio_estreno=2022,
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
        anio_estreno=2008,
        anio_fin=2013,
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
    assert "by_genre" in data
    assert len(data["trending"]) >= 1


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

    # 3. Listar géneros
    res_g = await async_client.get("/api/v1/genres")
    assert res_g.status_code == 200
    assert len(res_g.json()) >= 2


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

    # 2. Marcar episodio 1 de Breaking Bad como visto -> pone serie en 'siguiendo'
    await async_client.post("/api/v1/titles/2/seasons/1/episodes/1/watch", headers=headers)

    # Consultar Biblioteca
    lib_res = await async_client.get("/api/v1/users/me/library", headers=headers)
    assert lib_res.status_code == 200
    lib = lib_res.json()
    assert len(lib["favorites"]) == 1
    assert lib["favorites"][0]["id"] == 1
    assert len(lib["recently_watched"]) == 1
    assert len(lib["following"]) == 1
    assert lib["following"][0]["id"] == 2

    # Consultar Estadísticas
    stats_res = await async_client.get("/api/v1/users/me/stats", headers=headers)
    assert stats_res.status_code == 200
    stats = stats_res.json()
    assert stats["movies_watched_count"] == 1
    assert stats["episodes_watched_count"] == 1
    assert stats["total_hours"] > 0
    assert "Action" in stats["genres_distribution"]
