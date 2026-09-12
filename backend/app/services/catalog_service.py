import random
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional, Set
from sqlalchemy import and_, delete, desc, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
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
    titulos_elenco,
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
    UnreviewedWatchedResponse,
    UserLibraryResponse,
    UserReviewItemResponse,
    UserReviewsListResponse,
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
        fecha_estreno=titulo.fecha_estreno,
        fecha_fin=titulo.fecha_fin,
        anio_estreno=titulo.anio_estreno,
        anio_fin=titulo.anio_fin,
        duracion=titulo.duracion,
        popularidad=titulo.popularidad,
        popularidad_percentil=titulo.popularidad_percentil or 0.0,
        vote_average_tmdb=titulo.vote_average_tmdb,
        vote_count_tmdb=titulo.vote_count_tmdb,
        rating_unificado=titulo.rating_unificado,
        generos=genres,
        total_seasons=total_seasons,
        user_favorito=user_favorito,
        user_estado=user_estado,
        pais=titulo.pais,
        idioma_original=titulo.idioma_original,
    )


async def _get_watched_title_ids(db: AsyncSession, usuario_id: Optional[int]) -> Set[int]:
    if not usuario_id:
        return set()
    res = await db.execute(
        select(EstadoUsuarioTitulo.titulo_id).where(
            EstadoUsuarioTitulo.usuario_id == usuario_id,
            EstadoUsuarioTitulo.estado == "vista"
        )
    )
    return set(res.scalars().all())


async def get_titles(
    db: AsyncSession,
    tipo: Optional[str] = None,
    genero_id: Optional[int] = None,
    genero: Optional[str] = None,
    actor_id: Optional[int] = None,
    actor: Optional[str] = None,
    section: Optional[str] = None,
    q: Optional[str] = None,
    sort_by: str = "popularity",  # 'popularity', 'rating', 'release_date' (o 'newest'), 'title'
    order: str = "desc",          # 'desc' (default) o 'asc'
    page: int = 1,
    page_size: int = 20,
    usuario_id: Optional[int] = None,
    exclude_watched: bool = False
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
    elif genero:
        query = (
            query.join(titulos_generos, titulos_generos.c.titulo_id == Titulo.id)
            .join(Genero, Genero.id == titulos_generos.c.genero_id)
            .where(Genero.nombre.ilike(f"%{genero.strip()}%"))
        )

    if actor_id:
        actor_title_subq = (
            select(titulos_elenco.c.titulo_id)
            .where(titulos_elenco.c.actor_id == actor_id)
            .scalar_subquery()
        )
        query = query.where(Titulo.id.in_(actor_title_subq))
    elif actor:
        actor_name_subq = (
            select(titulos_elenco.c.titulo_id)
            .join(Actor, Actor.id == titulos_elenco.c.actor_id)
            .where(Actor.nombre.ilike(f"%{actor.strip()}%"))
            .scalar_subquery()
        )
        query = query.where(Titulo.id.in_(actor_name_subq))

    if q:
        search_pattern = f"%{q.strip()}%"
        actor_subq = (
            select(titulos_elenco.c.titulo_id)
            .join(Actor, Actor.id == titulos_elenco.c.actor_id)
            .where(Actor.nombre.ilike(search_pattern))
            .scalar_subquery()
        )
        query = query.where(
            (Titulo.nombre.ilike(search_pattern)) |
            (Titulo.director.ilike(search_pattern)) |
            (Titulo.guionista.ilike(search_pattern)) |
            (Titulo.id.in_(actor_subq))
        )

    if exclude_watched and usuario_id:
        watched_subq = (
            select(EstadoUsuarioTitulo.titulo_id)
            .where(
                EstadoUsuarioTitulo.usuario_id == usuario_id,
                EstadoUsuarioTitulo.estado == "vista"
            )
            .scalar_subquery()
        )
        query = query.where(Titulo.id.not_in(watched_subq))

    # 1. Filtro por sección curada (collection / section)
    # Soporta tanto el nuevo parámetro 'section' como valores legacy pasados en 'sort_by'
    active_section = section
    effective_sort = sort_by
    if not active_section and sort_by in ("classics", "top_rated", "others", "new_releases", "trending"):
        active_section = sort_by
        if sort_by == "top_rated":
            effective_sort = "rating"
        elif sort_by == "new_releases":
            effective_sort = "newest"
        else:
            effective_sort = "popularity"

    today = date.today()
    if active_section == "new_releases":
        nr_cutoff = today - timedelta(days=settings.HOME_NEW_RELEASES_DAYS)
        query = query.where(
            Titulo.fecha_estreno.isnot(None),
            Titulo.fecha_estreno >= nr_cutoff,
            Titulo.fecha_estreno <= today
        )
    elif active_section == "trending":
        tr_cutoff = today - timedelta(days=settings.HOME_TRENDING_DAYS)
        latest_ep_subq = (
            select(func.max(Episodio.fecha_estreno))
            .join(Temporada, Episodio.temporada_id == Temporada.id)
            .where(Temporada.titulo_id == Titulo.id)
            .scalar_subquery()
        )
        tv_date_expr = func.coalesce(latest_ep_subq, Titulo.fecha_estreno)
        trending_base_cond = or_(
            and_(Titulo.tipo == "movie", Titulo.fecha_estreno >= tr_cutoff, Titulo.fecha_estreno <= today),
            and_(Titulo.tipo == "tv", tv_date_expr >= tr_cutoff, tv_date_expr <= today)
        )
        top10_subq = (
            select(Titulo.id)
            .where(trending_base_cond)
            .order_by(desc(Titulo.popularidad), desc(Titulo.id))
            .limit(settings.HOME_SECTION_SAMPLE_SIZE)
            .scalar_subquery()
        )
        query = query.where(
            trending_base_cond,
            or_(
                Titulo.popularidad_percentil >= settings.HOME_TRENDING_MIN_POPULARITY_PERCENTILE,
                Titulo.id.in_(top10_subq)
            )
        )
    elif active_section == "classics":
        current_year = today.year
        cutoff_date = date(current_year - settings.HOME_CLASSICS_MIN_YEARS, 12, 31)
        query = query.where(
            Titulo.tipo == "movie",
            Titulo.fecha_estreno.isnot(None),
            Titulo.fecha_estreno <= cutoff_date,
            Titulo.rating_unificado >= settings.HOME_CLASSICS_MIN_RATING,
            Titulo.vote_count_tmdb >= settings.HOME_CLASSICS_MIN_VOTES
        )
    elif active_section == "top_rated":
        query = query.where(Titulo.vote_count_tmdb >= settings.HOME_TOP_RATED_MIN_VOTES)
    elif active_section == "others":
        genre_count_subq = (
            select(titulos_generos.c.genero_id)
            .join(Titulo, Titulo.id == titulos_generos.c.titulo_id)
        )
        if tipo and tipo in ("movie", "tv"):
            genre_count_subq = genre_count_subq.where(Titulo.tipo == tipo)
        genre_count_subq = (
            genre_count_subq
            .group_by(titulos_generos.c.genero_id)
            .having(func.count(titulos_generos.c.titulo_id) < settings.HOME_GENRE_MIN_TITLES_FOR_CAROUSEL)
            .scalar_subquery()
        )
        titles_in_minor = (
            select(titulos_generos.c.titulo_id)
            .where(titulos_generos.c.genero_id.in_(genre_count_subq))
            .scalar_subquery()
        )
        query = query.where(Titulo.id.in_(titles_in_minor))

    # 2. Ordenamiento puro (criterio + dirección)
    is_asc = order.lower() == "asc"
    norm_sort = effective_sort.lower()
    if norm_sort == "newest":
        norm_sort = "release_date"
        is_asc = False
    elif norm_sort == "oldest":
        norm_sort = "release_date"
        is_asc = True

    if norm_sort in ("rating", "top_rated"):
        if is_asc:
            query = query.order_by(Titulo.rating_unificado.asc(), Titulo.vote_count_tmdb.asc())
        else:
            query = query.order_by(desc(Titulo.rating_unificado), desc(Titulo.vote_count_tmdb))
    elif norm_sort in ("release_date", "date"):
        if is_asc:
            query = query.order_by(Titulo.fecha_estreno.asc(), Titulo.popularidad.asc())
        else:
            query = query.order_by(desc(Titulo.fecha_estreno), desc(Titulo.popularidad))
    elif norm_sort == "title":
        if is_asc:
            query = query.order_by(Titulo.nombre.asc())
        else:
            query = query.order_by(Titulo.nombre.desc())
    else:  # 'popularity'
        if is_asc:
            query = query.order_by(Titulo.popularidad.asc(), Titulo.id.asc())
        else:
            query = query.order_by(desc(Titulo.popularidad), desc(Titulo.id))

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
    """
    Devuelve las secciones curadas para la Home:
    - New Releases (últimos N días, configurable)
    - Trending (últimos N días por popularidad, extensible con última temporada en series)
    - Classics (películas con > N años y alto rating, pool aleatorio)
    - Top Rated (pool aleatorio de las mejores calificadas)
    - By Genre (carrusel propio para géneros con >= min_titles)
    - Others (pool aleatorio de géneros minoritarios con < min_titles)
    """
    today = date.today()
    sample_size = settings.HOME_SECTION_SAMPLE_SIZE

    def _apply_base_filters(query):
        return query

    # -------------------------------------------------------------------------
    # 1. New Releases (últimos HOME_NEW_RELEASES_DAYS días, ordenados por fecha desc)
    # Series entran si su propio estreno fue en esa ventana.
    # -------------------------------------------------------------------------
    nr_cutoff = today - timedelta(days=settings.HOME_NEW_RELEASES_DAYS)
    nr_query = (
        select(Titulo)
        .options(selectinload(Titulo.generos), selectinload(Titulo.temporadas))
        .where(
            Titulo.fecha_estreno.isnot(None),
            Titulo.fecha_estreno >= nr_cutoff,
            Titulo.fecha_estreno <= today
        )
    )
    if tipo in ("movie", "tv"):
        nr_query = nr_query.where(Titulo.tipo == tipo)
    nr_query = _apply_base_filters(nr_query)
    nr_query = nr_query.order_by(desc(Titulo.fecha_estreno), desc(Titulo.popularidad)).limit(sample_size)
    new_releases_titulos = (await db.execute(nr_query)).scalars().all()

    # -------------------------------------------------------------------------
    # 2. Trending (últimos HOME_TRENDING_DAYS días, ordenados por popularidad desc)
    # Series entran si su fecha de estreno o la de su última temporada entra en la ventana.
    # -------------------------------------------------------------------------
    tr_cutoff = today - timedelta(days=settings.HOME_TRENDING_DAYS)
    latest_ep_subq = (
        select(func.max(Episodio.fecha_estreno))
        .join(Temporada, Episodio.temporada_id == Temporada.id)
        .where(Temporada.titulo_id == Titulo.id)
        .scalar_subquery()
    )
    tv_date_expr = func.coalesce(latest_ep_subq, Titulo.fecha_estreno)

    tr_query = (
        select(Titulo)
        .options(selectinload(Titulo.generos), selectinload(Titulo.temporadas))
    )
    if tipo == "movie":
        tr_query = tr_query.where(
            Titulo.tipo == "movie",
            Titulo.fecha_estreno.isnot(None),
            Titulo.fecha_estreno >= tr_cutoff,
            Titulo.fecha_estreno <= today
        )
    elif tipo == "tv":
        tr_query = tr_query.where(
            Titulo.tipo == "tv",
            tv_date_expr.isnot(None),
            tv_date_expr >= tr_cutoff,
            tv_date_expr <= today
        )
    else:
        tr_query = tr_query.where(
            or_(
                (Titulo.tipo == "movie") & Titulo.fecha_estreno.isnot(None) & (Titulo.fecha_estreno >= tr_cutoff) & (Titulo.fecha_estreno <= today),
                (Titulo.tipo == "tv") & tv_date_expr.isnot(None) & (tv_date_expr >= tr_cutoff) & (tv_date_expr <= today)
            )
        )
    tr_query = _apply_base_filters(tr_query)
    tr_query = tr_query.order_by(desc(Titulo.popularidad), desc(Titulo.id)).limit(sample_size)
    trending_titulos = (await db.execute(tr_query)).scalars().all()

    # -------------------------------------------------------------------------
    # 3. Classics (solo películas con > HOME_CLASSICS_MIN_YEARS, rating >= 7.5, votos >= 500)
    # Pool de 50 más populares -> muestra aleatoria de sample_size (10)
    # -------------------------------------------------------------------------
    classics_titulos = []
    if tipo != "tv":
        classics_cutoff_year = today.year - settings.HOME_CLASSICS_MIN_YEARS
        classics_cutoff_date = date(classics_cutoff_year, 12, 31)
        cl_query = (
            select(Titulo)
            .options(selectinload(Titulo.generos), selectinload(Titulo.temporadas))
            .where(
                Titulo.tipo == "movie",
                Titulo.fecha_estreno.isnot(None),
                Titulo.fecha_estreno <= classics_cutoff_date,
                Titulo.rating_unificado >= settings.HOME_CLASSICS_MIN_RATING,
                Titulo.vote_count_tmdb >= settings.HOME_CLASSICS_MIN_VOTES
            )
        )
        cl_query = _apply_base_filters(cl_query)
        cl_query = cl_query.order_by(desc(Titulo.popularidad), desc(Titulo.id)).limit(settings.HOME_CLASSICS_POOL_SIZE)
        cl_pool = (await db.execute(cl_query)).scalars().all()
        if len(cl_pool) > sample_size:
            classics_titulos = random.sample(cl_pool, sample_size)
        else:
            classics_titulos = list(cl_pool)

    # -------------------------------------------------------------------------
    # 4. Top Rated (pool de 100 mejores calificadas con >= 100 votos -> muestra aleatoria de 10)
    # -------------------------------------------------------------------------
    tr_pool_query = (
        select(Titulo)
        .options(selectinload(Titulo.generos), selectinload(Titulo.temporadas))
        .where(
            Titulo.vote_count_tmdb >= settings.HOME_TOP_RATED_MIN_VOTES
        )
    )
    if tipo in ("movie", "tv"):
        tr_pool_query = tr_pool_query.where(Titulo.tipo == tipo)
    tr_pool_query = _apply_base_filters(tr_pool_query)
    tr_pool_query = tr_pool_query.order_by(desc(Titulo.rating_unificado), desc(Titulo.vote_count_tmdb)).limit(settings.HOME_TOP_RATED_POOL_SIZE)
    tr_pool = (await db.execute(tr_pool_query)).scalars().all()
    if len(tr_pool) > sample_size:
        top_rated_titulos = random.sample(tr_pool, sample_size)
    else:
        top_rated_titulos = list(tr_pool)

    # -------------------------------------------------------------------------
    # 5. By Genre y Others
    # - Géneros con >= HOME_GENRE_MIN_TITLES_FOR_CAROUSEL (10): Carrusel propio (muestra de 10 de pool 100)
    # - Géneros con < 10 títulos: agrupados en 'others' (muestra de 10 de pool)
    # -------------------------------------------------------------------------
    genre_count_q = (
        select(Genero.id, Genero.nombre, func.count(titulos_generos.c.titulo_id).label("cnt"))
        .join(titulos_generos, titulos_generos.c.genero_id == Genero.id)
        .join(Titulo, Titulo.id == titulos_generos.c.titulo_id)
    )
    if tipo in ("movie", "tv"):
        genre_count_q = genre_count_q.where(Titulo.tipo == tipo)
    genre_count_q = genre_count_q.group_by(Genero.id, Genero.nombre).order_by(desc("cnt"), Genero.nombre)

    genre_rows = (await db.execute(genre_count_q)).all()

    major_genres = []
    minor_genre_ids = []
    for gid, gname, cnt in genre_rows:
        if cnt >= settings.HOME_GENRE_MIN_TITLES_FOR_CAROUSEL:
            major_genres.append((gid, gname))
        elif cnt > 0:
            minor_genre_ids.append(gid)

    by_genre_titulos = {}
    for gid, gname in major_genres:
        g_q = (
            select(Titulo)
            .options(selectinload(Titulo.generos), selectinload(Titulo.temporadas))
            .join(titulos_generos, titulos_generos.c.titulo_id == Titulo.id)
            .where(titulos_generos.c.genero_id == gid)
        )
        if tipo in ("movie", "tv"):
            g_q = g_q.where(Titulo.tipo == tipo)
        g_q = _apply_base_filters(g_q)
        g_q = g_q.order_by(desc(Titulo.popularidad), desc(Titulo.id)).limit(settings.HOME_GENRE_POOL_SIZE)
        g_pool = (await db.execute(g_q)).scalars().all()
        if len(g_pool) > sample_size:
            by_genre_titulos[gname] = random.sample(g_pool, sample_size)
        else:
            by_genre_titulos[gname] = list(g_pool)

    others_titulos = []
    if minor_genre_ids:
        oth_q = (
            select(Titulo)
            .options(selectinload(Titulo.generos), selectinload(Titulo.temporadas))
            .join(titulos_generos, titulos_generos.c.titulo_id == Titulo.id)
            .where(titulos_generos.c.genero_id.in_(minor_genre_ids))
            .distinct()
        )
        if tipo in ("movie", "tv"):
            oth_q = oth_q.where(Titulo.tipo == tipo)
        oth_q = _apply_base_filters(oth_q)
        oth_q = oth_q.order_by(desc(Titulo.popularidad), desc(Titulo.id)).limit(settings.HOME_GENRE_POOL_SIZE)
        oth_pool = (await db.execute(oth_q)).scalars().all()
        if len(oth_pool) > sample_size:
            others_titulos = random.sample(oth_pool, sample_size)
        else:
            others_titulos = list(oth_pool)

    # -------------------------------------------------------------------------
    # Estados de usuario consolidados (1 sola consulta para todos los títulos)
    # -------------------------------------------------------------------------
    all_selected = (
        trending_titulos
        + new_releases_titulos
        + classics_titulos
        + top_rated_titulos
        + others_titulos
    )
    for g_list in by_genre_titulos.values():
        all_selected.extend(g_list)

    user_states_map = {}
    if usuario_id and all_selected:
        unique_ids = list({t.id for t in all_selected})
        st_res = await db.execute(
            select(EstadoUsuarioTitulo).where(
                EstadoUsuarioTitulo.usuario_id == usuario_id,
                EstadoUsuarioTitulo.titulo_id.in_(unique_ids)
            )
        )
        user_states_map = {st.titulo_id: st for st in st_res.scalars().all()}

    return HomeSectionsResponse(
        trending=[_build_title_card(t, user_states_map.get(t.id)) for t in trending_titulos],
        new_releases=[_build_title_card(t, user_states_map.get(t.id)) for t in new_releases_titulos],
        classics=[_build_title_card(t, user_states_map.get(t.id)) for t in classics_titulos],
        top_rated=[_build_title_card(t, user_states_map.get(t.id)) for t in top_rated_titulos],
        by_genre={
            gname: [_build_title_card(t, user_states_map.get(t.id)) for t in titles]
            for gname, titles in by_genre_titulos.items()
        },
        others=[_build_title_card(t, user_states_map.get(t.id)) for t in others_titulos]
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

        today_date = date.today()
        eligible_eps_count = sum(
            1 for ep in sea.episodios
            if ep.fecha_estreno is None or ep.fecha_estreno <= today_date
        )
        total_eps = len(episodes_list)
        temp_vista = eligible_eps_count > 0 and vistos_en_temp >= eligible_eps_count
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


async def delete_user_review(
    db: AsyncSession,
    titulo_id: int,
    usuario_id: int
) -> bool:
    """Elimina la reseña propia del usuario para el título especificado y recalcula ratings."""
    res = await db.execute(
        select(Resena).where(Resena.titulo_id == titulo_id, Resena.usuario_id == usuario_id)
    )
    review = res.scalar_one_or_none()
    if not review:
        return False

    await db.delete(review)
    await db.commit()

    # Recalcular el rating unificado del título
    from app.services.tmdb_sync_service import TMDBSyncService
    sync_svc = TMDBSyncService(db)
    await sync_svc.recalculate_unified_ratings(titulo_id=titulo_id)

    return True


async def get_user_reviews(
    db: AsyncSession,
    usuario_id: int,
    page: int = 1,
    page_size: int = 20
) -> UserReviewsListResponse:
    """Retorna las reseñas escritas por el usuario autenticado con datos del título."""
    count_q = select(func.count(Resena.id)).where(Resena.usuario_id == usuario_id)
    total_res = await db.execute(count_q)
    total = total_res.scalar() or 0

    q = (
        select(Resena, Titulo)
        .join(Titulo, Titulo.id == Resena.titulo_id)
        .where(Resena.usuario_id == usuario_id)
        .order_by(desc(Resena.fecha))
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    res = await db.execute(q)
    rows = res.all()

    items = [
        UserReviewItemResponse(
            id=r.id,
            titulo_id=r.titulo_id,
            titulo_nombre=t.nombre,
            titulo_tipo=t.tipo,
            titulo_portada_url=t.portada_url,
            titulo_fecha_estreno=t.fecha_estreno,
            puntaje=r.puntaje,
            texto=r.texto,
            fecha=r.fecha
        )
        for r, t in rows
    ]

    return UserReviewsListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size
    )


async def get_user_unreviewed_watched_titles(
    db: AsyncSession,
    usuario_id: int,
    limit: int = 50
) -> UnreviewedWatchedResponse:
    """Retorna títulos marcados como 'vista' por el usuario que aún no tienen reseña suya."""
    reviewed_ids_subq = select(Resena.titulo_id).where(Resena.usuario_id == usuario_id)

    q = (
        select(Titulo, EstadoUsuarioTitulo)
        .join(EstadoUsuarioTitulo, EstadoUsuarioTitulo.titulo_id == Titulo.id)
        .options(selectinload(Titulo.generos), selectinload(Titulo.temporadas))
        .where(
            EstadoUsuarioTitulo.usuario_id == usuario_id,
            EstadoUsuarioTitulo.estado == "vista",
            ~Titulo.id.in_(reviewed_ids_subq)
        )
        .order_by(desc(EstadoUsuarioTitulo.fecha_estado))
        .limit(limit)
    )
    res = await db.execute(q)
    rows = res.all()

    items = [_build_title_card(t, st) for t, st in rows]
    return UnreviewedWatchedResponse(items=items, total=len(items))


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


# -----------------------------------------------------------------------------
# ADMINISTRACIÓN: VACIADO TOTAL DEL CATÁLOGO
# -----------------------------------------------------------------------------
async def clear_entire_catalog(db: AsyncSession) -> Dict[str, int]:
    """
    Elimina todos los títulos del catálogo y sus datos dependientes en cascada:
    - Episodios vistos
    - Episodios y temporadas
    - Vinculaciones con géneros y elencos
    - Reseñas asociadas
    - Estados de usuario asociados a títulos
    - Títulos
    - Actores huérfanos
    Preserva intactos: usuarios registrados y tabla maestra de géneros.
    """
    # 1. Dependencias de episodios y temporadas
    del_vistos = await db.execute(delete(EpisodioVisto))
    del_eps = await db.execute(delete(Episodio))
    del_temps = await db.execute(delete(Temporada))

    # 2. Tablas asociativas
    del_elenco = await db.execute(delete(titulos_elenco))
    del_generos = await db.execute(delete(titulos_generos))

    # 3. Reseñas y estados de usuario sobre títulos
    del_resenas = await db.execute(delete(Resena))
    del_estados = await db.execute(delete(EstadoUsuarioTitulo))

    # 4. Títulos
    del_titulos = await db.execute(delete(Titulo))

    # 5. Actores huérfanos
    del_actores = await db.execute(delete(Actor))

    await db.commit()

    return {
        "titulos": del_titulos.rowcount if del_titulos.rowcount != -1 else 0,
        "temporadas": del_temps.rowcount if del_temps.rowcount != -1 else 0,
        "episodios": del_eps.rowcount if del_eps.rowcount != -1 else 0,
        "resenas": del_resenas.rowcount if del_resenas.rowcount != -1 else 0,
        "estados_usuario": del_estados.rowcount if del_estados.rowcount != -1 else 0,
        "actores": del_actores.rowcount if del_actores.rowcount != -1 else 0,
    }

