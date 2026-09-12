from datetime import date, datetime, timezone
from fastapi import HTTPException, status
from sqlalchemy import delete, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.episodio import Episodio
from app.models.episodio_visto import EpisodioVisto
from app.models.estado import EstadoUsuarioTitulo
from app.models.temporada import Temporada
from app.models.titulo import Titulo
from app.schemas.state import (
    EpisodeWatchResponse,
    FavoriteToggleResponse,
    StateChangeResponse,
    TitleUserStateResponse,
)


def _now() -> datetime:
    return datetime.now(timezone.utc)


async def get_or_create_title_state(
    db: AsyncSession,
    usuario_id: int,
    titulo_id: int
) -> EstadoUsuarioTitulo:
    """Obtiene el registro de estado del usuario sobre un título o lo inicializa en blanco."""
    query = select(EstadoUsuarioTitulo).where(
        EstadoUsuarioTitulo.usuario_id == usuario_id,
        EstadoUsuarioTitulo.titulo_id == titulo_id
    )
    res = await db.execute(query)
    estado = res.scalar_one_or_none()

    if not estado:
        estado = EstadoUsuarioTitulo(
            usuario_id=usuario_id,
            titulo_id=titulo_id,
            favorito=False,
            fecha_favorito=None,
            estado=None,
            fecha_estado=None
        )
        db.add(estado)
        await db.flush()

    return estado


async def toggle_favorite(
    db: AsyncSession,
    usuario_id: int,
    titulo_id: int
) -> FavoriteToggleResponse:
    """Alterna el favorito (♥) de forma ortogonal e independiente de cualquier estado."""
    # Verificar existencia del título
    titulo = await db.get(Titulo, titulo_id)
    if not titulo:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Título no encontrado.")

    estado_obj = await get_or_create_title_state(db, usuario_id, titulo_id)
    estado_obj.favorito = not estado_obj.favorito
    estado_obj.fecha_favorito = _now() if estado_obj.favorito else None

    await db.commit()
    return FavoriteToggleResponse(
        titulo_id=titulo_id,
        favorito=estado_obj.favorito,
        fecha_favorito=estado_obj.fecha_favorito
    )


async def toggle_watchlist(
    db: AsyncSession,
    usuario_id: int,
    titulo_id: int
) -> StateChangeResponse:
    """Alterna el estado Watchlist (🔖). Lanza 400 si el título está en 'vista' o 'siguiendo'."""
    titulo = await db.get(Titulo, titulo_id)
    if not titulo:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Título no encontrado.")

    estado_obj = await get_or_create_title_state(db, usuario_id, titulo_id)

    # Regla: Bookmark bloqueado si está en Vista o Siguiendo
    if estado_obj.estado in ("vista", "siguiendo"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"No se puede agregar a Watchlist un título en estado '{estado_obj.estado}'. Desmárquelo o abandónelo primero."
        )

    if estado_obj.estado == "watchlist":
        # Quitar de watchlist -> pasa a SinEstado
        estado_obj.estado = None
        estado_obj.fecha_estado = None
        mensaje = "Título quitado de Watchlist."
    else:
        # Pasa a watchlist
        estado_obj.estado = "watchlist"
        estado_obj.fecha_estado = _now()
        mensaje = "Título agregado a Watchlist."

    await db.commit()
    return StateChangeResponse(
        titulo_id=titulo_id,
        nuevo_estado=estado_obj.estado,
        fecha_estado=estado_obj.fecha_estado,
        mensaje=mensaje
    )


async def toggle_watched(
    db: AsyncSession,
    usuario_id: int,
    titulo_id: int
) -> StateChangeResponse:
    """Marca o desmarca un título completo como Visto (👁).
    En películas: toggle simple Vista <-> SinEstado.
    En series:
      - Si no está Vista: marca todos los episodios disponibles como vistos y pasa a Vista.
      - Si ya está Vista: borra todos los episodios vistos de esa serie (reseteo) y pasa a SinEstado.
    """
    titulo = await db.get(Titulo, titulo_id)
    if not titulo:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Título no encontrado.")

    estado_obj = await get_or_create_title_state(db, usuario_id, titulo_id)

    if titulo.tipo == "movie":
        if estado_obj.estado == "vista":
            estado_obj.estado = None
            estado_obj.fecha_estado = None
            mensaje = "Película desmarcada como vista."
        else:
            estado_obj.estado = "vista"
            estado_obj.fecha_estado = _now()
            mensaje = "Película marcada como vista."
    else:
        # Es una serie: obtener los IDs de episodios emitidos hasta la fecha
        today = date.today()
        ep_query = (
            select(Episodio.id)
            .join(Temporada, Episodio.temporada_id == Temporada.id)
            .where(
                Temporada.titulo_id == titulo_id,
                or_(Episodio.fecha_estreno.is_(None), Episodio.fecha_estreno <= today)
            )
        )
        ep_res = await db.execute(ep_query)
        eligible_episode_ids = [row[0] for row in ep_res.all()]

        if estado_obj.estado == "vista":
            # Desmarcar serie completa: borrar todos los episodios vistos de esta serie (empezar de cero)
            all_ep_query = (
                select(Episodio.id)
                .join(Temporada, Episodio.temporada_id == Temporada.id)
                .where(Temporada.titulo_id == titulo_id)
            )
            all_ep_res = await db.execute(all_ep_query)
            all_episode_ids = [row[0] for row in all_ep_res.all()]
            if all_episode_ids:
                await db.execute(
                    delete(EpisodioVisto).where(
                        EpisodioVisto.usuario_id == usuario_id,
                        EpisodioVisto.episodio_id.in_(all_episode_ids)
                    )
                )
            estado_obj.estado = None
            estado_obj.fecha_estado = None
            mensaje = "Serie desmarcada por completo (progreso reiniciado)."
        else:
            # Marcar serie completa: marcar todos los episodios emitidos como vistos
            if eligible_episode_ids:
                vistos_query = select(EpisodioVisto.episodio_id).where(
                    EpisodioVisto.usuario_id == usuario_id,
                    EpisodioVisto.episodio_id.in_(eligible_episode_ids)
                )
                vistos_res = await db.execute(vistos_query)
                already_watched = {row[0] for row in vistos_res.all()}

                now_ts = _now()
                new_vistos = [
                    EpisodioVisto(usuario_id=usuario_id, episodio_id=eid, fecha_visto=now_ts)
                    for eid in eligible_episode_ids if eid not in already_watched
                ]
                db.add_all(new_vistos)

            estado_obj.estado = "vista"
            estado_obj.fecha_estado = _now()
            mensaje = "Serie completa marcada como vista."

    await db.commit()
    return StateChangeResponse(
        titulo_id=titulo_id,
        nuevo_estado=estado_obj.estado,
        fecha_estado=estado_obj.fecha_estado,
        mensaje=mensaje
    )


async def abandon_series(
    db: AsyncSession,
    usuario_id: int,
    titulo_id: int
) -> StateChangeResponse:
    """Abandona una serie (❌). Pasa de Siguiendo a SinEstado, conservando los episodios vistos."""
    titulo = await db.get(Titulo, titulo_id)
    if not titulo:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Título no encontrado.")

    if titulo.tipo != "tv":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Solo las series pueden ser abandonadas.")

    estado_obj = await get_or_create_title_state(db, usuario_id, titulo_id)

    if estado_obj.estado != "siguiendo":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Solo las series en estado 'siguiendo' pueden ser abandonadas."
        )

    # Quita el estado activo pero conserva todos los episodios vistos
    estado_obj.estado = None
    estado_obj.fecha_estado = None

    await db.commit()
    return StateChangeResponse(
        titulo_id=titulo_id,
        nuevo_estado=None,
        fecha_estado=None,
        mensaje="Serie abandonada. El progreso de episodios vistos se conserva."
    )


async def toggle_episode_watched(
    db: AsyncSession,
    usuario_id: int,
    episodio_id: int
) -> EpisodeWatchResponse:
    """Marca o desmarca un episodio individual como visto y recalcula automáticamente el estado de la serie."""
    # Obtener episodio y su temporada/serie
    ep_query = (
        select(Episodio, Temporada.titulo_id)
        .join(Temporada, Episodio.temporada_id == Temporada.id)
        .where(Episodio.id == episodio_id)
    )
    res = await db.execute(ep_query)
    row = res.first()
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Episodio no encontrado.")

    episodio, titulo_id = row[0], row[1]

    today = date.today()
    is_future = episodio.fecha_estreno is not None and episodio.fecha_estreno > today

    # Verificar si ya está visto
    visto_query = select(EpisodioVisto).where(
        EpisodioVisto.usuario_id == usuario_id,
        EpisodioVisto.episodio_id == episodio_id
    )
    visto_res = await db.execute(visto_query)
    visto_obj = visto_res.scalar_one_or_none()

    if visto_obj:
        # Desmarcar episodio (siempre permitido, incluso para episodios futuros marcados previamente)
        await db.delete(visto_obj)
        visto = False
        fecha_visto = None
    else:
        # Regla: Bloquear marcado de episodios futuros
        if is_future:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No se puede marcar como visto un episodio con fecha de estreno futura."
            )
        # Marcar episodio
        now_ts = _now()
        visto_obj = EpisodioVisto(
            usuario_id=usuario_id,
            episodio_id=episodio_id,
            fecha_visto=now_ts
        )
        db.add(visto_obj)
        visto = True
        fecha_visto = now_ts

    await db.flush()

    # Recalcular progreso de la serie (solo episodios emitidos / disponibles)
    total_episodes_query = (
        select(func.count(Episodio.id))
        .join(Temporada, Episodio.temporada_id == Temporada.id)
        .where(
            Temporada.titulo_id == titulo_id,
            or_(Episodio.fecha_estreno.is_(None), Episodio.fecha_estreno <= today)
        )
    )
    total_res = await db.execute(total_episodes_query)
    total_episodios = total_res.scalar() or 0

    watched_query = (
        select(func.count(EpisodioVisto.id))
        .join(Episodio, EpisodioVisto.episodio_id == Episodio.id)
        .join(Temporada, Episodio.temporada_id == Temporada.id)
        .where(
            Temporada.titulo_id == titulo_id,
            EpisodioVisto.usuario_id == usuario_id,
            or_(Episodio.fecha_estreno.is_(None), Episodio.fecha_estreno <= today)
        )
    )
    watched_res = await db.execute(watched_query)
    episodios_vistos = watched_res.scalar() or 0

    # Actualizar estado de la serie
    estado_obj = await get_or_create_title_state(db, usuario_id, titulo_id)

    if total_episodios > 0 and episodios_vistos == total_episodios:
        # Completó todos los episodios emitidos a la fecha
        estado_obj.estado = "vista"
        estado_obj.fecha_estado = _now()
    elif episodios_vistos > 0:
        # Tiene episodios vistos pero no todos los emitidos
        if estado_obj.estado in (None, "watchlist", "vista"):
            estado_obj.estado = "siguiendo"
            estado_obj.fecha_estado = _now()
        # Si ya estaba en 'siguiendo', permanece en 'siguiendo'
    else:
        # 0 episodios vistos
        # Caso borde: si estaba en 'siguiendo' y desmarcó el único, cae a SinEstado
        if estado_obj.estado == "siguiendo":
            estado_obj.estado = None
            estado_obj.fecha_estado = None

    await db.commit()

    porcentaje = round((episodios_vistos / total_episodios * 100), 1) if total_episodios > 0 else 0.0

    return EpisodeWatchResponse(
        episodio_id=episodio_id,
        titulo_id=titulo_id,
        visto=visto,
        fecha_visto=fecha_visto,
        nuevo_estado_serie=estado_obj.estado,
        episodios_vistos_serie=episodios_vistos,
        total_episodios_serie=total_episodios,
        porcentaje_progreso=porcentaje
    )


async def get_title_user_state(
    db: AsyncSession,
    usuario_id: int,
    titulo_id: int
) -> TitleUserStateResponse:
    """Retorna el estado actual del usuario sobre un título (favorito, estado, progreso de episodios)."""
    titulo = await db.get(Titulo, titulo_id)
    if not titulo:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Título no encontrado.")

    estado_obj = await get_or_create_title_state(db, usuario_id, titulo_id)

    total_episodios = 0
    episodios_vistos = 0

    if titulo.tipo == "tv":
        today = date.today()
        total_query = (
            select(func.count(Episodio.id))
            .join(Temporada, Episodio.temporada_id == Temporada.id)
            .where(
                Temporada.titulo_id == titulo_id,
                or_(Episodio.fecha_estreno.is_(None), Episodio.fecha_estreno <= today)
            )
        )
        tot_res = await db.execute(total_query)
        total_episodios = tot_res.scalar() or 0

        watched_query = (
            select(func.count(EpisodioVisto.id))
            .join(Episodio, EpisodioVisto.episodio_id == Episodio.id)
            .join(Temporada, Episodio.temporada_id == Temporada.id)
            .where(
                Temporada.titulo_id == titulo_id,
                EpisodioVisto.usuario_id == usuario_id,
                or_(Episodio.fecha_estreno.is_(None), Episodio.fecha_estreno <= today)
            )
        )
        w_res = await db.execute(watched_query)
        episodios_vistos = w_res.scalar() or 0

    porcentaje = round((episodios_vistos / total_episodios * 100), 1) if total_episodios > 0 else 0.0

    return TitleUserStateResponse(
        titulo_id=titulo_id,
        tipo=titulo.tipo,
        favorito=estado_obj.favorito,
        fecha_favorito=estado_obj.fecha_favorito,
        estado=estado_obj.estado,
        fecha_estado=estado_obj.fecha_estado,
        total_episodios=total_episodios,
        episodios_vistos=episodios_vistos,
        porcentaje_progreso=porcentaje
    )


async def toggle_episode_by_number(
    db: AsyncSession,
    usuario_id: int,
    titulo_id: int,
    season_number: int,
    episode_number: int
) -> EpisodeWatchResponse:
    """Busca el episodio por número de temporada y episodio del título, y alterna su estado visto."""
    ep_query = (
        select(Episodio.id)
        .join(Temporada, Episodio.temporada_id == Temporada.id)
        .where(
            Temporada.titulo_id == titulo_id,
            Temporada.numero == season_number,
            Episodio.numero == episode_number
        )
    )
    res = await db.execute(ep_query)
    episodio_id = res.scalar_one_or_none()
    if not episodio_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No se encontró el episodio S{season_number:02d}E{episode_number:02d} para el título {titulo_id}."
        )

    return await toggle_episode_watched(db, usuario_id=usuario_id, episodio_id=episodio_id)


async def toggle_season_watched(
    db: AsyncSession,
    usuario_id: int,
    temporada_id: int
) -> SeasonWatchResponse:
    """
    Marca o desmarca una temporada entera como vista:
    - Si todos los episodios emitidos de la temporada ya están vistos: los desmarca todos (temporada pasa a no vista).
    - Si falta al menos un episodio por ver: marca todos los episodios emitidos de la temporada como vistos.
    Recalcula automáticamente el estado de la serie (siguiendo, vista, etc.).
    """
    from app.schemas.state import SeasonWatchResponse

    temp_res = await db.execute(
        select(Temporada).where(Temporada.id == temporada_id)
    )
    temporada = temp_res.scalar_one_or_none()
    if not temporada:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Temporada no encontrada.")

    titulo_id = temporada.titulo_id

    # Obtener episodios de la temporada (excluyendo episodios futuros no emitidos)
    ep_query = (
        select(Episodio.id)
        .where(
            Episodio.temporada_id == temporada_id,
            (Episodio.fecha_estreno.is_(None) | (Episodio.fecha_estreno <= date.today()))
        )
    )
    ep_res = await db.execute(ep_query)
    season_ep_ids = [row[0] for row in ep_res.all()]

    if not season_ep_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La temporada no contiene episodios emitidos disponibles para marcar."
        )

    # Ver cuáles de estos ya están vistos
    vistos_query = select(EpisodioVisto.episodio_id).where(
        EpisodioVisto.usuario_id == usuario_id,
        EpisodioVisto.episodio_id.in_(season_ep_ids)
    )
    vistos_res = await db.execute(vistos_query)
    already_watched = {row[0] for row in vistos_res.all()}

    all_watched = len(already_watched) == len(season_ep_ids)

    if all_watched:
        # Desmarcar todos los episodios de esta temporada
        await db.execute(
            delete(EpisodioVisto).where(
                EpisodioVisto.usuario_id == usuario_id,
                EpisodioVisto.episodio_id.in_(season_ep_ids)
            )
        )
        season_is_watched = False
        episodios_afectados = len(season_ep_ids)
    else:
        # Marcar los faltantes como vistos
        missing_ids = [eid for eid in season_ep_ids if eid not in already_watched]
        now_ts = _now()
        new_vistos = [
            EpisodioVisto(usuario_id=usuario_id, episodio_id=eid, fecha_visto=now_ts)
            for eid in missing_ids
        ]
        db.add_all(new_vistos)
        season_is_watched = True
        episodios_afectados = len(missing_ids)

    await db.flush()

    # Recalcular el progreso general de la serie (solo episodios emitidos / disponibles)
    today = date.today()
    total_query = (
        select(func.count(Episodio.id))
        .join(Temporada, Episodio.temporada_id == Temporada.id)
        .where(
            Temporada.titulo_id == titulo_id,
            or_(Episodio.fecha_estreno.is_(None), Episodio.fecha_estreno <= today)
        )
    )
    tot_res = await db.execute(total_query)
    total_episodios = tot_res.scalar() or 0

    watched_query = (
        select(func.count(EpisodioVisto.id))
        .join(Episodio, EpisodioVisto.episodio_id == Episodio.id)
        .join(Temporada, Episodio.temporada_id == Temporada.id)
        .where(
            Temporada.titulo_id == titulo_id,
            EpisodioVisto.usuario_id == usuario_id,
            or_(Episodio.fecha_estreno.is_(None), Episodio.fecha_estreno <= today)
        )
    )
    watched_res = await db.execute(watched_query)
    episodios_vistos = watched_res.scalar() or 0

    estado_obj = await get_or_create_title_state(db, usuario_id, titulo_id)

    if total_episodios > 0 and episodios_vistos == total_episodios:
        estado_obj.estado = "vista"
        estado_obj.fecha_estado = _now()
    elif episodios_vistos > 0:
        if estado_obj.estado in (None, "watchlist", "vista"):
            estado_obj.estado = "siguiendo"
            estado_obj.fecha_estado = _now()
    else:
        if estado_obj.estado == "siguiendo":
            estado_obj.estado = None
            estado_obj.fecha_estado = None

    await db.commit()

    porcentaje = round((episodios_vistos / total_episodios * 100), 1) if total_episodios > 0 else 0.0

    return SeasonWatchResponse(
        temporada_id=temporada_id,
        titulo_id=titulo_id,
        numero_temporada=temporada.numero,
        temporada_vista=season_is_watched,
        episodios_afectados=episodios_afectados,
        nuevo_estado_serie=estado_obj.estado,
        episodios_vistos_serie=episodios_vistos,
        total_episodios_serie=total_episodios,
        porcentaje_progreso=porcentaje
    )


async def toggle_season_by_number(
    db: AsyncSession,
    usuario_id: int,
    titulo_id: int,
    season_number: int
) -> SeasonWatchResponse:
    """Busca la temporada por número y título, y alterna su marcado completo como visto."""
    res = await db.execute(
        select(Temporada.id).where(
            Temporada.titulo_id == titulo_id,
            Temporada.numero == season_number
        )
    )
    temporada_id = res.scalar_one_or_none()
    if not temporada_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No se encontró la temporada {season_number} para el título {titulo_id}."
        )

    return await toggle_season_watched(db, usuario_id=usuario_id, temporada_id=temporada_id)
