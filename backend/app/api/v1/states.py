from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.usuario import Usuario
from app.schemas.state import (
    EpisodeWatchResponse,
    FavoriteToggleResponse,
    SeasonWatchResponse,
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
    """Marca o desmarca un episodio individual como visto por ID directo y recalcula el estado de la serie."""
    return await state_service.toggle_episode_watched(db, usuario_id=current_user.id, episodio_id=episode_id)


@router.post("/titles/{title_id}/seasons/{season_number}/episodes/{episode_number}/watch", response_model=EpisodeWatchResponse)
async def toggle_episode_by_season_episode(
    title_id: int,
    season_number: int,
    episode_number: int,
    current_user: Usuario = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> EpisodeWatchResponse:
    """Marca o desmarca un episodio como visto usando números semánticos de temporada y episodio (ej. S01E02)."""
    return await state_service.toggle_episode_by_number(
        db,
        usuario_id=current_user.id,
        titulo_id=title_id,
        season_number=season_number,
        episode_number=episode_number
    )


@router.post("/seasons/{season_id}/watch", response_model=SeasonWatchResponse)
async def toggle_season_watched_by_id(
    season_id: int,
    current_user: Usuario = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> SeasonWatchResponse:
    """Marca o desmarca una temporada completa como vista por ID directo."""
    return await state_service.toggle_season_watched(db, usuario_id=current_user.id, temporada_id=season_id)


@router.post("/titles/{title_id}/seasons/{season_number}/watch", response_model=SeasonWatchResponse)
async def toggle_season_watched_by_number(
    title_id: int,
    season_number: int,
    current_user: Usuario = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> SeasonWatchResponse:
    """Marca o desmarca una temporada completa como vista usando el título y número de temporada (ej. Temporada 1)."""
    return await state_service.toggle_season_by_number(
        db,
        usuario_id=current_user.id,
        titulo_id=title_id,
        season_number=season_number
    )
