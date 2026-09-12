from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.usuario import Usuario
from app.schemas.catalog import (
    UnreviewedWatchedResponse,
    UserLibraryResponse,
    UserReviewsListResponse,
    UserStatsResponse,
)
from app.services import catalog_service

router = APIRouter(prefix="/users", tags=["Perfil, Biblioteca y Estadísticas de Usuario"])


@router.get("/me/library", response_model=UserLibraryResponse)
async def get_my_library(
    current_user: Usuario = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> UserLibraryResponse:
    """Retorna las listas de títulos categorizados por estado para el usuario (Following, Favorites, Watchlist, Recently Watched)."""
    return await catalog_service.get_user_library(db, usuario_id=current_user.id)


@router.get("/me/stats", response_model=UserStatsResponse)
async def get_my_stats(
    current_user: Usuario = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> UserStatsResponse:
    """Calcula y retorna todas las métricas estadísticas del perfil (horas, conteos, top 5 y distribución de géneros)."""
    return await catalog_service.get_user_stats(db, usuario_id=current_user.id)


@router.get("/me/reviews", response_model=UserReviewsListResponse)
async def get_my_reviews(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=50),
    current_user: Usuario = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> UserReviewsListResponse:
    """Retorna todas las reseñas escritas por el usuario autenticado con datos del título."""
    return await catalog_service.get_user_reviews(
        db,
        usuario_id=current_user.id,
        page=page,
        page_size=page_size
    )


@router.get("/me/unreviewed-watched", response_model=UnreviewedWatchedResponse)
async def get_my_unreviewed_watched(
    limit: int = Query(default=50, ge=1, le=100),
    current_user: Usuario = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> UnreviewedWatchedResponse:
    """Retorna los títulos marcados como 'vista' por el usuario que aún no tienen reseña suya."""
    return await catalog_service.get_user_unreviewed_watched_titles(
        db,
        usuario_id=current_user.id,
        limit=limit
    )
