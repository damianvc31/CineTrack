import random
import re
from datetime import date, datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Set
from sqlalchemy import and_, delete, desc, extract, func, or_, select, text, union
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
from app.models.usuario import Usuario
from app.schemas.catalog import (
    CastMemberResponse,
    CountryItem,
    EpisodeResponse,
    GenreResponse,
    HomeSectionsResponse,
    LanguageItem,
    ReviewCreate,
    ReviewResponse,
    SeasonProgressResponse,
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

# Mapeo canónico de géneros: expande géneros individuales a las duplas que TMDB asigna a series
GENRE_EXPANSIONS: dict[str, list[str]] = {
    "action": ["Action", "Action & Adventure"],
    "adventure": ["Adventure", "Action & Adventure"],
    "science fiction": ["Science Fiction", "Sci-Fi & Fantasy"],
    "sci-fi": ["Science Fiction", "Sci-Fi & Fantasy"],
    "fantasy": ["Fantasy", "Sci-Fi & Fantasy"],
    "war": ["War", "War & Politics"],
}

EXCLUDED_GENRE_NAMES: set[str] = {"Action & Adventure", "Sci-Fi & Fantasy", "War & Politics"}


def expand_genre_names(genre_name: str) -> list[str]:
    """Expande un nombre de género a su conjunto canónico incluyendo duplas de TMDB."""
    key = genre_name.strip().lower()
    if key in GENRE_EXPANSIONS:
        return GENRE_EXPANSIONS[key]
    return [genre_name.strip()]


def _build_title_card(
    titulo: Titulo,
    user_state: Optional[EstadoUsuarioTitulo] = None,
    is_abandoned: bool = False,
    seasons_progress: Optional[List[SeasonProgressResponse]] = None,
    following_status_text: Optional[str] = None,
    user_rating: Optional[float] = None,
) -> TitleCardResponse:
    total_seasons = len(titulo.temporadas) if titulo.tipo == "tv" and hasattr(titulo, "temporadas") and titulo.temporadas else None
    genres = [GenreResponse(id=g.id, nombre=g.nombre) for g in titulo.generos] if hasattr(titulo, "generos") and titulo.generos else []

    user_favorito = False
    user_estado = None
    if user_state:
        user_favorito = user_state.favorito
        user_estado = user_state.estado

    # Si es serie de TV y tiene episodios vistos pero no está en siguiendo ni vista, su estado deducido es 'abandonada'
    if titulo.tipo == "tv" and (user_estado is None or user_estado == "abandonada") and is_abandoned:
        user_estado = "abandonada"

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
        seasons_progress=seasons_progress,
        following_status_text=following_status_text,
        user_rating=user_rating,
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
    generos: Optional[str | list[str]] = None,
    genre_op: str = "or",
    actor_id: Optional[int] = None,
    actor: Optional[str] = None,
    pais: Optional[str] = None,
    paises: Optional[str | list[str]] = None,
    idioma: Optional[str] = None,
    idiomas: Optional[str | list[str]] = None,
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
    else:
        target_genres: list[str] = []
        if generos:
            if isinstance(generos, str):
                target_genres.extend([g.strip() for g in generos.split(",") if g.strip()])
            else:
                for g in generos:
                    target_genres.extend([item.strip() for item in g.split(",") if item.strip()])
        elif genero:
            target_genres.extend([g.strip() for g in genero.split(",") if g.strip()])

        if target_genres:
            expanded_groups = [expand_genre_names(g) for g in target_genres]
            if genre_op.lower() == "and":
                for grp in expanded_groups:
                    grp_subq = (
                        select(titulos_generos.c.titulo_id)
                        .join(Genero, Genero.id == titulos_generos.c.genero_id)
                        .where(Genero.nombre.in_(grp))
                        .scalar_subquery()
                    )
                    query = query.where(Titulo.id.in_(grp_subq))
            else:
                all_allowed_genres = [item for grp in expanded_groups for item in grp]
                all_subq = (
                    select(titulos_generos.c.titulo_id)
                    .join(Genero, Genero.id == titulos_generos.c.genero_id)
                    .where(Genero.nombre.in_(all_allowed_genres))
                    .scalar_subquery()
                )
                query = query.where(Titulo.id.in_(all_subq))

    # Filtro por país(es)
    target_countries: list[str] = []
    if paises:
        if isinstance(paises, str):
            target_countries.extend([p.strip().upper() for p in paises.split(",") if p.strip()])
        else:
            for p in paises:
                target_countries.extend([item.strip().upper() for item in p.split(",") if item.strip()])
    elif pais:
        target_countries.extend([p.strip().upper() for p in pais.split(",") if p.strip()])

    if target_countries:
        query = query.where(Titulo.pais.in_(target_countries))

    # Filtro por idioma(s)
    target_languages: list[str] = []
    if idiomas:
        if isinstance(idiomas, str):
            target_languages.extend([i.strip().lower() for i in idiomas.split(",") if i.strip()])
        else:
            for i in idiomas:
                target_languages.extend([item.strip().lower() for item in i.split(",") if item.strip()])
    elif idioma:
        target_languages.extend([i.strip().lower() for i in idioma.split(",") if i.strip()])

    if target_languages:
        query = query.where(Titulo.idioma_original.in_(target_languages))

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

    # Si no se especificó orden, aplicar el default natural de cada sección
    if not effective_sort:
        if active_section == "top_rated":
            effective_sort = "rating"
        elif active_section == "new_releases":
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
        # Pool estricto de los 100 títulos con mejor calificación unificada
        top_100_subq = (
            query
            .with_only_columns(Titulo.id)
            .where(Titulo.vote_count_tmdb >= settings.HOME_TOP_RATED_MIN_VOTES)
            .order_by(desc(Titulo.rating_unificado), desc(Titulo.vote_count_tmdb))
            .limit(settings.HOME_TOP_RATED_POOL_SIZE)
            .scalar_subquery()
        )
        query = query.where(Titulo.id.in_(top_100_subq))

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

    # Cargar estados de usuario y calificaciones si está autenticado
    user_states_map = {}
    user_ratings_map = {}
    tv_abandoned_ids = set()
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

        r_res = await db.execute(
            select(Resena.titulo_id, Resena.puntaje).where(
                Resena.usuario_id == usuario_id,
                Resena.titulo_id.in_(title_ids),
                Resena.puntaje.isnot(None)
            )
        )
        for r_tid, r_score in r_res.all():
            user_ratings_map[r_tid] = r_score

        tv_ids = [t.id for t in titulos if t.tipo == "tv"]
        if tv_ids:
            w_res = await db.execute(
                select(Temporada.titulo_id)
                .join(Episodio, Episodio.temporada_id == Temporada.id)
                .join(EpisodioVisto, EpisodioVisto.episodio_id == Episodio.id)
                .where(
                    EpisodioVisto.usuario_id == usuario_id,
                    Temporada.titulo_id.in_(tv_ids)
                )
                .distinct()
            )
            watched_tv_ids = set(w_res.scalars().all())
            for tid in watched_tv_ids:
                st = user_states_map.get(tid)
                if not st or st.estado not in ("siguiendo", "vista"):
                    tv_abandoned_ids.add(tid)

    items = [
        _build_title_card(
            t,
            user_states_map.get(t.id),
            is_abandoned=(t.id in tv_abandoned_ids),
            user_rating=user_ratings_map.get(t.id)
        )
        for t in titulos
    ]
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
    # 5. By Genre (Carrusel propio para géneros canónicos con >= HOME_GENRE_MIN_TITLES_FOR_CAROUSEL)
    # Se excluyen duplas híbridas de TMDB (Action & Adventure, Sci-Fi & Fantasy, War & Politics)
    # y se expanden los géneros canónicos para abarcar películas y series conjuntamente.
    # -------------------------------------------------------------------------
    genre_count_q = (
        select(Genero.id, Genero.nombre, func.count(titulos_generos.c.titulo_id).label("cnt"))
        .join(titulos_generos, titulos_generos.c.genero_id == Genero.id)
        .join(Titulo, Titulo.id == titulos_generos.c.titulo_id)
        .where(Genero.nombre.notin_(EXCLUDED_GENRE_NAMES))
    )
    if tipo in ("movie", "tv"):
        genre_count_q = genre_count_q.where(Titulo.tipo == tipo)
    genre_count_q = genre_count_q.group_by(Genero.id, Genero.nombre).order_by(desc("cnt"), Genero.nombre)

    genre_rows = (await db.execute(genre_count_q)).all()

    major_genres = []
    for gid, gname, cnt in genre_rows:
        if cnt >= settings.HOME_GENRE_MIN_TITLES_FOR_CAROUSEL:
            major_genres.append((gid, gname))

    by_genre_titulos = {}
    for gid, gname in major_genres:
        expanded_names = expand_genre_names(gname)
        g_q = (
            select(Titulo)
            .options(selectinload(Titulo.generos), selectinload(Titulo.temporadas))
            .join(titulos_generos, titulos_generos.c.titulo_id == Titulo.id)
            .join(Genero, Genero.id == titulos_generos.c.genero_id)
            .where(Genero.nombre.in_(expanded_names))
            .distinct()
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

    # -------------------------------------------------------------------------
    # Estados de usuario consolidados (1 sola consulta para todos los títulos)
    # -------------------------------------------------------------------------
    all_selected = (
        trending_titulos
        + new_releases_titulos
        + classics_titulos
        + top_rated_titulos
    )
    for g_list in by_genre_titulos.values():
        all_selected.extend(g_list)

    user_states_map = {}
    user_ratings_map = {}
    tv_abandoned_ids = set()
    if usuario_id and all_selected:
        unique_ids = list({t.id for t in all_selected})
        st_res = await db.execute(
            select(EstadoUsuarioTitulo).where(
                EstadoUsuarioTitulo.usuario_id == usuario_id,
                EstadoUsuarioTitulo.titulo_id.in_(unique_ids)
            )
        )
        user_states_map = {st.titulo_id: st for st in st_res.scalars().all()}

        r_res = await db.execute(
            select(Resena.titulo_id, Resena.puntaje).where(
                Resena.usuario_id == usuario_id,
                Resena.titulo_id.in_(unique_ids),
                Resena.puntaje.isnot(None)
            )
        )
        for r_tid, r_score in r_res.all():
            user_ratings_map[r_tid] = r_score

        tv_ids = [t.id for t in all_selected if t.tipo == "tv"]
        if tv_ids:
            w_res = await db.execute(
                select(Temporada.titulo_id)
                .join(Episodio, Episodio.temporada_id == Temporada.id)
                .join(EpisodioVisto, EpisodioVisto.episodio_id == Episodio.id)
                .where(
                    EpisodioVisto.usuario_id == usuario_id,
                    Temporada.titulo_id.in_(tv_ids)
                )
                .distinct()
            )
            watched_tv_ids = set(w_res.scalars().all())
            for tid in watched_tv_ids:
                st = user_states_map.get(tid)
                if not st or st.estado not in ("siguiendo", "vista"):
                    tv_abandoned_ids.add(tid)

    def _build_card(t):
        return _build_title_card(
            t,
            user_states_map.get(t.id),
            is_abandoned=(t.id in tv_abandoned_ids),
            user_rating=user_ratings_map.get(t.id)
        )

    return HomeSectionsResponse(
        trending=[_build_card(t) for t in trending_titulos],
        new_releases=[_build_card(t) for t in new_releases_titulos],
        classics=[_build_card(t) for t in classics_titulos],
        top_rated=[_build_card(t) for t in top_rated_titulos],
        by_genre={
            gname: [_build_card(t) for t in titles]
            for gname, titles in by_genre_titulos.items()
        },
        others=[]
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
                foto_url=item.actor.foto_url if item.actor else None,
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

    total_vistos_serie = sum(s.episodios_vistos for s in temporadas_list) if titulo.tipo == "tv" else 0
    is_abandoned = (
        titulo.tipo == "tv"
        and (user_state is None or user_state.estado not in ("siguiendo", "vista"))
        and total_vistos_serie > 0
    )

    user_rating = None
    if usuario_id:
        r_res = await db.execute(
            select(Resena.puntaje).where(
                Resena.usuario_id == usuario_id,
                Resena.titulo_id == titulo_id,
                Resena.puntaje.isnot(None)
            )
        )
        user_rating = r_res.scalar_one_or_none()

    card = _build_title_card(titulo, user_state, is_abandoned=is_abandoned, user_rating=user_rating)
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

    series_with_watched_eps = (
        select(Temporada.titulo_id)
        .join(Episodio, Episodio.temporada_id == Temporada.id)
        .join(EpisodioVisto, EpisodioVisto.episodio_id == Episodio.id)
        .where(EpisodioVisto.usuario_id == usuario_id)
    )

    q = (
        select(Titulo, EstadoUsuarioTitulo)
        .join(EstadoUsuarioTitulo, EstadoUsuarioTitulo.titulo_id == Titulo.id)
        .options(selectinload(Titulo.generos), selectinload(Titulo.temporadas))
        .where(
            EstadoUsuarioTitulo.usuario_id == usuario_id,
            or_(
                EstadoUsuarioTitulo.estado == "vista",
                and_(
                    Titulo.tipo == "tv",
                    or_(
                        EstadoUsuarioTitulo.estado.in_(["siguiendo", "abandonada"]),
                        Titulo.id.in_(series_with_watched_eps)
                    )
                )
            ),
            ~Titulo.id.in_(reviewed_ids_subq)
        )
        .order_by(desc(EstadoUsuarioTitulo.fecha_estado))
        .limit(limit)
    )
    res = await db.execute(q)
    rows = res.all()

    items = []
    for t, st in rows:
        card = _build_title_card(t, st)
        if t.tipo == "tv" and (card.user_estado is None or card.user_estado == "abandonada"):
            card.user_estado = "abandonada"
        items.append(card)

    return UnreviewedWatchedResponse(items=items, total=len(items))


# -----------------------------------------------------------------------------
# BIBLIOTECA Y ESTADÍSTICAS DE USUARIO
# -----------------------------------------------------------------------------
async def get_user_library(
    db: AsyncSession,
    usuario_id: int
) -> UserLibraryResponse:
    """Devuelve las listas de títulos categorizados por estado para el usuario con orden cronológico descendente y progreso de siguiendo."""
    q = (
        select(Titulo, EstadoUsuarioTitulo)
        .join(EstadoUsuarioTitulo, EstadoUsuarioTitulo.titulo_id == Titulo.id)
        .options(
            selectinload(Titulo.generos),
            selectinload(Titulo.temporadas).selectinload(Temporada.episodios)
        )
        .where(EstadoUsuarioTitulo.usuario_id == usuario_id)
    )
    res = await db.execute(q)
    rows = res.all()

    # Obtener IDs de episodios vistos del usuario
    vistos_q = select(EpisodioVisto.episodio_id).where(EpisodioVisto.usuario_id == usuario_id)
    vistos_res = await db.execute(vistos_q)
    watched_ep_ids = set(vistos_res.scalars().all())

    # Obtener calificaciones del usuario si existen
    user_ratings_map = {}
    if rows:
        title_ids = [t.id for t, _ in rows]
        r_res = await db.execute(
            select(Resena.titulo_id, Resena.puntaje).where(
                Resena.usuario_id == usuario_id,
                Resena.titulo_id.in_(title_ids),
                Resena.puntaje.isnot(None)
            )
        )
        for r_tid, r_score in r_res.all():
            user_ratings_map[r_tid] = r_score

    today = date.today()

    following_items = []
    favorites_items = []
    watchlist_items = []
    recently_watched_items = []

    for titulo, st in rows:
        seasons_prog = None
        status_text = None

        if st.estado == "siguiendo" and titulo.tipo == "tv":
            seasons_prog = []
            earliest_uncompleted = None
            valid_seasons = sorted(
                [s for s in titulo.temporadas if s.numero > 0],
                key=lambda x: x.numero
            )
            for s in valid_seasons:
                aired_eps = [ep for ep in s.episodios if not ep.fecha_estreno or ep.fecha_estreno <= today]
                total_eps = len(aired_eps)
                if total_eps == 0:
                    continue
                vistos = sum(1 for ep in aired_eps if ep.id in watched_ep_ids)
                if total_eps > 0 and vistos == total_eps:
                    estado_temp = "completed"
                elif vistos > 0:
                    estado_temp = "in_progress"
                else:
                    estado_temp = "unwatched"

                seasons_prog.append(SeasonProgressResponse(
                    numero=s.numero,
                    total_episodios=total_eps,
                    episodios_vistos=vistos,
                    estado=estado_temp
                ))

                if estado_temp != "completed" and earliest_uncompleted is None:
                    earliest_uncompleted = (s.numero, estado_temp)

            if earliest_uncompleted:
                s_num, s_st = earliest_uncompleted
                if s_st == "in_progress":
                    status_text = f"S{s_num} in progress"
                else:
                    status_text = f"S{s_num} pending"
            elif seasons_prog:
                status_text = "All caught up"

        card = _build_title_card(
            titulo,
            user_state=st,
            seasons_progress=seasons_prog,
            following_status_text=status_text,
            user_rating=user_ratings_map.get(titulo.id),
        )

        min_date = datetime.min.replace(tzinfo=timezone.utc)

        if st.favorito:
            fav_date = st.fecha_favorito if st.fecha_favorito else min_date
            if fav_date.tzinfo is None:
                fav_date = fav_date.replace(tzinfo=timezone.utc)
            favorites_items.append((fav_date, card))

        if st.estado == "watchlist":
            st_date = st.fecha_estado if st.fecha_estado else min_date
            if st_date.tzinfo is None:
                st_date = st_date.replace(tzinfo=timezone.utc)
            watchlist_items.append((st_date, card))
        elif st.estado == "siguiendo":
            st_date = st.fecha_estado if st.fecha_estado else min_date
            if st_date.tzinfo is None:
                st_date = st_date.replace(tzinfo=timezone.utc)
            following_items.append((st_date, card))
        elif st.estado == "vista":
            st_date = st.fecha_estado if st.fecha_estado else min_date
            if st_date.tzinfo is None:
                st_date = st_date.replace(tzinfo=timezone.utc)
            recently_watched_items.append((st_date, card))

    # Orden cronológico descendente (más reciente primero)
    favorites_items.sort(key=lambda x: x[0], reverse=True)
    watchlist_items.sort(key=lambda x: x[0], reverse=True)
    following_items.sort(key=lambda x: x[0], reverse=True)
    recently_watched_items.sort(key=lambda x: x[0], reverse=True)

    return UserLibraryResponse(
        following=[item[1] for item in following_items],
        favorites=[item[1] for item in favorites_items],
        watchlist=[item[1] for item in watchlist_items],
        recently_watched=[item[1] for item in recently_watched_items]
    )


WINDOW_DAYS_MAP: dict[str, int] = {
    "1m": 30,
    "3m": 90,
    "6m": 180,
    "1y": 365,
    "5y": 365 * 5,
    "10y": 365 * 10,
}


async def get_user_stats(
    db: AsyncSession,
    usuario_id: int,
    window: str = "all_time"
) -> UserStatsResponse:
    """Calcula las estadísticas del perfil conforme a los wireframes y la ventana de tiempo seleccionada."""
    days = WINDOW_DAYS_MAP.get(window)
    since_date: Optional[datetime] = None
    if days:
        since_date = datetime.now(timezone.utc) - timedelta(days=days)

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
    if since_date:
        q_movies = q_movies.where(EstadoUsuarioTitulo.fecha_estado >= since_date)
    res_m = await db.execute(q_movies)
    watched_movies = res_m.scalars().all()
    movies_count = len(watched_movies)
    movie_minutes = sum(m.duracion or 100 for m in watched_movies)

    # 2. Episodios vistos (para las horas de visionado se cuentan solo los episodios vistos durante la ventana)
    q_eps = (
        select(Episodio, Titulo)
        .join(EpisodioVisto, EpisodioVisto.episodio_id == Episodio.id)
        .join(Temporada, Episodio.temporada_id == Temporada.id)
        .join(Titulo, Temporada.titulo_id == Titulo.id)
        .options(selectinload(Titulo.generos))
        .where(EpisodioVisto.usuario_id == usuario_id)
    )
    if since_date:
        q_eps = q_eps.where(EpisodioVisto.fecha_visto >= since_date)
    res_e = await db.execute(q_eps)
    watched_ep_rows = res_e.all()
    episodes_count = len(watched_ep_rows)
    tv_minutes = sum(ep.duracion or 45 for ep, _ in watched_ep_rows)

    # Series vistas (cuentan si se marcaron como 'vista' en ese periodo de tiempo)
    q_series = (
        select(Titulo)
        .join(EstadoUsuarioTitulo, EstadoUsuarioTitulo.titulo_id == Titulo.id)
        .options(selectinload(Titulo.generos))
        .where(
            EstadoUsuarioTitulo.usuario_id == usuario_id,
            EstadoUsuarioTitulo.estado == "vista",
            Titulo.tipo == "tv"
        )
    )
    if since_date:
        q_series = q_series.where(EstadoUsuarioTitulo.fecha_estado >= since_date)
    res_s = await db.execute(q_series)
    watched_series = res_s.scalars().all()
    series_count = len(watched_series)

    movie_hours = round(movie_minutes / 60.0, 1)
    tv_hours = round(tv_minutes / 60.0, 1)
    total_hours = round((movie_minutes + tv_minutes) / 60.0, 1)

    # Promedio de películas por semana
    user = await db.get(Usuario, usuario_id)
    if user and user.fecha_registro:
        reg_date = user.fecha_registro
        if reg_date.tzinfo is None:
            reg_date = reg_date.replace(tzinfo=timezone.utc)
        now_utc = datetime.now(timezone.utc)
        days_diff = max(1.0, (now_utc - reg_date).total_seconds() / 86400.0)
        effective_days = min(days, days_diff) if days else days_diff
        weeks = max(1.0, effective_days / 7.0)
        avg_movies_per_week = round(movies_count / weeks, 1)
    else:
        avg_movies_per_week = float(movies_count)

    # Temporadas completadas
    q_seasons = (
        select(Temporada)
        .options(selectinload(Temporada.episodios))
        .join(Episodio, Episodio.temporada_id == Temporada.id)
        .join(EpisodioVisto, EpisodioVisto.episodio_id == Episodio.id)
        .where(EpisodioVisto.usuario_id == usuario_id)
    )
    if since_date:
        q_seasons = q_seasons.where(EpisodioVisto.fecha_visto >= since_date)
    q_seasons = q_seasons.distinct()
    res_seasons = await db.execute(q_seasons)
    user_touched_seasons = res_seasons.scalars().all()

    user_ep_ids = {ep.id for ep, _ in watched_ep_rows}
    today = date.today()
    seasons_completed_count = 0
    for s in user_touched_seasons:
        aired_eps = [ep for ep in s.episodios if not ep.fecha_estreno or ep.fecha_estreno <= today]
        if aired_eps and all(ep.id in user_ep_ids for ep in aired_eps):
            seasons_completed_count += 1

    # 3. Distribución de géneros vistos (1 por cada título único consumido en la ventana)
    watched_titles_dict = {m.id: m for m in watched_movies}
    for _, t in watched_ep_rows:
        watched_titles_dict[t.id] = t
    for s in watched_series:
        watched_titles_dict[s.id] = s

    genres_dist = {}
    for t in watched_titles_dict.values():
        for g in t.generos:
            genres_dist[g.nombre] = genres_dist.get(g.nombre, 0) + 1

    # 4. Top 5 por Popularidad y Calificación de la Comunidad (de los títulos vistos en la ventana)
    all_watched_title_ids = set(watched_titles_dict.keys())
    top_pop = []
    top_community = []
    if all_watched_title_ids:
        q_pop = (
            select(Titulo)
            .options(selectinload(Titulo.temporadas))
            .where(Titulo.id.in_(all_watched_title_ids))
            .order_by(desc(Titulo.popularidad_percentil), desc(Titulo.popularidad))
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
                metric_value=round(
                    (t.popularidad_percentil if (t.popularidad_percentil and t.popularidad_percentil > 1) else ((t.popularidad_percentil or 0.0) * 100)),
                    1
                )
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

    # 5. Top 5 por My Rating (reseñas con puntaje del propio usuario dentro de la ventana si aplica)
    q_user_rate = (
        select(Titulo, Resena.puntaje)
        .join(Resena, Resena.titulo_id == Titulo.id)
        .options(selectinload(Titulo.temporadas))
        .where(Resena.usuario_id == usuario_id, Resena.puntaje.isnot(None))
    )
    if since_date:
        q_user_rate = q_user_rate.where(Resena.fecha >= since_date)
    q_user_rate = q_user_rate.order_by(desc(Resena.puntaje)).limit(5)
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
        avg_movies_per_week=avg_movies_per_week,
        series_watched_count=series_count,
        seasons_completed_count=seasons_completed_count,
        episodes_watched_count=episodes_count,
        top_by_popularity=top_pop,
        top_by_community_rating=top_community,
        top_by_user_rating=top_user_rate,
        genres_distribution=genres_dist,
        window=window
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


async def get_available_countries(db: AsyncSession) -> list[CountryItem]:
    """Retorna la lista de países disponibles en el catálogo con código y conteo de títulos."""
    res = await db.execute(
        select(Titulo.pais, func.count(Titulo.id))
        .where(Titulo.pais.isnot(None), Titulo.pais != "")
        .group_by(Titulo.pais)
        .order_by(func.count(Titulo.id).desc())
    )
    return [CountryItem(code=row[0], count=row[1]) for row in res.all()]


async def get_available_languages(db: AsyncSession) -> list[LanguageItem]:
    """Retorna la lista de idiomas originales disponibles en el catálogo con código y conteo de títulos."""
    res = await db.execute(
        select(Titulo.idioma_original, func.count(Titulo.id))
        .where(Titulo.idioma_original.isnot(None), Titulo.idioma_original != "")
        .group_by(Titulo.idioma_original)
        .order_by(func.count(Titulo.id).desc())
    )
    return [LanguageItem(code=row[0], count=row[1]) for row in res.all()]


# =============================================================================
# RECOMENDADOR INTELIGENTE POR IA (FASE 6)
# =============================================================================

GENRE_KEYWORD_MAP = {
    "accion": "Action",
    "acción": "Action",
    "action": "Action",
    "aventura": "Adventure",
    "adventure": "Adventure",
    "animacion": "Animation",
    "animación": "Animation",
    "animation": "Animation",
    "anime": "Animation",
    "comedia": "Comedy",
    "comedy": "Comedy",
    "humor": "Comedy",
    "crimen": "Crime",
    "crime": "Crime",
    "policial": "Crime",
    "policiales": "Crime",
    "robo": "Crime",
    "robos": "Crime",
    "atraco": "Crime",
    "atracos": "Crime",
    "heist": "Crime",
    "estafa": "Crime",
    "estafas": "Crime",
    "estafador": "Crime",
    "estafadores": "Crime",
    "mafia": "Crime",
    "gangster": "Crime",
    "gangsters": "Crime",
    "asesino": "Crime",
    "asesinos": "Crime",
    "asesinato": "Crime",
    "asesinatos": "Crime",
    "serial killer": "Crime",
    "documental": "Documentary",
    "documentary": "Documentary",
    "drama": "Drama",
    "dramatica": "Drama",
    "dramática": "Drama",
    "familia": "Family",
    "family": "Family",
    "familiar": "Family",
    "infantil": "Family",
    "fantasia": "Fantasy",
    "fantasía": "Fantasy",
    "fantasy": "Fantasy",
    "magia": "Fantasy",
    "mago": "Fantasy",
    "magos": "Fantasy",
    "historia": "History",
    "history": "History",
    "historica": "History",
    "histórica": "History",
    "terror": "Horror",
    "horror": "Horror",
    "miedo": "Horror",
    "zombie": "Horror",
    "zombies": "Horror",
    "vampiro": "Horror",
    "vampiros": "Horror",
    "musica": "Music",
    "música": "Music",
    "music": "Music",
    "musical": "Music",
    "misterio": "Mystery",
    "mystery": "Mystery",
    "romance": "Romance",
    "romantica": "Romance",
    "romántica": "Romance",
    "amor": "Romance",
    "ciencia ficcion": "Science Fiction",
    "ciencia ficción": "Science Fiction",
    "sci-fi": "Science Fiction",
    "scifi": "Science Fiction",
    "science fiction": "Science Fiction",
    "alien": "Science Fiction",
    "aliens": "Science Fiction",
    "extraterrestre": "Science Fiction",
    "extraterrestres": "Science Fiction",
    "robot": "Science Fiction",
    "robots": "Science Fiction",
    "espacio": "Science Fiction",
    "suspenso": "Thriller",
    "suspense": "Thriller",
    "thriller": "Thriller",
    "thrillers": "Thriller",
    "espia": "Thriller",
    "espía": "Thriller",
    "espias": "Thriller",
    "espías": "Thriller",
    "espionaje": "Thriller",
    "conspiracion": "Thriller",
    "conspiración": "Thriller",
    "belica": "War",
    "bélica": "War",
    "guerra": "War",
    "war": "War",
    "western": "Western",
}

# Mapeo semántico y bilingüe (ES -> EN) para conceptos, argumentos y temas recurrentes en sinopsis de TMDB
THEME_EXPANSION_MAP = {
    # Planes, atracos, robos, golpes maestros y estafas
    "plan": ["plan", "scheme", "mastermind", "heist", "elaborate", "operation"],
    "planes": ["plan", "plans", "scheme", "mastermind", "heist", "elaborate", "operation"],
    "elaborado": ["elaborate", "clever", "complex", "mastermind", "scheme", "intricate"],
    "elaborados": ["elaborate", "clever", "complex", "mastermind", "scheme", "intricate"],
    "maestro": ["mastermind", "master", "clever", "brilliant"],
    "maestros": ["mastermind", "master", "clever", "brilliant"],
    "ingenioso": ["clever", "ingenious", "smart", "brilliant", "witty"],
    "ingeniosos": ["clever", "ingenious", "smart", "brilliant", "witty"],
    "robo": ["robbery", "rob", "heist", "thief", "thieves", "steal", "bank"],
    "robos": ["robbery", "rob", "heist", "thief", "thieves", "steal", "bank"],
    "ladron": ["thief", "robber", "burglar", "con artist"],
    "ladrón": ["thief", "robber", "burglar", "con artist"],
    "ladrones": ["thieves", "robbers", "burglars", "heist crew"],
    "atraco": ["heist", "robbery", "rob", "bank", "vault", "thieves"],
    "atracos": ["heist", "robbery", "rob", "bank", "vault", "thieves"],
    "heist": ["heist", "robbery", "rob", "thief", "con", "scheme", "bank"],
    "estafa": ["con", "con artist", "scam", "fraud", "swindle", "trick"],
    "estafas": ["con", "con artist", "scam", "fraud", "swindle", "trick"],
    "estafador": ["con artist", "swindler", "grifter", "scammer"],
    "estafadores": ["con artists", "swindlers", "grifters"],
    "trampa": ["trap", "setup", "frame", "trick"],
    "trampas": ["traps", "setup", "frame", "tricks"],

    # Crimen, mafia, narcotráfico y bajos fondos
    "crimen": ["crime", "criminal", "underworld", "heist", "robbery"],
    "crimenes": ["crime", "criminal", "underworld", "crimes"],
    "crímenes": ["crime", "criminal", "underworld", "crimes"],
    "mafia": ["mafia", "mob", "gangster", "cartel", "syndicate", "godfather"],
    "gangster": ["gangster", "mob", "mafia", "mobster"],
    "gangsters": ["gangsters", "mobsters", "mafia"],
    "narco": ["cartel", "drug lord", "narcotics", "trafficking"],
    "narcos": ["cartel", "drug lords", "narcotics", "trafficking"],
    "drogas": ["drugs", "cartel", "narcotics", "smuggling"],

    # Suspenso, giros y tensión psicológica
    "thriller": ["thriller", "suspense", "tension", "psychological", "twist"],
    "thrillers": ["thriller", "suspense", "tension", "psychological", "twist"],
    "suspenso": ["suspense", "thriller", "tension", "twist", "cliffhanger"],
    "psicologico": ["psychological", "mind", "mental", "sanity", "madness"],
    "psicológico": ["psychological", "mind", "mental", "sanity", "madness"],
    "giro": ["twist", "unexpected", "plot twist", "shocking reveal"],
    "giros": ["twist", "twists", "unexpected", "plot twist"],

    # Investigación, detectives y policías
    "detective": ["detective", "investigation", "cop", "police", "clues", "sherlock"],
    "detectives": ["detectives", "investigation", "cops", "police", "clues"],
    "investigacion": ["investigation", "detective", "mystery", "solve", "case"],
    "investigación": ["investigation", "detective", "mystery", "solve", "case"],
    "policial": ["police", "cop", "detective", "investigation", "law enforcement"],
    "policiales": ["police", "cops", "detectives", "investigation"],
    "policia": ["police", "cop", "officer", "sheriff"],
    "policía": ["police", "cop", "officer", "sheriff"],
    "policias": ["police", "cops", "officers", "sheriffs"],
    "policías": ["police", "cops", "officers", "sheriffs"],
    "misterio": ["mystery", "riddle", "puzzle", "secret", "whodunit"],
    "misterios": ["mystery", "mysteries", "riddle", "puzzle"],

    # Asesinos, homicidios y violencia
    "asesino": ["killer", "serial killer", "murderer", "assassin", "hitman"],
    "asesinos": ["killers", "serial killers", "murderers", "assassins", "hitmen"],
    "asesinato": ["murder", "homicide", "kill", "crime", "slain"],
    "asesinatos": ["murders", "homicides", "kills", "crimes"],
    "sicario": ["hitman", "assassin", "contract killer"],
    "sicarios": ["hitmen", "assassins", "contract killers"],

    # Espionaje y conspiraciones
    "espia": ["spy", "secret agent", "espionage", "undercover", "cia", "mi6"],
    "espía": ["spy", "secret agent", "espionage", "undercover", "cia", "mi6"],
    "espias": ["spies", "secret agents", "espionage", "undercover"],
    "espías": ["spies", "secret agents", "espionage", "undercover"],
    "espionaje": ["espionage", "spy", "intelligence", "covert", "cia", "kgb"],
    "conspiracion": ["conspiracy", "covert", "cover-up", "plot", "government"],
    "conspiración": ["conspiracy", "covert", "cover-up", "plot", "government"],

    # Prisión y fuga
    "carcel": ["prison", "inmate", "jail", "escape", "convict"],
    "cárcel": ["prison", "inmate", "jail", "escape", "convict"],
    "prision": ["prison", "inmate", "jail", "escape", "convict"],
    "prisión": ["prison", "inmate", "jail", "escape", "convict"],
    "fuga": ["escape", "breakout", "prison break", "getaway"],
    "escape": ["escape", "breakout", "prison break", "evade"],

    # Venganza y redención
    "venganza": ["revenge", "vengeance", "retribution", "payback", "vendetta"],
    "redencion": ["redemption", "atonement", "forgiveness"],
    "redención": ["redemption", "atonement", "forgiveness"],

    # Magia e ilusionismo
    "magia": ["magic", "magician", "illusionist", "trick", "sorcery", "prestidigitation"],
    "mago": ["magician", "illusionist", "magic", "trick", "wizard"],
    "magos": ["magicians", "illusionists", "magic", "tricks"],
    "ilusionista": ["illusionist", "magician", "magic", "stage trick"],
    "ilusionistas": ["illusionists", "magicians", "magic"],

    # Ciencia ficción, tiempo y espacio
    "temporal": ["time travel", "timeline", "time loop", "time machine"],
    "tiempo": ["time travel", "timeline", "time loop", "clock"],
    "espacio": ["space", "galaxy", "orbit", "astronaut", "spaceship"],
    "alien": ["alien", "extraterrestrial", "invasion", "creature"],
    "aliens": ["aliens", "extraterrestrials", "invasion"],
    "robot": ["robot", "android", "cyborg", "artificial intelligence", "ai"],
    "robots": ["robots", "androids", "cyborgs", "artificial intelligence"],
    "apocalipsis": ["apocalypse", "post-apocalyptic", "dystopia", "wasteland"],
    "zombie": ["zombie", "undead", "infected", "virus", "apocalypse"],
    "zombies": ["zombies", "undead", "infected", "virus"],
}

# Patrones para detectar intención de ambientación / trama / locación (Setting)
SETTING_PATTERNS = [
    r"\bambientad[ao]s?\s+en\b",
    r"\btranscurr[aeio]n?\s+(?:en|por)\b",
    r"\bque\s+ocurr[ae]n?\s+en\b",
    r"\bsituad[ao]s?\s+en\b",
    r"\bfilmad[ao]s?\s+en\b",
    r"\brodad[ao]s?\s+en\b",
    r"\bviajan?\s+a\b",
    r"\bhistoria\s+(?:en|sobre)\b",
    r"\btrama\s+en\b",
    r"\bdesarrollad[ao]s?\s+en\b",
    r"\bque\s+pasan?\s+en\b",
    r"\bset\s+in\b",
    r"\btakes?\s+place\s+in\b",
    r"\bfilmed\s+in\b",
]

# Mapeo de términos geográficos a códigos ISO 3166-1 (país de producción)
COUNTRY_KEYWORDS_MAP = {
    # Argentina
    "argentina": "AR",
    "argentinas": "AR",
    "argentino": "AR",
    "argentinos": "AR",
    "cine argentino": "AR",
    "peliculas argentinas": "AR",
    "películas argentinas": "AR",
    # España
    "españa": "ES",
    "espana": "ES",
    "española": "ES",
    "españolas": "ES",
    "español": "ES",
    "españoles": "ES",
    "cine español": "ES",
    # Corea del Sur
    "corea": "KR",
    "corea del sur": "KR",
    "coreana": "KR",
    "coreanas": "KR",
    "coreano": "KR",
    "coreanos": "KR",
    "k-drama": "KR",
    "kdrama": "KR",
    "korean": "KR",
    "cine coreano": "KR",
    # Japón
    "japón": "JP",
    "japon": "JP",
    "japonesa": "JP",
    "japonesas": "JP",
    "japonés": "JP",
    "japones": "JP",
    "japoneses": "JP",
    "japanese": "JP",
    "japan": "JP",
    "cine japonés": "JP",
    "cine japones": "JP",
    # Francia
    "francia": "FR",
    "francesa": "FR",
    "francesas": "FR",
    "francés": "FR",
    "frances": "FR",
    "franceses": "FR",
    "french": "FR",
    "france": "FR",
    "cine francés": "FR",
    "cine frances": "FR",
    # Italia
    "italia": "IT",
    "italiana": "IT",
    "italianas": "IT",
    "italiano": "IT",
    "italianos": "IT",
    "italian": "IT",
    "italy": "IT",
    "cine italiano": "IT",
    # México
    "méxico": "MX",
    "mexico": "MX",
    "mexicana": "MX",
    "mexicanas": "MX",
    "mexicano": "MX",
    "mexicanos": "MX",
    "mexican": "MX",
    "cine mexicano": "MX",
    # Reino Unido / Inglaterra
    "reino unido": "GB",
    "inglaterra": "GB",
    "británica": "GB",
    "britanica": "GB",
    "británicas": "GB",
    "britanicas": "GB",
    "británico": "GB",
    "britanico": "GB",
    "británicos": "GB",
    "britanicos": "GB",
    "british": "GB",
    "uk": "GB",
    "cine británico": "GB",
    "cine britanico": "GB",
    # Alemania
    "alemania": "DE",
    "alemana": "DE",
    "alemanas": "DE",
    "alemán": "DE",
    "aleman": "DE",
    "alemanes": "DE",
    "german": "DE",
    "germany": "DE",
    "cine alemán": "DE",
    "cine aleman": "DE",
    # Brasil
    "brasil": "BR",
    "brasileña": "BR",
    "brasileñas": "BR",
    "brasileño": "BR",
    "brasileños": "BR",
    "brasilera": "BR",
    "brasileras": "BR",
    "brasilero": "BR",
    "brasileros": "BR",
    "brazil": "BR",
    "brazilian": "BR",
    "cine brasileño": "BR",
    # Estados Unidos
    "estados unidos": "US",
    "eeuu": "US",
    "ee.uu.": "US",
    "estadounidense": "US",
    "estadounidenses": "US",
    "americana": "US",
    "americanas": "US",
    "americano": "US",
    "americanos": "US",
    "american": "US",
    "usa": "US",
    "cine estadounidense": "US",
    # Chile
    "chile": "CL",
    "chilena": "CL",
    "chilenas": "CL",
    "chileno": "CL",
    "chilenos": "CL",
    "cine chileno": "CL",
    # Uruguay
    "uruguay": "UY",
    "uruguaya": "UY",
    "uruguayas": "UY",
    "uruguayo": "UY",
    "uruguayos": "UY",
    "cine uruguayo": "UY",
    # Colombia
    "colombia": "CO",
    "colombiana": "CO",
    "colombianas": "CO",
    "colombiano": "CO",
    "colombianos": "CO",
    "cine colombiano": "CO",
    # Hong Kong
    "hong kong": "HK",
    "hongkonesa": "HK",
    "hongkones": "HK",
    "hongkong": "HK",
    # China
    "china": "CN",
    "chinas": "CN",
    "chino": "CN",
    "chinos": "CN",
    "chinese": "CN",
    "cine chino": "CN",
    # India
    "india": "IN",
    "indio": "IN",
    "indias": "IN",
    "indios": "IN",
    "bollywood": "IN",
    "indian": "IN",
    "cine indio": "IN",
    # Canadá
    "canadá": "CA",
    "canada": "CA",
    "canadiense": "CA",
    "canadienses": "CA",
    "canadian": "CA",
    # Australia
    "australia": "AU",
    "australiana": "AU",
    "australiano": "AU",
    "australian": "AU",
    # Dinamarca
    "dinamarca": "DK",
    "danesa": "DK",
    "danés": "DK",
    "danes": "DK",
    "danish": "DK",
    "cine danés": "DK",
    # Suecia
    "suecia": "SE",
    "sueca": "SE",
    "sueco": "SE",
    "swedish": "SE",
    "cine sueco": "SE",
    # Noruega
    "noruega": "NO",
    "noruego": "NO",
    "norwegian": "NO",
    "cine noruego": "NO",
    # Rusia
    "rusia": "RU",
    "rusa": "RU",
    "ruso": "RU",
    "russian": "RU",
    "cine ruso": "RU",
    # Turquía
    "turquía": "TR",
    "turquia": "TR",
    "turca": "TR",
    "turco": "TR",
    "turkish": "TR",
    "turkey": "TR",
    "series turcas": "TR",
    "novelas turcas": "TR",
    # Tailandia
    "tailandia": "TH",
    "tailandesa": "TH",
    "thai": "TH",
    "thailand": "TH",
    # Polonia
    "polonia": "PL",
    "polaca": "PL",
    "polaco": "PL",
    "polish": "PL",
    "poland": "PL",
    # Irlanda
    "irlanda": "IE",
    "irlandesa": "IE",
    "irlandés": "IE",
    "irish": "IE",
    "ireland": "IE",
}

# Mapeo de frases de idioma a códigos ISO 639-1
LANGUAGE_KEYWORDS_MAP = {
    # Español / Castellano
    "en español": "es",
    "en espanol": "es",
    "en castellano": "es",
    "en habla hispana": "es",
    "de habla hispana": "es",
    "habla hispana": "es",
    "idioma español": "es",
    "idioma espanol": "es",
    "in spanish": "es",
    # Inglés
    "en inglés": "en",
    "en ingles": "en",
    "en lengua inglesa": "en",
    "de habla inglesa": "en",
    "habla inglesa": "en",
    "in english": "en",
    # Japonés
    "en japonés": "ja",
    "en japones": "ja",
    "in japanese": "ja",
    # Coreano
    "en coreano": "ko",
    "in korean": "ko",
    # Francés
    "en francés": "fr",
    "en frances": "fr",
    "in french": "fr",
    # Italiano
    "en italiano": "it",
    "in italian": "it",
    # Alemán
    "en alemán": "de",
    "en aleman": "de",
    "in german": "de",
    # Portugués
    "en portugués": "pt",
    "en portugues": "pt",
    "in portuguese": "pt",
    # Ruso
    "en ruso": "ru",
    "in russian": "ru",
    # Chino
    "en chino": ["zh", "cn"],
    "en mandarín": ["zh", "cn"],
    "en mandarin": ["zh", "cn"],
    "en cantonés": ["zh", "cn"],
    "en cantones": ["zh", "cn"],
    "in chinese": ["zh", "cn"],
    # Turco
    "en turco": "tr",
    "in turkish": "tr",
    # Hindi
    "en hindi": "hi",
    "in hindi": "hi",
    # Danés
    "en danés": "da",
    "en danes": "da",
    "in danish": "da",
    # Sueco
    "en sueco": "sv",
    "in swedish": "sv",
    # Noruego
    "en noruego": "no",
    "in norwegian": "no",
    # Tailandés
    "en tailandés": "th",
    "en tailandes": "th",
    "in thai": "th",
    # Polaco
    "en polaco": "pl",
    "in polish": "pl",
}

# Mapeo de ciudades icónicas a sus respectivos códigos de país ISO 3166-1
CITY_TO_COUNTRY_MAP = {
    "buenos aires": "AR",
    "madrid": "ES",
    "barcelona": "ES",
    "sevilla": "ES",
    "paris": "FR",
    "parís": "FR",
    "tokio": "JP",
    "tokyo": "JP",
    "kioto": "JP",
    "seul": "KR",
    "seúl": "KR",
    "roma": "IT",
    "venecia": "IT",
    "milan": "IT",
    "milán": "IT",
    "florencia": "IT",
    "londres": "GB",
    "london": "GB",
    "berlin": "DE",
    "berlín": "DE",
    "munich": "DE",
    "múnich": "DE",
    "nueva york": "US",
    "new york": "US",
    "los angeles": "US",
    "los ángeles": "US",
    "chicago": "US",
    "miami": "US",
    "rio de janeiro": "BR",
    "río de janeiro": "BR",
    "sao paulo": "BR",
    "são paulo": "BR",
    "ciudad de mexico": "MX",
    "ciudad de méxico": "MX",
    "cdmx": "MX",
}


async def get_user_recommendation_context(db: AsyncSession, usuario_id: int) -> dict:
    """Extrae el perfil condensado de gustos, favoritos y títulos vistos del usuario."""
    # 1. Favoritos
    fav_res = await db.execute(
        select(Titulo.id, Titulo.nombre)
        .join(EstadoUsuarioTitulo, EstadoUsuarioTitulo.titulo_id == Titulo.id)
        .where(
            EstadoUsuarioTitulo.usuario_id == usuario_id,
            EstadoUsuarioTitulo.favorito == True
        )
        .limit(15)
    )
    favorites = [{"id": r[0], "nombre": r[1]} for r in fav_res.all()]

    # 2. Títulos mejor puntuados por el usuario (>= 8.0)
    high_res = await db.execute(
        select(Titulo.id, Titulo.nombre, Resena.puntaje)
        .join(Resena, Resena.titulo_id == Titulo.id)
        .where(
            Resena.usuario_id == usuario_id,
            Resena.puntaje >= 8.0
        )
        .order_by(Resena.puntaje.desc())
        .limit(10)
    )
    high_rated = [{"id": r[0], "nombre": r[1], "puntaje": r[2]} for r in high_res.all()]

    # 3. Títulos vistos (IDs a excluir)
    watched_res = await db.execute(
        select(EstadoUsuarioTitulo.titulo_id)
        .where(
            EstadoUsuarioTitulo.usuario_id == usuario_id,
            EstadoUsuarioTitulo.estado == "vista"
        )
    )
    watched_ids = set(watched_res.scalars().all())

    # 4. Géneros más frecuentes en favoritos o vistos
    genre_freq_res = await db.execute(
        select(Genero.nombre, func.count(Genero.id).label("cnt"))
        .join(titulos_generos, titulos_generos.c.genero_id == Genero.id)
        .join(EstadoUsuarioTitulo, EstadoUsuarioTitulo.titulo_id == titulos_generos.c.titulo_id)
        .where(
            EstadoUsuarioTitulo.usuario_id == usuario_id,
            or_(EstadoUsuarioTitulo.favorito == True, EstadoUsuarioTitulo.estado == "vista")
        )
        .group_by(Genero.nombre)
        .order_by(desc("cnt"))
        .limit(4)
    )
    top_genres = [r[0] for r in genre_freq_res.all()]

    return {
        "favorites": favorites,
        "high_rated": high_rated,
        "watched_ids": list(watched_ids),
        "top_genres": top_genres,
        "has_history": bool(favorites or high_rated or watched_ids)
    }


async def get_recommendation_candidates(
    db: AsyncSession,
    prompt: str,
    usuario_id: Optional[int] = None,
    tipo_filtro: Optional[str] = "all",
    clarification_context: Optional[dict] = None
) -> tuple[list[dict], Optional[dict]]:
    """Selecciona un pool inteligente y acotado (35-45 títulos) de candidatos relevantes de PostgreSQL."""
    # Si hay contexto de aclaración, enriquecer términos de búsqueda para resolver respuestas relativas
    search_prompt = prompt
    if clarification_context:
        prev_p = clarification_context.get("previous_prompt", "")
        suggs = clarification_context.get("suggestions", [])
        lower_p = prompt.lower()
        if any(w in lower_p for w in ("primera", "primero", "1", "first")) and len(suggs) >= 1:
            search_prompt = f"{prompt} {suggs[0]}"
        elif any(w in lower_p for w in ("segunda", "segundo", "2", "second")) and len(suggs) >= 2:
            search_prompt = f"{prompt} {suggs[1]}"
        elif any(w in lower_p for w in ("tercera", "tercero", "3", "third")) and len(suggs) >= 3:
            search_prompt = f"{prompt} {suggs[2]}"
        else:
            search_prompt = f"{prompt} {prev_p} {' '.join(suggs)}"

    lower_prompt = search_prompt.lower()
    user_ctx = await get_user_recommendation_context(db, usuario_id) if usuario_id else None

    # Detección de intenciones sobre títulos ya vistos (Exclusivo vs. Inclusión Mixta vs. Por Defecto)
    inclusion_rewatch_phrases = [
        "puedes incluir", "puede incluir", "podés incluir", "pueden incluir",
        "podia incluir", "podía incluir", "puedo incluir", "podrias incluir", "podrías incluir",
        "incluyendo", "incluir algo que ya", "incluir lo que ya", "incluir las que ya",
        "incluir que ya", "incluir algo que ya habia visto", "incluir algo que ya había visto",
        "incluir peliculas ya", "incluir películas ya", "incluir titulos ya", "incluir títulos ya",
        "incluir vistas", "incluso si ya", "incluso ya", "incluso las que ya", "incluso lo que ya",
        "incluso peliculas ya vistas", "incluso películas ya vistas",
        "no importa si ya", "sin importar si ya",
        "aunque ya", "aunque la haya visto", "aunque las haya visto", "aunque ya la vi", "aunque ya las vi", "aunque ya vi",
        "también las que", "también si ya", "también de mis vistas", "también ya vistas",
        "tambien las que", "tambien si ya", "tambien de mis vistas", "tambien ya vistas",
        "tanto vistas como no vistas", "vistas y no vistas", "nuevas o vistas", "vistas o nuevas", "nuevas y vistas",
        "pueden ser repetidas", "puede ser repetida", "pueden ser vistas", "puede ser vista",
        "permitir vistas", "permite vistas", "permitiendo vistas",
        "can include watched", "include watched", "even if watched", "even if already seen",
        "both watched and unwatched", "allow watched"
    ]

    exclusive_watched_phrases = [
        "solo de las que ya vi", "solo las que ya vi", "sólo lo que ya vi", "solo lo que ya vi",
        "solo que ya vi", "sólo que ya vi", "unicamente lo que ya vi", "únicamente lo que ya vi",
        "unicamente las que ya vi", "únicamente las que ya vi", "exclusivamente lo que ya vi",
        "exclusivamente las que ya vi", "exclusivamente de mis vistas",
        "solo de mis vistas", "sólo de mis vistas", "solo vistas", "sólo vistas", "solo titulos vistos",
        "solo títulos vistos", "solo peliculas que ya vi", "solo películas que ya vi",
        "de las que ya vi", "de lo que ya vi", "de los titulos que ya vi", "de los títulos que ya vi",
        "de las peliculas que ya vi", "de las películas que ya vi", "de las pelis que ya vi",
        "de mi biblioteca ya vista", "de mis vistas que valga", "de mis peliculas vistas",
        "only watched", "only from what i watched", "only from my watched", "only already seen",
        "exclusively from my watched", "from my watched list only"
    ]

    pure_rewatch_phrases = [
        "volver a ver", "repetir", "rewatch", "rever", "revivir"
    ]

    has_inclusion = any(ip in lower_prompt for ip in inclusion_rewatch_phrases)
    has_exclusive = any(ep in lower_prompt for ep in exclusive_watched_phrases)
    has_pure_rewatch = any(rp in lower_prompt for rp in pure_rewatch_phrases)

    if has_inclusion:
        only_watched = False
        allow_rewatch = True
    elif has_exclusive or has_pure_rewatch:
        only_watched = True
        allow_rewatch = True
    else:
        only_watched = False
        allow_rewatch = False

    watched_ids = set(user_ctx.get("watched_ids", [])) if user_ctx else set()

    if user_ctx:
        user_ctx["only_watched"] = only_watched
        user_ctx["allow_rewatch"] = allow_rewatch

    # Detección de tipo en el prompt si no vino impuesto por tipo_filtro
    effective_tipo = tipo_filtro
    if effective_tipo == "all":
        if any(w in lower_prompt for w in ("serie", "series", "temporada", "temporadas", "tv show", "tv series")):
            effective_tipo = "tv"
        elif any(w in lower_prompt for w in ("pelicula", "película", "peliculas", "películas", "peli", "pelis", "movie", "movies", "film", "films")):
            effective_tipo = "movie"

    # Detección de décadas o rangos temporales
    min_year, max_year = None, None
    if "80" in lower_prompt or "ochenta" in lower_prompt:
        min_year, max_year = 1980, 1989
    elif "90" in lower_prompt or "noventa" in lower_prompt:
        min_year, max_year = 1990, 1999
    elif "2000" in lower_prompt or "dos mil" in lower_prompt:
        min_year, max_year = 2000, 2009
    elif "50" in lower_prompt or "60" in lower_prompt or "70" in lower_prompt or "dorado" in lower_prompt:
        min_year, max_year = 1950, 1979
    elif any(w in lower_prompt for w in ("clasico", "clásico", "classic", "antigua", "antiguo")):
        max_year = datetime.now().year - 20
    elif any(w in lower_prompt for w in ("reciente", "recientes", "estreno", "estrenos", "recent", "new")):
        min_year = datetime.now().year - 3

    # Detección de géneros del mapeo
    detected_genres = set()
    for kw, gname in GENRE_KEYWORD_MAP.items():
        if kw in lower_prompt:
            detected_genres.add(gname)

    # Extraer términos significativos del prompt para búsqueda de directores, actores, títulos y temáticas
    STOP_WORDS = {
        "pelicula", "peliculas", "película", "películas", "serie", "series", "temporada", "temporadas",
        "movie", "movies", "film", "films", "show", "shows", "quiero", "ver", "algo", "sobre", "con",
        "para", "como", "buena", "buenas", "bueno", "buenos", "recomiendame", "recomendame", "recomienda",
        "dame", "busco", "algun", "alguna", "algunas", "algunos", "mejor", "mejores", "top", "great",
        "want", "watch", "give", "look", "looking", "about", "like", "some", "best", "good", "recommend",
        "please", "por", "favor", "cual", "cuales", "cuál", "cuáles", "que", "qué", "los", "las", "les",
        "una", "uno", "unos", "unas", "del", "de", "en", "el", "la", "un", "and", "the", "with", "from",
        "entre", "ambos", "estilo", "tipo", "mucho", "muchas", "donde", "dondequiera", "alguien"
    }
    raw_tokens = re.findall(r"[a-zA-ZáéíóúÁÉÍÓÚñÑ0-9]+", lower_prompt)
    search_terms = [t for t in raw_tokens if len(t) >= 3 and t not in STOP_WORDS]
    bigrams = [" ".join(raw_tokens[i:i+2]) for i in range(len(raw_tokens)-1)]
    valid_bigrams = [bg for bg in bigrams if len(bg) >= 7 and not any(sw in bg.split() for sw in STOP_WORDS)]

    # Expandir conceptos temáticos bilingües (ES -> EN) para análisis en sinopsis
    expanded_syn_terms: set[str] = set()
    for t in search_terms:
        expanded_syn_terms.add(t)
        if t in THEME_EXPANSION_MAP:
            expanded_syn_terms.update(THEME_EXPANSION_MAP[t])
    syn_search_words = [w for w in expanded_syn_terms if len(w) >= 4]

    # Detección de exclusiones negativas de género (Negative Filtering)
    GENRE_NEGATION_MAP = {
        "anime": ["Animación"],
        "animacion": ["Animación"],
        "animación": ["Animación"],
        "animation": ["Animación"],
        "comedia": ["Comedia"],
        "comedy": ["Comedia"],
        "terror": ["Terror"],
        "horror": ["Terror"],
        "miedo": ["Terror"],
        "documental": ["Documental"],
        "documentales": ["Documental"],
        "documentary": ["Documental"],
        "drama": ["Drama"],
        "romance": ["Romance"],
        "romantica": ["Romance"],
        "romántica": ["Romance"],
        "accion": ["Acción"],
        "acción": ["Acción"],
        "action": ["Acción"],
        "ciencia ficcion": ["Ciencia ficción"],
        "ciencia ficción": ["Ciencia ficción"],
        "sci-fi": ["Ciencia ficción"],
        "scifi": ["Ciencia ficción"],
        "western": ["Western"],
        "musical": ["Música"],
    }
    excluded_genres = set()
    for neg_prefix in ("no", "sin", "nada de", "excepto", "not", "without", "exclude"):
        for term, g_list in GENRE_NEGATION_MAP.items():
            pattern = rf"\b{re.escape(neg_prefix)}\s+{re.escape(term)}\b"
            if re.search(pattern, lower_prompt):
                excluded_genres.update(g_list)

    # Detección de intención de ambientación / locación (Setting) vs. producción (Origin)
    is_setting_intent = any(re.search(pat, lower_prompt) for pat in SETTING_PATTERNS)

    detected_country = None
    detected_country_keyword = None
    for kw in sorted(COUNTRY_KEYWORDS_MAP.keys(), key=len, reverse=True):
        if re.search(rf"\b{re.escape(kw)}\b", lower_prompt):
            detected_country = COUNTRY_KEYWORDS_MAP[kw]
            detected_country_keyword = kw
            break

    # Si no detectó país por nombre de país/gentilicio, buscar si mencionó una ciudad icónica
    if not detected_country:
        for city, ccode in sorted(CITY_TO_COUNTRY_MAP.items(), key=lambda x: len(x[0]), reverse=True):
            if re.search(rf"\b{re.escape(city)}\b", lower_prompt):
                detected_country = ccode
                detected_country_keyword = city
                break

    detected_language = None
    for kw in sorted(LANGUAGE_KEYWORDS_MAP.keys(), key=len, reverse=True):
        if re.search(rf"\b{re.escape(kw)}\b", lower_prompt):
            detected_language = LANGUAGE_KEYWORDS_MAP[kw]
            break

    # Si hay intención de ambientación/locación (ej: "ambientada en Argentina" o "que transcurra en Buenos Aires"),
    # incluir el término geográfico en la búsqueda de sinopsis para recuperar títulos situados allí
    if is_setting_intent and detected_country_keyword:
        syn_search_words.append(detected_country_keyword)
        # Si el keyword fue una ciudad, o un país, agregar ambos a la búsqueda en sinopsis
        if detected_country_keyword in CITY_TO_COUNTRY_MAP:
            for c_kw, c_code in COUNTRY_KEYWORDS_MAP.items():
                if c_code == detected_country and len(c_kw) >= 5 and " " not in c_kw:
                    syn_search_words.append(c_kw)
                    break
        elif detected_country in ("AR", "ES", "FR", "IT", "JP", "KR", "GB", "US", "DE", "BR", "MX"):
            for city_name, c_code in CITY_TO_COUNTRY_MAP.items():
                if c_code == detected_country:
                    syn_search_words.append(city_name)

    def apply_base_filters(query):
        if effective_tipo in ("movie", "tv"):
            query = query.where(Titulo.tipo == effective_tipo)
        if min_year:
            query = query.where(extract("year", Titulo.fecha_estreno) >= min_year)
        if max_year:
            query = query.where(extract("year", Titulo.fecha_estreno) <= max_year)
        # Si la intención es de Producción / Origen (no Setting), filtrar estrictamente por país
        if detected_country and not is_setting_intent:
            if isinstance(detected_country, list):
                query = query.where(Titulo.pais.in_(detected_country))
            else:
                query = query.where(Titulo.pais == detected_country)
        # Filtro estricto por idioma original
        if detected_language:
            if isinstance(detected_language, list):
                query = query.where(Titulo.idioma_original.in_(detected_language))
            else:
                query = query.where(Titulo.idioma_original == detected_language)
        if only_watched:
            if watched_ids:
                query = query.where(Titulo.id.in_(list(watched_ids)))
            else:
                query = query.where(Titulo.id == -1)
        elif watched_ids and not allow_rewatch:
            query = query.where(Titulo.id.notin_(list(watched_ids)))
        if excluded_genres:
            ex_subq = (
                select(titulos_generos.c.titulo_id)
                .join(Genero, Genero.id == titulos_generos.c.genero_id)
                .where(Genero.nombre.in_(list(excluded_genres)))
                .scalar_subquery()
            )
            query = query.where(Titulo.id.notin_(ex_subq))
        return query

    entity_titles: dict[int, Titulo] = {}
    theme_titles: dict[int, Titulo] = {}
    vector_titles: dict[int, Titulo] = {}
    fallback_titles: dict[int, Titulo] = {}

    is_postgres = False
    try:
        bind = db.bind or (db.get_bind() if hasattr(db, "get_bind") else None)
        if bind and bind.dialect.name == "postgresql":
            is_postgres = True
    except Exception:
        pass

    # -------------------------------------------------------------------------
    # 0. BÚSQUEDA POR ENTIDADES DIRECTAS (Actores, Directores, Nombres de títulos)
    #    MÁXIMA PRIORIDAD: si el usuario nombró a un actor o director (ej: Ian McKellen, Brad Pitt),
    #    estas obras DEBEN encabezar los candidatos antes de los resultados vectoriales genéricos.
    #    Incluye Fuzzy Matching con pg_trgm para tolerar errores ortográficos (ej: 'brad pit', 'ian mckelen', 'scorsece').
    # -------------------------------------------------------------------------
    matched_actor_ids: set[int] = set()

    # 0.0 Obras producidas en el país/locación ambientada:
    # Si el usuario busca historias ambientadas en un país o ciudad (ej: ambientada en Argentina o Buenos Aires),
    # incluir las mejores producciones de ese país (que naturalmente transcurren allí) como candidatas destacadas
    if is_setting_intent and detected_country:
        set_nat_q = select(Titulo).options(selectinload(Titulo.generos), selectinload(Titulo.actores))
        if isinstance(detected_country, list):
            set_nat_q = set_nat_q.where(Titulo.pais.in_(detected_country))
        else:
            set_nat_q = set_nat_q.where(Titulo.pais == detected_country)
        set_nat_q = apply_base_filters(set_nat_q)
        set_nat_res = await db.execute(set_nat_q.order_by(desc(Titulo.rating_unificado), desc(Titulo.popularidad)).limit(8))
        for t in set_nat_res.scalars().all():
            entity_titles[t.id] = t

    # A. Búsqueda exacta de actores y directores por bigramas (ej: "brad pitt", "ian mckellen")
    if valid_bigrams:
        for bg in valid_bigrams:
            # Director por nombre completo
            dir_bg_q = select(Titulo).options(selectinload(Titulo.generos), selectinload(Titulo.actores))
            dir_bg_q = apply_base_filters(dir_bg_q).where(Titulo.director.ilike(f"%{bg}%"))
            dir_bg_res = await db.execute(dir_bg_q.order_by(desc(Titulo.rating_unificado), desc(Titulo.popularidad)).limit(15))
            for t in dir_bg_res.scalars().all():
                entity_titles[t.id] = t

            # Actor por nombre completo
            act_res = await db.execute(select(Actor.id).where(Actor.nombre.ilike(f"%{bg}%")).limit(10))
            for aid in act_res.scalars().all():
                matched_actor_ids.add(aid)

            # Fuzzy Trigram para bigramas completos (ej: 'brad pit' -> 'Brad Pitt', 'ian mckelen' -> 'Ian McKellen')
            if is_postgres:
                try:
                    f_act = await db.execute(
                        text("SELECT id FROM actores WHERE similarity(nombre, :bg) >= 0.45 ORDER BY similarity(nombre, :bg) DESC LIMIT 5"),
                        {"bg": bg}
                    )
                    for r in f_act.all():
                        matched_actor_ids.add(r[0])

                    f_dir = await db.execute(
                        text("SELECT DISTINCT director FROM titulos WHERE director IS NOT NULL AND similarity(director, :bg) >= 0.45 LIMIT 3"),
                        {"bg": bg}
                    )
                    for r in f_dir.all():
                        d_q = select(Titulo).options(selectinload(Titulo.generos), selectinload(Titulo.actores))
                        d_q = apply_base_filters(d_q).where(Titulo.director == r[0])
                        d_res = await db.execute(d_q.order_by(desc(Titulo.rating_unificado), desc(Titulo.popularidad)).limit(15))
                        for t in d_res.scalars().all():
                            entity_titles[t.id] = t
                except Exception as e:
                    logger.debug(f"pg_trgm fuzzy matching ignorado en bigrama: {e}")

    # B. Búsqueda de actores y directores por términos individuales distintivos
    # Se ejecuta principalmente si no se identificó ya un actor o director por nombre compuesto (bigrama)
    if search_terms and not matched_actor_ids and not entity_titles:
        long_terms = [t for t in search_terms if len(t) >= 4]
        for t in long_terms:
            # Directores por término exacto
            dir_t_q = select(Titulo).options(selectinload(Titulo.generos), selectinload(Titulo.actores))
            dir_t_q = apply_base_filters(dir_t_q).where(Titulo.director.ilike(f"%{t}%"))
            dir_t_res = await db.execute(dir_t_q.order_by(desc(Titulo.rating_unificado), desc(Titulo.popularidad)).limit(15))
            for tit in dir_t_res.scalars().all():
                entity_titles[tit.id] = tit

            # Actores por término exacto
            act_t_res = await db.execute(select(Actor.id).where(Actor.nombre.ilike(f"%{t}%")).limit(10))
            for aid in act_t_res.scalars().all():
                matched_actor_ids.add(aid)

            # Fuzzy para directores y actores con errores ortográficos (ej: 'scorsece' -> 'Martin Scorsese')
            if is_postgres:
                try:
                    f_single_dir = await db.execute(
                        text("SELECT DISTINCT director FROM titulos WHERE director IS NOT NULL AND (similarity(director, :term) >= 0.3 OR director ILIKE :pat) LIMIT 3"),
                        {"term": t, "pat": f"%{t}%"}
                    )
                    for r in f_single_dir.all():
                        d_q = select(Titulo).options(selectinload(Titulo.generos), selectinload(Titulo.actores))
                        d_q = apply_base_filters(d_q).where(Titulo.director == r[0])
                        d_res = await db.execute(d_q.order_by(desc(Titulo.rating_unificado), desc(Titulo.popularidad)).limit(15))
                        for tit in d_res.scalars().all():
                            entity_titles[tit.id] = tit

                    if not matched_actor_ids:
                        f_single_act = await db.execute(
                            text("SELECT id FROM actores WHERE similarity(nombre, :term) >= 0.4 ORDER BY similarity(nombre, :term) DESC LIMIT 5"),
                            {"term": t}
                        )
                        for r in f_single_act.all():
                            matched_actor_ids.add(r[0])
                except Exception as e:
                    logger.debug(f"pg_trgm fuzzy matching ignorado en término: {e}")

    # C. Búsqueda de títulos por nombre directo (solo si no se detectó actor o director prioritario)
    if search_terms and not matched_actor_ids and not entity_titles:
        title_terms = [t for t in search_terms if len(t) >= 4]
        if title_terms:
            name_q = select(Titulo).options(selectinload(Titulo.generos), selectinload(Titulo.actores))
            name_q = apply_base_filters(name_q).where(or_(*[Titulo.nombre.ilike(f"%{t}%") for t in title_terms]))
            name_q = name_q.order_by(desc(Titulo.rating_unificado), desc(Titulo.popularidad)).limit(15)
            name_res = await db.execute(name_q)
            for tit in name_res.scalars().all():
                entity_titles[tit.id] = tit

    # C. Si encontramos actores coincidentes, cargar sus títulos con máxima prioridad
    if matched_actor_ids:
        act_titles_q = (
            select(Titulo)
            .options(selectinload(Titulo.generos), selectinload(Titulo.actores))
            .join(titulos_elenco, titulos_elenco.c.titulo_id == Titulo.id)
            .where(titulos_elenco.c.actor_id.in_(list(matched_actor_ids)))
        )
        act_titles_q = apply_base_filters(act_titles_q)
        act_titles_res = await db.execute(
            act_titles_q.order_by(desc(Titulo.rating_unificado), desc(Titulo.popularidad)).distinct().limit(20)
        )
        for t in act_titles_res.scalars().all():
            entity_titles[t.id] = t

    # -------------------------------------------------------------------------
    # 1. BÚSQUEDA SEMÁNTICA VECTORIAL CON PGVECTOR (RAG HÍBRIDO)
    # -------------------------------------------------------------------------
    if is_postgres and settings.GEMINI_API_KEY:
        try:
            from app.services.embedding_service import EmbeddingService
            emb_svc = EmbeddingService()
            user_vec = await emb_svc.get_embedding(search_prompt)
            if user_vec:
                vector_q = (
                    select(Titulo)
                    .options(selectinload(Titulo.generos), selectinload(Titulo.actores))
                    .where(Titulo.embedding.isnot(None))
                )
                vector_q = apply_base_filters(vector_q)
                # Exigir un piso razonable de votos para evitar registros con metadata vacía
                vector_q = vector_q.where(Titulo.vote_count_tmdb >= 25)
                # Ordenar por distancia coseno de pgvector
                vector_q = vector_q.order_by(Titulo.embedding.cosine_distance(user_vec).asc()).limit(25)
                v_res = await db.execute(vector_q)
                for t in v_res.scalars().all():
                    vector_titles[t.id] = t
        except Exception as e:
            logger.warning(f"Error en búsqueda semántica vectorial: {e}. Continuando con fallback léxico.")

    target_genres = list(detected_genres)
    # Solo recurrir a los géneros favoritos del usuario si no hubo géneros ni términos de búsqueda explícitos en el prompt
    if not target_genres and not search_terms and user_ctx and user_ctx.get("top_genres"):
        target_genres = user_ctx["top_genres"][:2]

    # -------------------------------------------------------------------------
    # 2. BÚSQUEDA TEMÁTICA COMBINADA O POR SINOPSIS (Términos expandidos bilingües)
    # -------------------------------------------------------------------------
    if target_genres and syn_search_words:
        expanded_genres = []
        for tg in target_genres:
            expanded_genres.extend(expand_genre_names(tg))
        theme_genre_q = (
            select(Titulo)
            .options(selectinload(Titulo.generos), selectinload(Titulo.actores))
            .join(titulos_generos, titulos_generos.c.titulo_id == Titulo.id)
            .join(Genero, Genero.id == titulos_generos.c.genero_id)
        )
        theme_genre_q = apply_base_filters(theme_genre_q)
        theme_genre_q = theme_genre_q.where(
            Genero.nombre.in_(expanded_genres),
            Titulo.vote_count_tmdb >= 80,
            or_(*[Titulo.sinopsis.ilike(f"%{w}%") for w in syn_search_words])
        )
        theme_genre_q = theme_genre_q.order_by(desc(Titulo.rating_unificado), desc(Titulo.popularidad)).distinct().limit(25)
        tg_res = await db.execute(theme_genre_q)
        for t in tg_res.scalars().all():
            theme_titles[t.id] = t
    elif syn_search_words:
        theme_syn_q = (
            select(Titulo)
            .options(selectinload(Titulo.generos), selectinload(Titulo.actores))
        )
        theme_syn_q = apply_base_filters(theme_syn_q)
        theme_syn_q = theme_syn_q.where(
            Titulo.vote_count_tmdb >= 80,
            or_(*[Titulo.sinopsis.ilike(f"%{w}%") for w in syn_search_words])
        )
        theme_syn_q = theme_syn_q.order_by(desc(Titulo.rating_unificado), desc(Titulo.popularidad)).limit(25)
        ts_res = await db.execute(theme_syn_q)
        for t in ts_res.scalars().all():
            theme_titles[t.id] = t

    # -------------------------------------------------------------------------
    # 3. FALLBACKS DE CALIDAD Y GÉNEROS (Para completar el cupo requerido)
    # -------------------------------------------------------------------------
    total_accumulated = len(entity_titles) + len(theme_titles) + len(vector_titles)

    # Géneros detectados
    if target_genres and total_accumulated < 25:
        expanded_genres = []
        for tg in target_genres:
            expanded_genres.extend(expand_genre_names(tg))
        g_q = (
            select(Titulo)
            .options(selectinload(Titulo.generos), selectinload(Titulo.actores))
            .join(titulos_generos, titulos_generos.c.titulo_id == Titulo.id)
            .join(Genero, Genero.id == titulos_generos.c.genero_id)
        )
        g_q = apply_base_filters(g_q)
        g_q = g_q.where(
            Genero.nombre.in_(expanded_genres),
            Titulo.vote_count_tmdb >= 150
        )
        g_q = g_q.order_by(desc(Titulo.rating_unificado), desc(Titulo.popularidad)).distinct().limit(20)
        g_res = await db.execute(g_q)
        for t in g_res.scalars().all():
            fallback_titles[t.id] = t

    # Obras exclusivamente vistas (only_watched) si es necesario complementar
    if only_watched and (total_accumulated + len(fallback_titles)) < 25:
        ow_q = select(Titulo).options(selectinload(Titulo.generos), selectinload(Titulo.actores))
        ow_q = apply_base_filters(ow_q)
        ow_q = ow_q.order_by(desc(Titulo.rating_unificado), desc(Titulo.popularidad)).limit(25)
        ow_res = await db.execute(ow_q)
        for t in ow_res.scalars().all():
            fallback_titles[t.id] = t

    # Relleno general diverso con obras aclamadas
    if (total_accumulated + len(fallback_titles)) < 20 and not only_watched:
        needed = 25 - (total_accumulated + len(fallback_titles))
        fill_q = select(Titulo).options(selectinload(Titulo.generos), selectinload(Titulo.actores))
        fill_q = apply_base_filters(fill_q)
        fill_q = fill_q.where(
            Titulo.vote_count_tmdb >= 150,
            Titulo.rating_unificado >= 7.5
        )
        fill_q = fill_q.order_by(func.random()).limit(needed)
        fill_res = await db.execute(fill_q)
        for t in fill_res.scalars().all():
            fallback_titles[t.id] = t

    # -------------------------------------------------------------------------
    # 4. ENSAMBLADO JERÁRQUICO FINAL DE CANDIDATOS
    #    1º Entidades Directas (Actores / Directores / Títulos explícitos o fuzzy)
    #    2º Coincidencias Temáticas / Sinopsis
    #    3º Similitud Semántica Vectorial (pgvector)
    #    4º Fallback de Género y Aclamadas
    # -------------------------------------------------------------------------
    max_candidates = getattr(settings, "RECOMMENDATION_CANDIDATES_LIMIT", 20)
    ordered_titles: dict[int, Titulo] = {}

    for t in entity_titles.values():
        if len(ordered_titles) >= max_candidates:
            break
        ordered_titles[t.id] = t

    for t in theme_titles.values():
        if len(ordered_titles) >= max_candidates:
            break
        ordered_titles[t.id] = t

    for t in vector_titles.values():
        if len(ordered_titles) >= max_candidates:
            break
        ordered_titles[t.id] = t

    for t in fallback_titles.values():
        if len(ordered_titles) >= max_candidates:
            break
        ordered_titles[t.id] = t

    candidate_titles = list(ordered_titles.values())[:max_candidates]

    # Buscar fragmentos de reseñas locales para los candidatos
    cand_ids = [t.id for t in candidate_titles]
    snippets_map = {}
    if cand_ids:
        rev_res = await db.execute(
            select(Resena.titulo_id, Resena.texto)
            .where(
                Resena.titulo_id.in_(cand_ids),
                Resena.texto.isnot(None),
                func.length(Resena.texto) >= 20
            )
            .order_by(desc(Resena.id))
        )
        for tid, cont in rev_res.all():
            if tid not in snippets_map and cont:
                snippets_map[tid] = cont[:140] + ("..." if len(cont) > 140 else "")

    # Mapear a estructura compacta para el LLM y motor heurístico
    formatted_candidates = []
    for t in candidate_titles:
        g_names = [g.nombre for g in t.generos]
        actor_names = [a.nombre for a in t.actores[:3]] if hasattr(t, "actores") and t.actores else []
        short_synopsis = (t.sinopsis[:160] + "...") if t.sinopsis and len(t.sinopsis) > 160 else (t.sinopsis or "")
        formatted_candidates.append({
            "id": t.id,
            "nombre": t.nombre,
            "tipo": t.tipo,
            "anio": t.anio_estreno,
            "pais": t.pais,
            "idioma_original": t.idioma_original,
            "generos": g_names,
            "director": t.director,
            "actores": actor_names,
            "vote_average": round(t.rating_unificado or t.vote_average_tmdb, 1),
            "vote_count": t.vote_count_tmdb,
            "sinopsis_corta": short_synopsis,
            "community_review_snippet": snippets_map.get(t.id),
            "is_watched": (t.id in watched_ids)
        })

    return formatted_candidates, user_ctx


async def get_hydrated_recommendations(
    db: AsyncSession,
    title_ids: list[int],
    usuario_id: Optional[int] = None
) -> list[TitleCardResponse]:
    """Obtiene y construye las TitleCards completas e interactivas para una lista de IDs recomendados."""
    if not title_ids:
        return []

    q = (
        select(Titulo)
        .options(selectinload(Titulo.generos), selectinload(Titulo.temporadas))
        .where(Titulo.id.in_(title_ids))
    )
    res = await db.execute(q)
    titles_map = {t.id: t for t in res.scalars().all()}

    user_states_map = {}
    user_ratings_map = {}
    if usuario_id:
        st_res = await db.execute(
            select(EstadoUsuarioTitulo).where(
                EstadoUsuarioTitulo.usuario_id == usuario_id,
                EstadoUsuarioTitulo.titulo_id.in_(title_ids)
            )
        )
        user_states_map = {st.titulo_id: st for st in st_res.scalars().all()}

        r_res = await db.execute(
            select(Resena.titulo_id, Resena.puntaje).where(
                Resena.usuario_id == usuario_id,
                Resena.titulo_id.in_(title_ids),
                Resena.puntaje.isnot(None)
            )
        )
        for r_tid, r_score in r_res.all():
            user_ratings_map[r_tid] = r_score

    cards = []
    for tid in title_ids:
        t = titles_map.get(tid)
        if t:
            cards.append(
                _build_title_card(
                    t,
                    user_states_map.get(t.id),
                    user_rating=user_ratings_map.get(t.id)
                )
            )
    return cards

