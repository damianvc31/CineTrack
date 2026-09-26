from typing import Literal, Optional
from pydantic import BaseModel, Field

from app.core.config import VarietyLevel
from app.schemas.catalog import TitleCardResponse


class ClarificationContext(BaseModel):
    previous_prompt: str
    assistant_message: Optional[str] = None
    suggestions: Optional[list[str]] = Field(default_factory=list)


class RecommendationRequest(BaseModel):
    prompt: str = Field(
        ...,
        min_length=1,
        max_length=1000,
        description="Prompt o consulta en lenguaje natural del usuario solicitando recomendaciones"
    )
    tipo_filtro: Optional[Literal["all", "movie", "tv"]] = Field(
        default="all",
        description="Filtro opcional por tipo: 'all' (ambos), 'movie' o 'tv'"
    )
    language: Optional[Literal["es", "en"]] = Field(
        default="es",
        description="Idioma preferido de respuesta ('es' o 'en')"
    )
    clarification_context: Optional[ClarificationContext] = Field(
        default=None,
        description="Contexto previo si el usuario está respondiendo a una solicitud de aclaración del asistente"
    )
    variety_level: Optional[VarietyLevel] = Field(
        default=None,
        description="Nivel opcional de variedad / factor sorpresa ('VERY_LOW', 'LOW', 'MEDIUM', 'HIGH', 'VERY_HIGH')"
    )


class RecommendationItem(BaseModel):
    title_id: int
    reason: str
    title: Optional[TitleCardResponse] = None


class RecommendationResponse(BaseModel):
    status: Literal["recommended", "clarification_needed"]
    message: str
    recommendations: list[RecommendationItem] = Field(default_factory=list)
    clarification_suggestions: list[str] = Field(default_factory=list)
    provider_used: str = "gemini"
    model_used: Optional[str] = None
    variety_level: Optional[VarietyLevel] = None


class CandidateTitle(BaseModel):
    id: int
    nombre: str
    tipo: str
    anio: Optional[int] = None
    pais: Optional[str] = None
    idioma_original: Optional[str] = None
    generos: list[str] = Field(default_factory=list)
    director: Optional[str] = None
    vote_average: float = 0.0
    vote_count: int = 0
    sinopsis_corta: str = ""
    community_review_snippet: Optional[str] = None
