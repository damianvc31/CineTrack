from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_optional_current_user, get_optional_user_id
from app.db.session import get_db
from app.models.usuario import Usuario
from app.schemas.catalog import (
    CountryItem,
    GenreResponse,
    HomeSectionsResponse,
    LanguageItem,
    ReviewCreate,
    ReviewResponse,
    TitleDetailResponse,
    TitleListResponse,
)
from app.services import catalog_service
from app.services.catalog_service import EXCLUDED_GENRE_NAMES
from app.models.genero import Genero
from sqlalchemy import select

router = APIRouter(tags=["Catálogo y Títulos"])


@router.get("/home", response_model=HomeSectionsResponse)
async def get_home(
    tipo: Optional[str] = Query(default=None, description="Filtro opcional: 'movie' o 'tv'"),
    user_id: Optional[int] = Depends(get_optional_user_id),
    db: AsyncSession = Depends(get_db)
) -> HomeSectionsResponse:
    """Retorna las secciones curadas de la Home (Trending, New Releases, Classics y por Género)."""
    return await catalog_service.get_home_sections(db, tipo=tipo, usuario_id=user_id)


@router.get("/titles", response_model=TitleListResponse)
async def list_titles(
    tipo: Optional[str] = Query(default=None, description="Filtrar por tipo: 'movie' o 'tv'"),
    genero_id: Optional[int] = Query(default=None, description="Filtrar por ID numérico de género"),
    genero: Optional[str] = Query(default=None, description="Filtrar por nombre de género"),
    generos: Optional[str] = Query(default=None, description="Filtrar por uno o más géneros separados por coma (ej: 'Action,Comedy')"),
    genre_op: str = Query(default="or", pattern="^(or|and)$", description="Operador lógico para múltiples géneros: 'or' (cualquiera) o 'and' (todos)"),
    actor_id: Optional[int] = Query(default=None, description="Filtrar por ID numérico de actor"),
    actor: Optional[str] = Query(default=None, description="Filtrar por nombre de actor (ej: 'DiCaprio', 'Tom Cruise')"),
    pais: Optional[str] = Query(default=None, description="Filtrar por país de origen (código ISO o lista separada por coma)"),
    paises: Optional[str] = Query(default=None, description="Filtrar por uno o más países de origen separados por coma (ej: 'US,JP,KR')"),
    idioma: Optional[str] = Query(default=None, description="Filtrar por idioma original (código ISO o lista separada por coma)"),
    idiomas: Optional[str] = Query(default=None, description="Filtrar por uno o más idiomas originales separados por coma (ej: 'en,ja,es')"),
    section: Optional[str] = Query(default=None, description="Filtrar por sección curada: 'new_releases', 'trending', 'classics', 'top_rated'"),
    q: Optional[str] = Query(default=None, description="Buscar por nombre, director, guionista o actor del elenco"),
    sort_by: str = Query(default="popularity", description="Criterio de orden: 'popularity', 'rating', 'release_date', 'title'"),
    order: str = Query(default="desc", pattern="^(asc|desc)$", description="Dirección del orden: 'desc' o 'asc'"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    user_id: Optional[int] = Depends(get_optional_user_id),
    db: AsyncSession = Depends(get_db)
) -> TitleListResponse:
    """Búsqueda y listado paginado de títulos con filtros multidimensionales y secciones."""
    return await catalog_service.get_titles(
        db,
        tipo=tipo,
        genero_id=genero_id,
        genero=genero,
        generos=generos,
        genre_op=genre_op,
        actor_id=actor_id,
        actor=actor,
        pais=pais,
        paises=paises,
        idioma=idioma,
        idiomas=idiomas,
        section=section,
        q=q,
        sort_by=sort_by,
        order=order,
        page=page,
        page_size=page_size,
        usuario_id=user_id
    )


@router.get("/titles/{title_id}", response_model=TitleDetailResponse)
async def get_title(
    title_id: int,
    current_user: Optional[Usuario] = Depends(get_optional_current_user),
    db: AsyncSession = Depends(get_db)
) -> TitleDetailResponse:
    """Retorna el detalle completo de un título con temporadas, episodios y elenco."""
    user_id = current_user.id if current_user else None
    detail = await catalog_service.get_title_detail(db, titulo_id=title_id, usuario_id=user_id)
    if not detail:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Título no encontrado.")
    return detail


@router.get("/titles/{title_id}/reviews", response_model=list[ReviewResponse])
async def list_reviews(
    title_id: int,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=50),
    db: AsyncSession = Depends(get_db)
) -> list[ReviewResponse]:
    """Retorna las reseñas públicas de TMDB y de la comunidad para un título."""
    return await catalog_service.get_title_reviews(db, titulo_id=title_id, page=page, page_size=page_size)


@router.post("/titles/{title_id}/reviews", response_model=ReviewResponse, status_code=status.HTTP_201_CREATED)
async def post_review(
    title_id: int,
    review_in: ReviewCreate,
    current_user: Usuario = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> ReviewResponse:
    """Publica o actualiza una reseña personal con puntaje (1-10) y texto."""
    return await catalog_service.create_user_review(
        db,
        titulo_id=title_id,
        usuario_id=current_user.id,
        review_in=review_in
    )


@router.delete("/titles/{title_id}/reviews", status_code=status.HTTP_200_OK)
async def delete_review(
    title_id: int,
    current_user: Usuario = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Elimina la reseña propia del usuario para el título especificado y recalcula ratings."""
    deleted = await catalog_service.delete_user_review(db, titulo_id=title_id, usuario_id=current_user.id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No se encontró una reseña del usuario para este título."
        )
    return {"message": "Reseña eliminada correctamente."}



@router.get("/genres", response_model=list[GenreResponse])
async def list_genres(
    db: AsyncSession = Depends(get_db)
) -> list[GenreResponse]:
    """Retorna la lista de géneros canónicos registrados en el catálogo (excluyendo duplas compuestas)."""
    res = await db.execute(select(Genero).order_by(Genero.nombre.asc()))
    generos = res.scalars().all()
    return [
        GenreResponse(id=g.id, nombre=g.nombre)
        for g in generos
        if g.nombre not in EXCLUDED_GENRE_NAMES
    ]


@router.get("/countries", response_model=list[CountryItem])
async def list_countries(
    db: AsyncSession = Depends(get_db)
) -> list[CountryItem]:
    """Retorna la lista de países disponibles en el catálogo con código y conteo de títulos."""
    return await catalog_service.get_available_countries(db)


@router.get("/languages", response_model=list[LanguageItem])
async def list_languages(
    db: AsyncSession = Depends(get_db)
) -> list[LanguageItem]:
    """Retorna la lista de idiomas originales disponibles en el catálogo con código y conteo de títulos."""
    return await catalog_service.get_available_languages(db)
