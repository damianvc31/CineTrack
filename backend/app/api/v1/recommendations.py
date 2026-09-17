from typing import Optional
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, get_optional_current_user
from app.models.usuario import Usuario
from app.schemas.recommendations import RecommendationRequest, RecommendationResponse
from app.services import catalog_service
from app.services.ai_recommender_service import ai_recommender_service

router = APIRouter()


@router.post("", response_model=RecommendationResponse)
async def get_recommendations(
    request: RecommendationRequest,
    current_user: Optional[Usuario] = Depends(get_optional_current_user),
    db: AsyncSession = Depends(get_db)
) -> RecommendationResponse:
    """Genera recomendaciones inteligentes asistidas por IA basándose en el prompt del usuario y su perfil."""
    usuario_id = current_user.id if current_user else None

    # 1. Obtener candidatos relevantes del catálogo local y contexto del usuario
    candidates, user_ctx = await catalog_service.get_recommendation_candidates(
        db,
        prompt=request.prompt,
        usuario_id=usuario_id,
        tipo_filtro=request.tipo_filtro or "all"
    )

    # 2. Invocar el servicio de IA (Gemini con fallback a Groq / heurístico)
    ai_response = await ai_recommender_service.get_recommendation(
        prompt=request.prompt,
        user_context=user_ctx,
        candidates=candidates,
        language=request.language or "es"
    )

    # 3. Si se generaron recomendaciones, hidratar las TitleCard completas
    if ai_response.status == "recommended" and ai_response.recommendations:
        title_ids = [r.title_id for r in ai_response.recommendations]
        hydrated_cards = await catalog_service.get_hydrated_recommendations(
            db,
            title_ids=title_ids,
            usuario_id=usuario_id
        )
        cards_map = {c.id: c for c in hydrated_cards}

        # Vincular cada card a su respectiva justificación preservando el orden
        for item in ai_response.recommendations:
            item.title = cards_map.get(item.title_id)

        # Filtrar si alguna card no se pudo hidratar
        ai_response.recommendations = [r for r in ai_response.recommendations if r.title is not None]

    return ai_response
