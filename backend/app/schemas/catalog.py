from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class GenreResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nombre: str


class CountryItem(BaseModel):
    code: str
    count: int


class LanguageItem(BaseModel):
    code: str
    count: int


class CastMemberResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    actor_id: int
    tmdb_id: int | None = None
    nombre: str
    foto_url: str | None = None
    personaje: str | None = None
    orden: int = 0


class EpisodeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    temporada_id: int
    numero: int
    nombre: str
    fecha_estreno: date | None = None
    duracion: int | None = None
    visto: bool = False


class SeasonResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    titulo_id: int
    numero: int
    sinopsis: str | None = None
    fecha_estreno: date | None = None
    cantidad_episodios: int = 0
    episodios_vistos: int = 0
    temporada_vista: bool = False
    episodios: list[EpisodeResponse] = Field(default_factory=list)


class SeasonProgressResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    numero: int
    total_episodios: int
    episodios_vistos: int
    estado: Literal["completed", "in_progress", "unwatched"]


class TitleCardResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    tmdb_id: int
    tipo: Literal["movie", "tv"]
    nombre: str
    sinopsis: str | None = None
    portada_url: str | None = None
    fecha_estreno: date | None = None
    fecha_fin: date | None = None
    anio_estreno: int | None = None
    anio_fin: int | None = None
    duracion: int | None = None
    popularidad: float = 0.0
    popularidad_percentil: float = 0.0
    vote_average_tmdb: float = 0.0
    vote_count_tmdb: int = 0
    rating_unificado: float = 0.0
    generos: list[GenreResponse] = Field(default_factory=list)
    total_seasons: int | None = None
    user_favorito: bool = False
    user_estado: str | None = None
    pais: str | None = None
    idioma_original: str | None = None
    seasons_progress: list[SeasonProgressResponse] | None = None
    following_status_text: str | None = None
    user_rating: float | None = None


class TitleDetailResponse(TitleCardResponse):
    model_config = ConfigDict(from_attributes=True)

    director: str | None = None
    guionista: str | None = None
    pais: str | None = None
    idioma_original: str | None = None
    status_tmdb: str | None = None
    proximo_episodio_fecha: date | None = None
    elenco: list[CastMemberResponse] = Field(default_factory=list)
    temporadas: list[SeasonResponse] = Field(default_factory=list)


class ReviewResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    titulo_id: int
    usuario_id: int | None = None
    nombre_usuario: str | None = None
    avatar_url: str | None = None
    autor_tmdb: str | None = None
    puntaje: float | None = None
    texto: str
    fecha: datetime


class ReviewCreate(BaseModel):
    puntaje: float | None = Field(default=None, ge=0.0, le=10.0, description="Calificación opcional de 0.0 a 10.0 en saltos de 0.5")
    texto: str = Field(..., min_length=5, max_length=5000, description="Texto de la reseña")

    @field_validator("puntaje")
    @classmethod
    def validate_half_steps(cls, v: float | None) -> float | None:
        if v is None:
            return None
        if not abs(v * 2 - round(v * 2)) < 1e-6:
            raise ValueError("El puntaje debe ser un número entre 0.0 y 10.0 en saltos de 0.5 (ej. 7.0, 7.5, 8.0).")
        return round(v * 2) / 2


class UserReviewItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    titulo_id: int
    titulo_nombre: str
    titulo_tipo: str
    titulo_portada_url: str | None = None
    titulo_fecha_estreno: date | None = None
    puntaje: float | None = None
    texto: str
    fecha: datetime


class UserReviewsListResponse(BaseModel):
    items: list[UserReviewItemResponse]
    total: int
    page: int
    page_size: int


class UnreviewedWatchedResponse(BaseModel):
    items: list[TitleCardResponse]
    total: int


class TitleListResponse(BaseModel):
    items: list[TitleCardResponse]
    total: int
    page: int
    page_size: int


class HomeSectionsResponse(BaseModel):
    trending: list[TitleCardResponse]
    new_releases: list[TitleCardResponse]
    classics: list[TitleCardResponse] = Field(default_factory=list)
    top_rated: list[TitleCardResponse] = Field(default_factory=list)
    by_genre: dict[str, list[TitleCardResponse]] = Field(default_factory=dict)
    others: list[TitleCardResponse] = Field(default_factory=list)


class UserLibraryResponse(BaseModel):
    following: list[TitleCardResponse] = Field(default_factory=list)
    favorites: list[TitleCardResponse] = Field(default_factory=list)
    watchlist: list[TitleCardResponse] = Field(default_factory=list)
    recently_watched: list[TitleCardResponse] = Field(default_factory=list)


class TopTitleStat(BaseModel):
    id: int
    nombre: str
    tipo: str
    anio_estreno: int | None = None
    anio_fin: int | None = None
    total_seasons: int | None = None
    portada_url: str | None = None
    metric_value: float


class UserStatsResponse(BaseModel):
    total_hours: float
    movie_hours: float
    tv_hours: float
    movies_watched_count: int
    avg_movies_per_week: float = 0.0
    series_watched_count: int
    seasons_completed_count: int = 0
    episodes_watched_count: int
    top_by_popularity: list[TopTitleStat] = Field(default_factory=list)
    top_by_community_rating: list[TopTitleStat] = Field(default_factory=list)
    top_by_user_rating: list[TopTitleStat] = Field(default_factory=list)
    genres_distribution: dict[str, int] = Field(default_factory=dict)
    window: str = "all_time"
