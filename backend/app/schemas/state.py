from datetime import datetime
from pydantic import BaseModel, ConfigDict


class TitleUserStateResponse(BaseModel):
    titulo_id: int
    tipo: str  # 'movie' | 'tv'
    favorito: bool
    fecha_favorito: datetime | None = None
    estado: str | None = None  # 'watchlist' | 'siguiendo' | 'vista' | None
    fecha_estado: datetime | None = None
    total_episodios: int = 0
    episodios_vistos: int = 0
    porcentaje_progreso: float = 0.0

    model_config = ConfigDict(from_attributes=True)


class EpisodeWatchResponse(BaseModel):
    episodio_id: int
    titulo_id: int
    visto: bool
    fecha_visto: datetime | None = None
    nuevo_estado_serie: str | None = None
    episodios_vistos_serie: int
    total_episodios_serie: int
    porcentaje_progreso: float


class FavoriteToggleResponse(BaseModel):
    titulo_id: int
    favorito: bool
    fecha_favorito: datetime | None = None


class StateChangeResponse(BaseModel):
    titulo_id: int
    nuevo_estado: str | None = None
    fecha_estado: datetime | None = None
    mensaje: str
