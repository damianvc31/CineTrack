from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.security import hash_password, verify_password
from app.db.session import get_db
from app.models.usuario import Usuario
from app.schemas.auth import PasswordChangeRequest, UserResponse, UserUpdate
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


@router.patch("/me", response_model=UserResponse)
async def update_my_profile(
    payload: UserUpdate,
    current_user: Usuario = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> UserResponse:
    """Actualiza la información del perfil del usuario (bio, país, ciudad, avatar). No altera el nombre de usuario."""
    if payload.pais is not None:
        current_user.pais = payload.pais.strip() or None
    if payload.ciudad is not None:
        current_user.ciudad = payload.ciudad.strip() or None
    if payload.descripcion is not None:
        current_user.descripcion = payload.descripcion.strip() or None
    if payload.avatar_url is not None:
        current_user.avatar_url = payload.avatar_url.strip() or None

    await db.commit()
    await db.refresh(current_user)
    return current_user


@router.post("/me/change-password")
async def change_my_password(
    payload: PasswordChangeRequest,
    current_user: Usuario = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Cambia la contraseña del usuario tras verificar la contraseña actual."""
    if not verify_password(payload.current_password, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La contraseña actual es incorrecta."
        )

    current_user.password_hash = hash_password(payload.new_password)
    await db.commit()
    return {"message": "Contraseña actualizada exitosamente."}
