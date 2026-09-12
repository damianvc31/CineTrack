from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_optional_current_user
from app.db.session import get_db
from app.models.usuario import Usuario
from app.schemas.catalog import (
    GenreResponse,
    HomeSectionsResponse,
    ReviewCreate,
    ReviewResponse,
    TitleDetailResponse,
    TitleListResponse,
)
from app.services import catalog_service
from app.models.genero import Genero
from sqlalchemy import select

router = APIRouter(tags=["Catálogo y Títulos"])


@router.get("/home", response_model=HomeSectionsResponse)
async def get_home(
    tipo: Optional[str] = Query(default=None, description="Filtro opcional: 'movie' o 'tv'"),
    current_user: Optional[Usuario] = Depends(get_optional_current_user),
    db: AsyncSession = Depends(get_db)
) -> HomeSectionsResponse:
    """Retorna las secciones curadas de la Home (Trending, New Releases, Classics y por Género)."""
    user_id = current_user.id if current_user else None
    return await catalog_service.get_home_sections(db, tipo=tipo, usuario_id=user_id)


@router.get("/titles", response_model=TitleListResponse)
async def list_titles(
    tipo: Optional[str] = Query(default=None, description="Filtrar por tipo: 'movie' o 'tv'"),
    genero_id: Optional[int] = Query(default=None, description="Filtrar por ID de género"),
    q: Optional[str] = Query(default=None, description="Buscar por nombre, director o guionista"),
    sort_by: str = Query(default="popularity", description="Orden: 'popularity', 'rating', 'newest', 'classics'"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    current_user: Optional[Usuario] = Depends(get_optional_current_user),
    db: AsyncSession = Depends(get_db)
) -> TitleListResponse:
    """Búsqueda y listado paginado de títulos con filtros."""
    user_id = current_user.id if current_user else None
    return await catalog_service.get_titles(
        db,
        tipo=tipo,
        genero_id=genero_id,
        q=q,
        sort_by=sort_by,
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


@router.get("/genres", response_model=list[GenreResponse])
async def list_genres(
    db: AsyncSession = Depends(get_db)
) -> list[GenreResponse]:
    """Retorna la lista completa de géneros registrados en el catálogo."""
    res = await db.execute(select(Genero).order_by(Genero.nombre.asc()))
    generos = res.scalars().all()
    return [GenreResponse(id=g.id, nombre=g.nombre) for g in generos]
