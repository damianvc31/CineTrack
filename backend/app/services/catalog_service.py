from datetime import date, datetime
from typing import Any, Dict, List, Optional
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import (
    Actor,
    Episodio,
    EpisodioVisto,
    EstadoUsuarioTitulo,
    Genero,
    Resena,
    Temporada,
    Titulo,
    TituloElenco,
    titulos_generos,
)
from app.schemas.catalog import (
    CastMemberResponse,
    EpisodeResponse,
    GenreResponse,
    HomeSectionsResponse,
    ReviewCreate,
    ReviewResponse,
    SeasonResponse,
    TitleCardResponse,
    TitleDetailResponse,
    TitleListResponse,
    TopTitleStat,
    UserLibraryResponse,
    UserStatsResponse,
)


def _build_title_card(
    titulo: Titulo,
    user_state: Optional[EstadoUsuarioTitulo] = None
) -> TitleCardResponse:
    total_seasons = len(titulo.temporadas) if titulo.tipo == "tv" and hasattr(titulo, "temporadas") and titulo.temporadas else None
    genres = [GenreResponse(id=g.id, nombre=g.nombre) for g in titulo.generos] if hasattr(titulo, "generos") and titulo.generos else []

    user_favorito = False
    user_estado = None
    if user_state:
        user_favorito = user_state.favorito
        user_estado = user_state.estado

    return TitleCardResponse(
        id=titulo.id,
        tmdb_id=titulo.tmdb_id,
        tipo=titulo.tipo,
        nombre=titulo.nombre,
        sinopsis=titulo.sinopsis,
        portada_url=titulo.portada_url,
        anio_estreno=titulo.anio_estreno,
        anio_fin=titulo.anio_fin,
        duracion=titulo.duracion,
        popularidad=titulo.popularidad,
        vote_average_tmdb=titulo.vote_average_tmdb,
        vote_count_tmdb=titulo.vote_count_tmdb,
        rating_unificado=titulo.rating_unificado,
        generos=genres,
        total_seasons=total_seasons,
        user_favorito=user_favorito,
        user_estado=user_estado,
    )


async def get_titles(
    db: AsyncSession,
    tipo: Optional[str] = None,
    genero_id: Optional[int] = None,
    q: Optional[str] = None,
    sort_by: str = "popularity",  # 'popularity', 'rating', 'newest', 'classics'
    page: int = 1,
    page_size: int = 20,
    usuario_id: Optional[int] = None
) -> TitleListResponse:
    query = (
        select(Titulo)
        .options(selectinload(Titulo.generos), selectinload(Titulo.temporadas))
    )

    if tipo and tipo in ("movie", "tv"):
        query = query.where(Titulo.tipo == tipo)

    if genero_id:
        query = query.join(titulos_generos, titulos_generos.c.titulo_id == Titulo.id).where(
            titulos_generos.c.genero_id == genero_id
        )

    if q:
        search_pattern = f"%{q.strip()}%"
        query = query.where(
            (Titulo.nombre.ilike(search_pattern)) |
            (Titulo.director.ilike(search_pattern)) |
            (Titulo.guionista.ilike(search_pattern))
        )

    # Ordenamiento
    if sort_by == "popularity":
        query = query.order_by(desc(Titulo.popularidad), desc(Titulo.id))
    elif sort_by == "rating":
        query = query.order_by(desc(Titulo.rating_unificado), desc(Titulo.vote_count_tmdb))
    elif sort_by == "newest":
        query = query.order_by(desc(Titulo.anio_estreno), desc(Titulo.popularidad))
    elif sort_by == "classics":
        query = query.where(Titulo.vote_average_tmdb >= 8.0, Titulo.anio_estreno < 2010).order_by(
            desc(Titulo.rating_unificado)
        )
    else:
        query = query.order_by(desc(Titulo.popularidad))

    # Paginación
    count_query = select(func.count()).select_from(query.subquery())
    total_res = await db.execute(count_query)
    total = total_res.scalar() or 0

    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size)
    res = await db.execute(query)
    titulos = res.scalars().all()

    # Cargar estados de usuario si está autenticado
    user_states_map = {}
    if usuario_id and titulos:
        title_ids = [t.id for t in titulos]
        st_res = await db.execute(
            select(EstadoUsuarioTitulo).where(
                EstadoUsuarioTitulo.usuario_id == usuario_id,
                EstadoUsuarioTitulo.titulo_id.in_(title_ids)
            )
        )
        for st in st_res.scalars().all():
            user_states_map[st.titulo_id] = st

    items = [_build_title_card(t, user_states_map.get(t.id)) for t in titulos]
    return TitleListResponse(items=items, total=total, page=page, page_size=page_size)


async def get_home_sections(
    db: AsyncSession,
    tipo: Optional[str] = None,
    usuario_id: Optional[int] = None
) -> HomeSectionsResponse:
    """Devuelve las secciones curadas para la Home (Trending, New Releases, Classics y Géneros populares)."""
    # 1. Trending (top popularidad)
    trending_res = await get_titles(db, tipo=tipo, sort_by="popularity", page=1, page_size=10, usuario_id=usuario_id)
    # 2. New Releases (últimos años)
    new_res = await get_titles(db, tipo=tipo, sort_by="newest", page=1, page_size=10, usuario_id=usuario_id)
    # 3. Classics
    classics_res = await get_titles(db, tipo=tipo, sort_by="classics", page=1, page_size=10, usuario_id=usuario_id)

    # 4. By Genre (obtener los 4 géneros con más títulos)
    genre_counts_q = (
        select(Genero.id, Genero.nombre, func.count(titulos_generos.c.titulo_id).label("cnt"))
        .join(titulos_generos, titulos_generos.c.genero_id == Genero.id)
        .group_by(Genero.id, Genero.nombre)
        .order_by(desc("cnt"))
        .limit(4)
    )
    g_res = await db.execute(genre_counts_q)
    top_genres = g_res.all()

    by_genre = {}
    for gid, gname, _ in top_genres:
        g_titles = await get_titles(db, tipo=tipo, genero_id=gid, sort_by="popularity", page=1, page_size=10, usuario_id=usuario_id)
        if g_titles.items:
            by_genre[gname] = g_titles.items

    return HomeSectionsResponse(
        trending=trending_res.items,
        new_releases=new_res.items,
        classics=classics_res.items,
        by_genre=by_genre
    )


async def get_title_detail(
    db: AsyncSession,
    titulo_id: int,
    usuario_id: Optional[int] = None
) -> Optional[TitleDetailResponse]:
    query = (
        select(Titulo)
        .options(
            selectinload(Titulo.generos),
            selectinload(Titulo.temporadas).selectinload(Temporada.episodios),
            selectinload(Titulo.elenco).selectinload(TituloElenco.actor),
        )
        .where(Titulo.id == titulo_id)
    )
    res = await db.execute(query)
    titulo = res.scalar_one_or_none()
    if not titulo:
        return None

    # Estado del usuario
    user_state = None
    watched_ep_ids = set()
    if usuario_id:
        st_res = await db.execute(
            select(EstadoUsuarioTitulo).where(
                EstadoUsuarioTitulo.usuario_id == usuario_id,
                EstadoUsuarioTitulo.titulo_id == titulo_id
            )
        )
        user_state = st_res.scalar_one_or_none()

        w_res = await db.execute(
            select(EpisodioVisto.episodio_id)
            .join(Episodio, EpisodioVisto.episodio_id == Episodio.id)
            .join(Temporada, Episodio.temporada_id == Temporada.id)
            .where(
                Temporada.titulo_id == titulo_id,
                EpisodioVisto.usuario_id == usuario_id
            )
        )
        watched_ep_ids = set(w_res.scalars().all())

    # Formar elenco
    elenco_list = []
    for item in sorted(titulo.elenco, key=lambda x: x.orden):
        elenco_list.append(
            CastMemberResponse(
                actor_id=item.actor_id,
                tmdb_id=item.actor.tmdb_id if item.actor else None,
                nombre=item.actor.nombre if item.actor else "Desconocido",
                personaje=item.personaje,
                orden=item.orden
            )
        )

    # Formar temporadas y episodios
    temporadas_list = []
    for sea in sorted(titulo.temporadas, key=lambda x: x.numero):
        episodes_list = []
        vistos_en_temp = 0
        sorted_eps = sorted(sea.episodios, key=lambda x: x.numero)
        for ep in sorted_eps:
            is_visto = ep.id in watched_ep_ids
            if is_visto:
                vistos_en_temp += 1
            episodes_list.append(
                EpisodeResponse(
                    id=ep.id,
                    temporada_id=ep.temporada_id,
                    numero=ep.numero,
                    nombre=ep.nombre,
                    fecha_estreno=ep.fecha_estreno,
                    duracion=ep.duracion,
                    visto=is_visto
                )
            )

        total_eps = len(episodes_list)
        temp_vista = total_eps > 0 and vistos_en_temp == total_eps
        temporadas_list.append(
            SeasonResponse(
                id=sea.id,
                titulo_id=sea.titulo_id,
                numero=sea.numero,
                sinopsis=sea.sinopsis,
                fecha_estreno=sea.fecha_estreno,
                cantidad_episodios=total_eps,
                episodios_vistos=vistos_en_temp,
                temporada_vista=temp_vista,
                episodios=episodes_list
            )
        )

    card = _build_title_card(titulo, user_state)
    return TitleDetailResponse(
        **card.model_dump(),
        director=titulo.director,
        guionista=titulo.guionista,
        pais=titulo.pais,
        idioma_original=titulo.idioma_original,
        status_tmdb=titulo.status_tmdb,
        proximo_episodio_fecha=titulo.proximo_episodio_fecha,
        elenco=elenco_list,
        temporadas=temporadas_list
    )


# -----------------------------------------------------------------------------
# RESEÑAS
# -----------------------------------------------------------------------------
async def get_title_reviews(
    db: AsyncSession,
    titulo_id: int,
    page: int = 1,
    page_size: int = 20
) -> List[ReviewResponse]:
    q = (
        select(Resena)
        .options(selectinload(Resena.usuario))
        .where(Resena.titulo_id == titulo_id)
        .order_by(desc(Resena.fecha))
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    res = await db.execute(q)
    rows = res.scalars().all()

    return [
        ReviewResponse(
            id=r.id,
            titulo_id=r.titulo_id,
            usuario_id=r.usuario_id,
            nombre_usuario=r.usuario.nombre_usuario if r.usuario else None,
            avatar_url=r.usuario.avatar_url if r.usuario else None,
            autor_tmdb=r.autor_tmdb,
            puntaje=r.puntaje,
            texto=r.texto,
            fecha=r.fecha
        )
        for r in rows
    ]


async def create_user_review(
    db: AsyncSession,
    titulo_id: int,
    usuario_id: int,
    review_in: ReviewCreate
) -> ReviewResponse:
    # Buscar si el usuario ya tenía una reseña para este título
    res = await db.execute(
        select(Resena).where(Resena.titulo_id == titulo_id, Resena.usuario_id == usuario_id)
    )
    existing = res.scalar_one_or_none()
    if existing:
        existing.puntaje = review_in.puntaje
        existing.texto = review_in.texto
        existing.fecha = datetime.now()
        review = existing
    else:
        review = Resena(
            titulo_id=titulo_id,
            usuario_id=usuario_id,
            puntaje=review_in.puntaje,
            texto=review_in.texto,
            fecha=datetime.now()
        )
        db.add(review)

    await db.commit()
    await db.refresh(review)

    # Recalcular el rating unificado del título
    from app.services.tmdb_sync_service import TMDBSyncService
    sync_svc = TMDBSyncService(db)
    await sync_svc.recalculate_unified_ratings(titulo_id=titulo_id)

    # Recargar con usuario
    q = select(Resena).options(selectinload(Resena.usuario)).where(Resena.id == review.id)
    r_full = (await db.execute(q)).scalar_one()

    return ReviewResponse(
        id=r_full.id,
        titulo_id=r_full.titulo_id,
        usuario_id=r_full.usuario_id,
        nombre_usuario=r_full.usuario.nombre_usuario if r_full.usuario else None,
        avatar_url=r_full.usuario.avatar_url if r_full.usuario else None,
        autor_tmdb=r_full.autor_tmdb,
        puntaje=r_full.puntaje,
        texto=r_full.texto,
        fecha=r_full.fecha
    )


# -----------------------------------------------------------------------------
# BIBLIOTECA Y ESTADÍSTICAS DE USUARIO
# -----------------------------------------------------------------------------
async def get_user_library(
    db: AsyncSession,
    usuario_id: int
) -> UserLibraryResponse:
    """Devuelve las listas de títulos categorizados por estado para el usuario."""
    q = (
        select(Titulo, EstadoUsuarioTitulo)
        .join(EstadoUsuarioTitulo, EstadoUsuarioTitulo.titulo_id == Titulo.id)
        .options(selectinload(Titulo.generos), selectinload(Titulo.temporadas))
        .where(EstadoUsuarioTitulo.usuario_id == usuario_id)
    )
    res = await db.execute(q)
    rows = res.all()

    following = []
    favorites = []
    watchlist = []
    recently_watched = []

    for titulo, st in rows:
        card = _build_title_card(titulo, st)
        if st.favorito:
            favorites.append(card)
        if st.estado == "watchlist":
            watchlist.append(card)
        elif st.estado == "siguiendo":
            following.append(card)
        elif st.estado == "vista":
            recently_watched.append(card)

    return UserLibraryResponse(
        following=following,
        favorites=favorites,
        watchlist=watchlist,
        recently_watched=recently_watched
    )


async def get_user_stats(
    db: AsyncSession,
    usuario_id: int
) -> UserStatsResponse:
    """Calcula las estadísticas del perfil conforme a los wireframes."""
    # 1. Películas vistas
    q_movies = (
        select(Titulo)
        .join(EstadoUsuarioTitulo, EstadoUsuarioTitulo.titulo_id == Titulo.id)
        .options(selectinload(Titulo.generos))
        .where(
            EstadoUsuarioTitulo.usuario_id == usuario_id,
            EstadoUsuarioTitulo.estado == "vista",
            Titulo.tipo == "movie"
        )
    )
    res_m = await db.execute(q_movies)
    watched_movies = res_m.scalars().all()
    movies_count = len(watched_movies)
    movie_minutes = sum(m.duracion or 100 for m in watched_movies)

    # 2. Episodios vistos
    q_eps = (
        select(Episodio, Titulo)
        .join(EpisodioVisto, EpisodioVisto.episodio_id == Episodio.id)
        .join(Temporada, Episodio.temporada_id == Temporada.id)
        .join(Titulo, Temporada.titulo_id == Titulo.id)
        .options(selectinload(Titulo.generos))
        .where(EpisodioVisto.usuario_id == usuario_id)
    )
    res_e = await db.execute(q_eps)
    watched_ep_rows = res_e.all()
    episodes_count = len(watched_ep_rows)
    tv_minutes = sum(ep.duracion or 45 for ep, _ in watched_ep_rows)

    # Series vistas (completadas)
    q_series = (
        select(func.count(Titulo.id))
        .join(EstadoUsuarioTitulo, EstadoUsuarioTitulo.titulo_id == Titulo.id)
        .where(
            EstadoUsuarioTitulo.usuario_id == usuario_id,
            EstadoUsuarioTitulo.estado == "vista",
            Titulo.tipo == "tv"
        )
    )
    series_count = (await db.execute(q_series)).scalar() or 0

    movie_hours = round(movie_minutes / 60.0, 1)
    tv_hours = round(tv_minutes / 60.0, 1)
    total_hours = round((movie_minutes + tv_minutes) / 60.0, 1)

    # 3. Distribución de géneros vistos
    genres_dist = {}
    for m in watched_movies:
        for g in m.generos:
            genres_dist[g.nombre] = genres_dist.get(g.nombre, 0) + 1
    for _, t in watched_ep_rows:
        for g in t.generos:
            genres_dist[g.nombre] = genres_dist.get(g.nombre, 0) + 1

    # 4. Top 5 por Popularidad (de los títulos vistos)
    all_watched_title_ids = {m.id for m in watched_movies}.union({t.id for _, t in watched_ep_rows})
    top_pop = []
    top_community = []
    if all_watched_title_ids:
        q_pop = (
            select(Titulo)
            .options(selectinload(Titulo.temporadas))
            .where(Titulo.id.in_(all_watched_title_ids))
            .order_by(desc(Titulo.popularidad))
            .limit(5)
        )
        res_pop = await db.execute(q_pop)
        top_pop = [
            TopTitleStat(
                id=t.id,
                nombre=t.nombre,
                tipo=t.tipo,
                anio_estreno=t.anio_estreno,
                anio_fin=t.anio_fin,
                total_seasons=len(t.temporadas) if t.tipo == "tv" else None,
                portada_url=t.portada_url,
                metric_value=round(t.popularidad, 1)
            )
            for t in res_pop.scalars().all()
        ]

        q_comm = (
            select(Titulo)
            .options(selectinload(Titulo.temporadas))
            .where(Titulo.id.in_(all_watched_title_ids))
            .order_by(desc(Titulo.rating_unificado))
            .limit(5)
        )
        res_comm = await db.execute(q_comm)
        top_community = [
            TopTitleStat(
                id=t.id,
                nombre=t.nombre,
                tipo=t.tipo,
                anio_estreno=t.anio_estreno,
                anio_fin=t.anio_fin,
                total_seasons=len(t.temporadas) if t.tipo == "tv" else None,
                portada_url=t.portada_url,
                metric_value=round(t.rating_unificado, 1)
            )
            for t in res_comm.scalars().all()
        ]

    # 5. Top 5 por My Rating (reseñas con puntaje del propio usuario)
    q_user_rate = (
        select(Titulo, Resena.puntaje)
        .join(Resena, Resena.titulo_id == Titulo.id)
        .options(selectinload(Titulo.temporadas))
        .where(Resena.usuario_id == usuario_id, Resena.puntaje.isnot(None))
        .order_by(desc(Resena.puntaje))
        .limit(5)
    )
    res_ur = await db.execute(q_user_rate)
    top_user_rate = [
        TopTitleStat(
            id=t.id,
            nombre=t.nombre,
            tipo=t.tipo,
            anio_estreno=t.anio_estreno,
            anio_fin=t.anio_fin,
            total_seasons=len(t.temporadas) if t.tipo == "tv" else None,
            portada_url=t.portada_url,
            metric_value=float(score)
        )
        for t, score in res_ur.all()
    ]

    return UserStatsResponse(
        total_hours=total_hours,
        movie_hours=movie_hours,
        tv_hours=tv_hours,
        movies_watched_count=movies_count,
        series_watched_count=series_count,
        episodes_watched_count=episodes_count,
        top_by_popularity=top_pop,
        top_by_community_rating=top_community,
        top_by_user_rating=top_user_rate,
        genres_distribution=genres_dist
    )
