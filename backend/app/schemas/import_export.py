from typing import Optional, List, Literal
from datetime import date
from pydantic import BaseModel, Field, ConfigDict


class ElencoImportSchema(BaseModel):
    nombre: str
    personaje: Optional[str] = None
    foto_path: Optional[str] = None


class EpisodioImportSchema(BaseModel):
    numero_episodio: int
    titulo: str
    sinopsis: Optional[str] = None
    duracion_min: Optional[int] = None
    fecha_estreno: Optional[date] = None


class TemporadaImportSchema(BaseModel):
    numero_temporada: int
    nombre: Optional[str] = None
    sinopsis: Optional[str] = None
    poster_path: Optional[str] = None
    episodios: List[EpisodioImportSchema] = Field(default_factory=list)


class TituloManualImportSchema(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id_tmdb: Optional[int] = None
    titulo: str
    tipo: Literal["movie", "tv"]
    sinopsis: Optional[str] = None
    poster_path: Optional[str] = None
    backdrop_path: Optional[str] = None
    fecha_estreno: Optional[date] = None
    duracion_min: Optional[int] = None
    director: Optional[str] = None
    guionista: Optional[str] = None
    pais_origen: Optional[str] = None
    popularidad: Optional[float] = 0.0
    promedio_votos: Optional[float] = 0.0
    cantidad_votos: Optional[int] = 0
    estado_serie: Optional[str] = None
    total_temporadas: Optional[int] = 0
    total_episodios: Optional[int] = 0
    generos: List[str] = Field(default_factory=list)
    elenco: List[ElencoImportSchema] = Field(default_factory=list)
    temporadas: List[TemporadaImportSchema] = Field(default_factory=list)
