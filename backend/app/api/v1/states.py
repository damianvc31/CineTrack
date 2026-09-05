from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.usuario import Usuario
from app.schemas.state import (
    EpisodeWatchResponse,
    FavoriteToggleResponse,
    StateChangeResponse,
    TitleUserStateResponse,
)
from app.services import state_service

router = APIRouter(tags=["Estados de Título y Episodios"])


@router.post("/titles/{title_id}/favorite", response_model=FavoriteToggleResponse)
async def toggle_title_favorite(
    title_id: int,
    current_user: Usuario = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> FavoriteToggleResponse:
    """Alterna el favorito (♥) del título para el usuario autenticado."""
    return await state_service.toggle_favorite(db, usuario_id=current_user.id, titulo_id=title_id)


@router.post("/titles/{title_id}/watchlist", response_model=StateChangeResponse)
async def toggle_title_watchlist(
    title_id: int,
    current_user: Usuario = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> StateChangeResponse:
    """Alterna el estado Watchlist (🔖). Error 400 si el título está en Vista o Siguiendo."""
    return await state_service.toggle_watchlist(db, usuario_id=current_user.id, titulo_id=title_id)


@router.post("/titles/{title_id}/watched", response_model=StateChangeResponse)
async def toggle_title_watched(
    title_id: int,
    current_user: Usuario = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> StateChangeResponse:
    """Marca o desmarca el título completo como Visto (👁). En series limpia episodios si se desmarca."""
    return await state_service.toggle_watched(db, usuario_id=current_user.id, titulo_id=title_id)


@router.post("/titles/{title_id}/unfollow", response_model=StateChangeResponse)
async def unfollow_series(
    title_id: int,
    current_user: Usuario = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> StateChangeResponse:
    """Abandona una serie en seguimiento (❌), conservando los episodios vistos."""
    return await state_service.abandon_series(db, usuario_id=current_user.id, titulo_id=title_id)


@router.get("/titles/{title_id}/user-state", response_model=TitleUserStateResponse)
async def get_title_state(
    title_id: int,
    current_user: Usuario = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> TitleUserStateResponse:
    """Retorna el estado de tracking y progreso del usuario sobre el título."""
    return await state_service.get_title_user_state(db, usuario_id=current_user.id, titulo_id=title_id)


@router.post("/episodes/{episode_id}/watch", response_model=EpisodeWatchResponse)
async def toggle_episode_watched(
    episode_id: int,
    current_user: Usuario = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> EpisodeWatchResponse:
    """Marca o desmarca un episodio individual como visto y recalcula el estado de la serie."""
    return await state_service.toggle_episode_watched(db, usuario_id=current_user.id, episodio_id=episode_id)
