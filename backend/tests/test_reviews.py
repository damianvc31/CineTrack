from datetime import date, timedelta
import pytest
from httpx import AsyncClient
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Titulo
from app.schemas.catalog import ReviewCreate
from tests.test_catalog import create_user_and_token


def test_review_create_half_step_validation():
    # Valid scores
    valid_scores = [0.0, 0.5, 1.0, 7.5, 8.0, 9.5, 10.0, None]
    for s in valid_scores:
        r = ReviewCreate(puntaje=s, texto="Excelente película muy recomendada")
        assert r.puntaje == s

    # Invalid scores
    invalid_scores = [7.3, 0.2, 9.9, -0.5, 10.5, 11.0]
    for s in invalid_scores:
        with pytest.raises(ValidationError):
            ReviewCreate(puntaje=s, texto="Excelente película muy recomendada")


@pytest.mark.asyncio
async def test_review_crud_and_upsert(async_client: AsyncClient, db_session: AsyncSession):
    # 1. Crear título
    title = Titulo(
        id=1,
        tmdb_id=1001,
        tipo="movie",
        nombre="Inception",
        fecha_estreno=date(2010, 7, 16),
        popularidad=100.0,
        vote_average_tmdb=8.5,
        vote_count_tmdb=1000,
        rating_unificado=8.5
    )
    db_session.add(title)
    await db_session.commit()

    # 2. Registrar usuario
    user_id, token = await create_user_and_token(async_client, "reviewer_1")
    headers = {"Authorization": f"Bearer {token}"}

    # 3. Post review con puntaje 8.5
    res = await async_client.post(
        "/api/v1/titles/1/reviews",
        json={"puntaje": 8.5, "texto": "Obra maestra de Christopher Nolan"},
        headers=headers
    )
    assert res.status_code == 201
    data = res.json()
    assert data["puntaje"] == 8.5
    assert data["texto"] == "Obra maestra de Christopher Nolan"
    assert data["usuario_id"] == user_id
    review_id = data["id"]

    # 4. Upsert: Mismo usuario edita la reseña (puntaje 9.0)
    res_edit = await async_client.post(
        "/api/v1/titles/1/reviews",
        json={"puntaje": 9.0, "texto": "Edición: Realmente es una obra maestra absoluta"},
        headers=headers
    )
    assert res_edit.status_code == 201
    data_edit = res_edit.json()
    assert data_edit["id"] == review_id
    assert data_edit["puntaje"] == 9.0
    assert "Edición" in data_edit["texto"]

    # 5. Listar reseñas del título
    res_list = await async_client.get("/api/v1/titles/1/reviews")
    assert res_list.status_code == 200
    reviews = res_list.json()
    assert len(reviews) == 1
    assert reviews[0]["puntaje"] == 9.0

    # 6. Listar en /api/v1/users/me/reviews
    res_my_reviews = await async_client.get("/api/v1/users/me/reviews", headers=headers)
    assert res_my_reviews.status_code == 200
    my_reviews = res_my_reviews.json()
    assert my_reviews["total"] == 1
    assert my_reviews["items"][0]["titulo_nombre"] == "Inception"
    assert my_reviews["items"][0]["puntaje"] == 9.0

    # 7. Eliminar reseña
    res_del = await async_client.delete("/api/v1/titles/1/reviews", headers=headers)
    assert res_del.status_code == 200

    # 8. Comprobar que ya no está
    res_list_after = await async_client.get("/api/v1/titles/1/reviews")
    assert len(res_list_after.json()) == 0

    # 9. Eliminar de nuevo devuelve 404
    res_del_404 = await async_client.delete("/api/v1/titles/1/reviews", headers=headers)
    assert res_del_404.status_code == 404


@pytest.mark.asyncio
async def test_review_optional_score_and_pending(async_client: AsyncClient, db_session: AsyncSession):
    # 1. Crear títulos
    t1 = Titulo(
        id=1,
        tmdb_id=2001,
        tipo="movie",
        nombre="Interstellar",
        fecha_estreno=date(2014, 11, 7),
        popularidad=100.0,
        vote_average_tmdb=8.6,
        vote_count_tmdb=1500,
        rating_unificado=8.6
    )
    t2 = Titulo(
        id=2,
        tmdb_id=2002,
        tipo="movie",
        nombre="Memento",
        fecha_estreno=date(2000, 10, 11),
        popularidad=80.0,
        vote_average_tmdb=8.4,
        vote_count_tmdb=800,
        rating_unificado=8.4
    )
    db_session.add_all([t1, t2])
    await db_session.commit()

    # 2. Usuario
    user_id, token = await create_user_and_token(async_client, "reviewer_2")
    headers = {"Authorization": f"Bearer {token}"}

    # 3. Marcar ambos como "vista"
    await async_client.post("/api/v1/titles/1/watched", headers=headers)
    await async_client.post("/api/v1/titles/2/watched", headers=headers)

    # 4. Ambos deben estar en /users/me/unreviewed-watched
    res_unrev = await async_client.get("/api/v1/users/me/unreviewed-watched", headers=headers)
    assert res_unrev.status_code == 200
    pending_items = res_unrev.json()["items"]
    assert len(pending_items) == 2
    pending_ids = [p["id"] for p in pending_items]
    assert 1 in pending_ids
    assert 2 in pending_ids

    # 5. Escribir reseña para t1 SIN puntaje (puntaje=None)
    res_no_score = await async_client.post(
        "/api/v1/titles/1/reviews",
        json={"puntaje": None, "texto": "Increíble banda sonora e imágenes espaciales."},
        headers=headers
    )
    assert res_no_score.status_code == 201
    assert res_no_score.json()["puntaje"] is None

    # 6. Ahora t1 ya no debe estar en /users/me/unreviewed-watched, pero t2 sí
    res_unrev2 = await async_client.get("/api/v1/users/me/unreviewed-watched", headers=headers)
    pending_items2 = res_unrev2.json()["items"]
    assert len(pending_items2) == 1
    assert pending_items2[0]["id"] == 2

    # 7. Crear una serie con episodios y marcar 1 episodio visto (estado = 'siguiendo')
    from app.models import Temporada, Episodio
    s1 = Titulo(
        id=3,
        tmdb_id=2003,
        tipo="tv",
        nombre="Severance",
        fecha_estreno=date(2022, 2, 18),
        popularidad=95.0,
        vote_average_tmdb=8.7,
        vote_count_tmdb=1100,
        rating_unificado=8.7
    )
    temp = Temporada(id=10, titulo_id=3, numero=1)
    ep1 = Episodio(id=101, temporada_id=10, numero=1, nombre="Good News About Hell", fecha_estreno=date(2022, 2, 18))
    ep2 = Episodio(id=102, temporada_id=10, numero=2, nombre="Half Loop", fecha_estreno=date(2022, 2, 18))
    db_session.add_all([s1, temp, ep1, ep2])
    await db_session.commit()

    # Marcar solo el episodio 1 como visto -> la serie queda en estado "siguiendo" (sin terminar)
    await async_client.post("/api/v1/episodes/101/watch", headers=headers)

    # Debe aparecer en /users/me/unreviewed-watched porque ya se vio al menos un episodio
    res_unrev3 = await async_client.get("/api/v1/users/me/unreviewed-watched", headers=headers)
    pending_items3 = res_unrev3.json()["items"]
    pending_ids3 = [p["id"] for p in pending_items3]
    assert 3 in pending_ids3
    s3_item = next(p for p in pending_items3 if p["id"] == 3)
    assert s3_item["user_estado"] == "siguiendo"

    # 8. Abandonar la serie (unfollow) -> debe seguir apareciendo en unreviewed-watched pero con estado 'abandonada'
    res_abandon = await async_client.post("/api/v1/titles/3/unfollow", headers=headers)
    assert res_abandon.status_code == 200

    res_unrev4 = await async_client.get("/api/v1/users/me/unreviewed-watched", headers=headers)
    pending_items4 = res_unrev4.json()["items"]
    pending_ids4 = [p["id"] for p in pending_items4]
    assert 3 in pending_ids4
    s3_abandoned_item = next(p for p in pending_items4 if p["id"] == 3)
    assert s3_abandoned_item["user_estado"] == "abandonada"


@pytest.mark.asyncio
async def test_review_score_only_without_text(async_client: AsyncClient, db_session: AsyncSession):
    # 1. Crear título
    title = Titulo(
        id=99,
        tmdb_id=9999,
        tipo="movie",
        nombre="Dune: Part Two",
        fecha_estreno=date(2024, 3, 1),
        popularidad=150.0,
        vote_average_tmdb=8.5,
        vote_count_tmdb=2000,
        rating_unificado=8.5
    )
    db_session.add(title)
    await db_session.commit()

    user_id, token = await create_user_and_token(async_client, "score_only_user")
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Reseña sin puntaje ni texto debe fallar con 422
    res_empty = await async_client.post(
        "/api/v1/titles/99/reviews",
        json={"puntaje": None, "texto": ""},
        headers=headers
    )
    assert res_empty.status_code == 422

    # 3. Reseña sin puntaje con texto demasiado corto (< 5 chars) debe fallar con 422
    res_short = await async_client.post(
        "/api/v1/titles/99/reviews",
        json={"puntaje": None, "texto": "meh"},
        headers=headers
    )
    assert res_short.status_code == 422

    # 4. Reseña con SOLO puntaje y texto nulo/vacío debe guardarse exitosamente
    res_score_only = await async_client.post(
        "/api/v1/titles/99/reviews",
        json={"puntaje": 9.5, "texto": None},
        headers=headers
    )
    assert res_score_only.status_code == 201
    data = res_score_only.json()
    assert data["puntaje"] == 9.5
    assert data["texto"] is None
    assert data["usuario_id"] == user_id

    # 5. Listar reseñas del título
    res_list = await async_client.get("/api/v1/titles/99/reviews")
    assert res_list.status_code == 200
    revs = res_list.json()
    assert len(revs) == 1
    assert revs[0]["puntaje"] == 9.5
    assert revs[0]["texto"] is None

    # 6. Listar en /api/v1/users/me/reviews
    res_my = await async_client.get("/api/v1/users/me/reviews", headers=headers)
    assert res_my.status_code == 200
    my_revs = res_my.json()
    assert my_revs["total"] == 1
    assert my_revs["items"][0]["puntaje"] == 9.5
    assert my_revs["items"][0]["texto"] is None


