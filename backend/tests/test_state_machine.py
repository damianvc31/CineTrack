from datetime import date, timedelta
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.episodio import Episodio
from app.models.temporada import Temporada
from app.models.titulo import Titulo


async def create_user_and_get_token(client: AsyncClient, username: str) -> str:
    """Helper para registrar un usuario y obtener su Bearer token."""
    res = await client.post("/api/v1/auth/register", json={
        "nombre_usuario": username,
        "password": "password123"
    })
    return res.json()["access_token"]


@pytest.mark.asyncio
async def test_pelicula_state_machine(async_client: AsyncClient, db_session: AsyncSession):
    """Verifica la máquina de estados completa para películas."""
    # 1. Crear película en DB
    pelicula = Titulo(tmdb_id=1001, tipo="movie", nombre="Oppenheimer", duracion=180)
    db_session.add(pelicula)
    await db_session.commit()
    await db_session.refresh(pelicula)

    token = await create_user_and_get_token(async_client, "user_movie")
    headers = {"Authorization": f"Bearer {token}"}

    # Estado inicial: sin estado
    state_res = await async_client.get(f"/api/v1/titles/{pelicula.id}/user-state", headers=headers)
    assert state_res.status_code == 200
    assert state_res.json()["estado"] is None
    assert state_res.json()["favorito"] is False
    assert state_res.json()["fecha_estado"] is None

    # Toggle Favorito (ortogonal)
    fav_res = await async_client.post(f"/api/v1/titles/{pelicula.id}/favorite", headers=headers)
    assert fav_res.status_code == 200
    assert fav_res.json()["favorito"] is True
    assert fav_res.json()["fecha_favorito"] is not None

    # Agregar a Watchlist
    wl_res = await async_client.post(f"/api/v1/titles/{pelicula.id}/watchlist", headers=headers)
    assert wl_res.status_code == 200
    assert wl_res.json()["nuevo_estado"] == "watchlist"
    assert wl_res.json()["fecha_estado"] is not None

    # Quitar de Watchlist -> pasa a SinEstado (fecha_estado = None)
    wl_remove = await async_client.post(f"/api/v1/titles/{pelicula.id}/watchlist", headers=headers)
    assert wl_remove.status_code == 200
    assert wl_remove.json()["nuevo_estado"] is None
    assert wl_remove.json()["fecha_estado"] is None

    # Marcar Vista
    watched_res = await async_client.post(f"/api/v1/titles/{pelicula.id}/watched", headers=headers)
    assert watched_res.status_code == 200
    assert watched_res.json()["nuevo_estado"] == "vista"
    assert watched_res.json()["fecha_estado"] is not None

    # Regla: Bookmark bloqueado en Vista -> Error 400
    blocked_wl = await async_client.post(f"/api/v1/titles/{pelicula.id}/watchlist", headers=headers)
    assert blocked_wl.status_code == 400
    assert "No se puede agregar a Watchlist" in blocked_wl.json()["detail"]

    # Desmarcar Vista -> vuelve a SinEstado (fecha_estado = None)
    unwatched_res = await async_client.post(f"/api/v1/titles/{pelicula.id}/watched", headers=headers)
    assert unwatched_res.status_code == 200
    assert unwatched_res.json()["nuevo_estado"] is None
    assert unwatched_res.json()["fecha_estado"] is None


@pytest.mark.asyncio
async def test_serie_state_machine_and_episode_progress(async_client: AsyncClient, db_session: AsyncSession):
    """Verifica transiciones de estado de series mediante episodios y reglas de bloqueo."""
    # Crear serie con 1 temporada de 3 episodios
    serie = Titulo(tmdb_id=2001, tipo="tv", nombre="Severance")
    temp = Temporada(titulo=serie, numero=1)
    ep1 = Episodio(temporada=temp, numero=1, nombre="Good News About Hell", fecha_estreno=date(2022, 2, 18))
    ep2 = Episodio(temporada=temp, numero=2, nombre="Half Loop", fecha_estreno=date(2022, 2, 18))
    ep3 = Episodio(temporada=temp, numero=3, nombre="In Perpetuity", fecha_estreno=date(2022, 2, 25))

    db_session.add_all([serie, temp, ep1, ep2, ep3])
    await db_session.commit()
    await db_session.refresh(serie)
    await db_session.refresh(ep1)
    await db_session.refresh(ep2)
    await db_session.refresh(ep3)

    token = await create_user_and_get_token(async_client, "user_series")
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Agregar a Watchlist
    wl_res = await async_client.post(f"/api/v1/titles/{serie.id}/watchlist", headers=headers)
    assert wl_res.status_code == 200
    assert wl_res.json()["nuevo_estado"] == "watchlist"

    # 2. Marcar primer episodio -> pasa automáticamente a 'siguiendo' y registra fecha_estado
    ep1_res = await async_client.post(f"/api/v1/episodes/{ep1.id}/watch", headers=headers)
    assert ep1_res.status_code == 200
    assert ep1_res.json()["visto"] is True
    assert ep1_res.json()["nuevo_estado_serie"] == "siguiendo"
    assert ep1_res.json()["episodios_vistos_serie"] == 1
    assert ep1_res.json()["total_episodios_serie"] == 3

    # 3. Regla: Bookmark bloqueado en Siguiendo -> Error 400
    blocked_wl = await async_client.post(f"/api/v1/titles/{serie.id}/watchlist", headers=headers)
    assert blocked_wl.status_code == 400

    # 4. Marcar segundo y tercer episodio -> al completar todos pasa a 'vista'
    await async_client.post(f"/api/v1/episodes/{ep2.id}/watch", headers=headers)
    ep3_res = await async_client.post(f"/api/v1/episodes/{ep3.id}/watch", headers=headers)
    assert ep3_res.status_code == 200
    assert ep3_res.json()["nuevo_estado_serie"] == "vista"
    assert ep3_res.json()["porcentaje_progreso"] == 100.0

    # 5. Desmarcar un episodio desde Vista -> vuelve automáticamente a 'siguiendo'
    ep3_unwatch = await async_client.post(f"/api/v1/episodes/{ep3.id}/watch", headers=headers)
    assert ep3_unwatch.status_code == 200
    assert ep3_unwatch.json()["visto"] is False
    assert ep3_unwatch.json()["nuevo_estado_serie"] == "siguiendo"
    assert ep3_unwatch.json()["episodios_vistos_serie"] == 2

    # 6. Desmarcar los otros dos hasta quedar en 0 -> pasa a SinEstado
    await async_client.post(f"/api/v1/episodes/{ep2.id}/watch", headers=headers)
    ep1_unwatch = await async_client.post(f"/api/v1/episodes/{ep1.id}/watch", headers=headers)
    assert ep1_unwatch.status_code == 200
    assert ep1_unwatch.json()["nuevo_estado_serie"] is None
    assert ep1_unwatch.json()["episodios_vistos_serie"] == 0


@pytest.mark.asyncio
async def test_serie_abandon_and_preserve_progress(async_client: AsyncClient, db_session: AsyncSession):
    """Verifica que abandonar una serie (❌) pasa a SinEstado pero conserva los episodios vistos."""
    serie = Titulo(tmdb_id=3001, tipo="tv", nombre="Lost")
    temp = Temporada(titulo=serie, numero=1)
    ep1 = Episodio(temporada=temp, numero=1, nombre="Pilot 1")
    ep2 = Episodio(temporada=temp, numero=2, nombre="Pilot 2")
    db_session.add_all([serie, temp, ep1, ep2])
    await db_session.commit()
    await db_session.refresh(serie)
    await db_session.refresh(ep1)

    token = await create_user_and_get_token(async_client, "user_abandon")
    headers = {"Authorization": f"Bearer {token}"}

    # Ver ep1 -> estado pasa a siguiendo
    await async_client.post(f"/api/v1/episodes/{ep1.id}/watch", headers=headers)

    # Abandonar serie
    abandon_res = await async_client.post(f"/api/v1/titles/{serie.id}/unfollow", headers=headers)
    assert abandon_res.status_code == 200
    assert abandon_res.json()["nuevo_estado"] == "abandonada"

    # Verificar que el estado es abandonada pero el progreso se conserva (1 episodio visto)
    st = await async_client.get(f"/api/v1/titles/{serie.id}/user-state", headers=headers)
    assert st.json()["estado"] == "abandonada"
    assert st.json()["episodios_vistos"] == 1
    assert st.json()["total_episodios"] == 2

    # Reanudar seguimiento con follow (Reanudar / Follow)
    follow_res = await async_client.post(f"/api/v1/titles/{serie.id}/follow", headers=headers)
    assert follow_res.status_code == 200
    assert follow_res.json()["nuevo_estado"] == "siguiendo"

    st_follow = await async_client.get(f"/api/v1/titles/{serie.id}/user-state", headers=headers)
    assert st_follow.json()["estado"] == "siguiendo"
    assert st_follow.json()["episodios_vistos"] == 1

    # Volver a abandonar y poner en Watchlist conservando progreso previo
    await async_client.post(f"/api/v1/titles/{serie.id}/unfollow", headers=headers)
    wl_res = await async_client.post(f"/api/v1/titles/{serie.id}/watchlist", headers=headers)
    assert wl_res.status_code == 200
    assert wl_res.json()["nuevo_estado"] == "watchlist"

    st_after = await async_client.get(f"/api/v1/titles/{serie.id}/user-state", headers=headers)
    assert st_after.json()["estado"] == "watchlist"
    assert st_after.json()["episodios_vistos"] == 1


@pytest.mark.asyncio
async def test_serie_resume_follow_validation(async_client: AsyncClient, db_session: AsyncSession):
    """Verifica validaciones de /titles/{id}/follow (requiere episodios vistos y no estar en siguiendo/vista)."""
    serie = Titulo(tmdb_id=3002, tipo="tv", nombre="Fringe")
    temp = Temporada(titulo=serie, numero=1)
    ep1 = Episodio(temporada=temp, numero=1, nombre="Pilot")
    ep2 = Episodio(temporada=temp, numero=2, nombre="The Same Old Story")
    db_session.add_all([serie, temp, ep1, ep2])
    await db_session.commit()
    await db_session.refresh(serie)
    await db_session.refresh(ep1)
    serie_id = serie.id
    ep1_id = ep1.id

    token = await create_user_and_get_token(async_client, "user_follow_val")
    headers = {"Authorization": f"Bearer {token}"}

    # Intentar follow sin haber visto ningún episodio -> 400 Bad Request
    res_no_ep = await async_client.post(f"/api/v1/titles/{serie_id}/follow", headers=headers)
    assert res_no_ep.status_code == 400
    assert "No se puede reanudar una serie sin episodios vistos" in res_no_ep.json()["detail"]

    # Marcar episodio -> pasa a siguiendo
    await async_client.post(f"/api/v1/episodes/{ep1_id}/watch", headers=headers)

    # Intentar follow cuando ya está en siguiendo -> 400 Bad Request
    res_already_following = await async_client.post(f"/api/v1/titles/{serie_id}/follow", headers=headers)
    assert res_already_following.status_code == 400
    assert "ya se encuentra en estado 'siguiendo'" in res_already_following.json()["detail"]


@pytest.mark.asyncio
async def test_serie_watch_all_and_unwatch_all(async_client: AsyncClient, db_session: AsyncSession):
    """Verifica que marcar serie entera con ojo (👁) marca todos los episodios,
    y desmarcar con ojo (👁‍🗨) borra todos los episodios vistos (reinicio desde cero).
    """
    serie = Titulo(tmdb_id=4001, tipo="tv", nombre="Chernobyl")
    temp = Temporada(titulo=serie, numero=1)
    episodes = [Episodio(temporada=temp, numero=i, nombre=f"Episodio {i}") for i in range(1, 6)]
    db_session.add_all([serie, temp] + episodes)
    await db_session.commit()
    await db_session.refresh(serie)

    token = await create_user_and_get_token(async_client, "user_reset")
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Marcar serie completa con ojo (👁)
    watch_all = await async_client.post(f"/api/v1/titles/{serie.id}/watched", headers=headers)
    assert watch_all.status_code == 200
    assert watch_all.json()["nuevo_estado"] == "vista"

    # Comprobar que todos los 5 episodios están marcados
    st1 = await async_client.get(f"/api/v1/titles/{serie.id}/user-state", headers=headers)
    assert st1.json()["estado"] == "vista"
    assert st1.json()["episodios_vistos"] == 5
    assert st1.json()["porcentaje_progreso"] == 100.0

    # 2. Desmarcar serie completa con ojo (👁‍🗨) -> reseteo de cero
    unwatch_all = await async_client.post(f"/api/v1/titles/{serie.id}/watched", headers=headers)
    assert unwatch_all.status_code == 200
    assert unwatch_all.json()["nuevo_estado"] is None

    # Comprobar que los episodios vistos cayeron a 0
    st2 = await async_client.get(f"/api/v1/titles/{serie.id}/user-state", headers=headers)
    assert st2.json()["estado"] is None
    assert st2.json()["episodios_vistos"] == 0
    assert st2.json()["porcentaje_progreso"] == 0.0


@pytest.mark.asyncio
async def test_block_future_episodes(async_client: AsyncClient, db_session: AsyncSession):
    """Verifica que no se permita marcar como visto un episodio con fecha futura."""
    serie = Titulo(tmdb_id=5001, tipo="tv", nombre="Future Show")
    temp = Temporada(titulo=serie, numero=1)
    fecha_futura = date.today() + timedelta(days=7)
    ep_futuro = Episodio(temporada=temp, numero=1, nombre="Unaired Episode", fecha_estreno=fecha_futura)

    db_session.add_all([serie, temp, ep_futuro])
    await db_session.commit()
    await db_session.refresh(ep_futuro)

    token = await create_user_and_get_token(async_client, "user_future")
    headers = {"Authorization": f"Bearer {token}"}

    res = await async_client.post(f"/api/v1/episodes/{ep_futuro.id}/watch", headers=headers)
    assert res.status_code == 400
    assert "fecha de estreno futura" in res.json()["detail"]


@pytest.mark.asyncio
async def test_watch_episode_by_season_and_episode_numbers(async_client: AsyncClient, db_session: AsyncSession):
    """Verifica el marcado de episodio por números semánticos (season_number y episode_number)."""
    serie = Titulo(tmdb_id=6001, tipo="tv", nombre="Fargo")
    temp1 = Temporada(titulo=serie, numero=1)
    temp2 = Temporada(titulo=serie, numero=2)
    ep1_1 = Episodio(temporada=temp1, numero=1, nombre="S01E01")
    ep2_3 = Episodio(temporada=temp2, numero=3, nombre="S02E03")

    db_session.add_all([serie, temp1, temp2, ep1_1, ep2_3])
    await db_session.commit()
    await db_session.refresh(serie)

    token = await create_user_and_get_token(async_client, "user_semantic_ep")
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Marcar S01E01
    res1 = await async_client.post(
        f"/api/v1/titles/{serie.id}/seasons/1/episodes/1/watch",
        headers=headers
    )
    assert res1.status_code == 200
    data1 = res1.json()
    assert data1["visto"] is True
    assert data1["nuevo_estado_serie"] == "siguiendo"
    assert data1["episodios_vistos_serie"] == 1

    # 2. Intentar marcar episodio inexistente -> 404
    res_not_found = await async_client.post(
        f"/api/v1/titles/{serie.id}/seasons/1/episodes/99/watch",
        headers=headers
    )
    assert res_not_found.status_code == 404

    # 3. Desmarcar S01E01
    res_unwatch = await async_client.post(
        f"/api/v1/titles/{serie.id}/seasons/1/episodes/1/watch",
        headers=headers
    )
    assert res_unwatch.status_code == 200
    assert res_unwatch.json()["visto"] is False
    assert res_unwatch.json()["episodios_vistos_serie"] == 0


@pytest.mark.asyncio
async def test_toggle_season_watch(async_client: AsyncClient, db_session: AsyncSession):
    """Verifica marcar y desmarcar temporadas completas (por id y por número)."""
    serie = Titulo(tmdb_id=7001, tipo="tv", nombre="True Detective")
    temp1 = Temporada(titulo=serie, numero=1)
    temp2 = Temporada(titulo=serie, numero=2)
    # Temporada 1: 3 episodios
    eps_t1 = [Episodio(temporada=temp1, numero=i, nombre=f"T1E{i}") for i in range(1, 4)]
    # Temporada 2: 2 episodios
    eps_t2 = [Episodio(temporada=temp2, numero=i, nombre=f"T2E{i}") for i in range(1, 3)]

    db_session.add_all([serie, temp1, temp2, *eps_t1, *eps_t2])
    await db_session.commit()
    await db_session.refresh(serie)
    await db_session.refresh(temp1)

    token = await create_user_and_get_token(async_client, "user_season_watcher")
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Marcar temporada 1 completa por número semántico -> debe marcar 3 episodios
    res1 = await async_client.post(
        f"/api/v1/titles/{serie.id}/seasons/1/watch",
        headers=headers
    )
    assert res1.status_code == 200
    data1 = res1.json()
    assert data1["temporada_vista"] is True
    assert data1["episodios_afectados"] == 3
    assert data1["episodios_vistos_serie"] == 3
    assert data1["total_episodios_serie"] == 5
    assert data1["nuevo_estado_serie"] == "siguiendo"

    # 2. Desmarcar temporada 1 por ID directo -> debe desmarcar 3 episodios
    res_unwatch = await async_client.post(
        f"/api/v1/seasons/{temp1.id}/watch",
        headers=headers
    )
    assert res_unwatch.status_code == 200
    data_unwatch = res_unwatch.json()
    assert data_unwatch["temporada_vista"] is False
    assert data_unwatch["episodios_afectados"] == 3
    assert data_unwatch["episodios_vistos_serie"] == 0
    assert data_unwatch["nuevo_estado_serie"] is None


@pytest.mark.asyncio
async def test_series_with_future_episodes_only_marks_released(async_client: AsyncClient, db_session: AsyncSession):
    """Verifica que marcar una serie con episodios futuros como vista solo marque los emitidos y quede en Vista."""
    serie = Titulo(tmdb_id=8801, tipo="tv", nombre="Ongoing Hit")
    temp = Temporada(titulo=serie, numero=1)
    past_date = date.today() - timedelta(days=10)
    future_date = date.today() + timedelta(days=30)
    ep_released = Episodio(temporada=temp, numero=1, nombre="Ep 1 Released", fecha_estreno=past_date)
    ep_unreleased = Episodio(temporada=temp, numero=2, nombre="Ep 2 Future", fecha_estreno=future_date)

    db_session.add_all([serie, temp, ep_released, ep_unreleased])
    await db_session.commit()
    await db_session.refresh(serie)

    token = await create_user_and_get_token(async_client, "user_future_series")
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Marcar serie completa como vista (👁)
    res = await async_client.post(f"/api/v1/titles/{serie.id}/watched", headers=headers)
    assert res.status_code == 200
    assert res.json()["nuevo_estado"] == "vista"

    # 2. Verificar detalle: solo el episodio emitido está visto
    detail_res = await async_client.get(f"/api/v1/titles/{serie.id}", headers=headers)
    assert detail_res.status_code == 200
    detail = detail_res.json()
    assert detail["user_estado"] == "vista"
    episodes = detail["temporadas"][0]["episodios"]
    assert episodes[0]["visto"] is True
    assert episodes[1]["visto"] is False

    # 3. Intentar marcar el episodio futuro individualmente -> bloqueado
    unreleased_ep_id = episodes[1]["id"]
    err_res = await async_client.post(f"/api/v1/episodes/{unreleased_ep_id}/watch", headers=headers)
    assert err_res.status_code == 400
