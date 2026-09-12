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
