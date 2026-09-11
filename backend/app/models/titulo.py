from datetime import date
from typing import TYPE_CHECKING
from sqlalchemy import Date, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.actor import titulos_elenco
from app.models.genero import titulos_generos

if TYPE_CHECKING:
    from app.models.actor import Actor, TituloElenco
    from app.models.estado import EstadoUsuarioTitulo
    from app.models.genero import Genero
    from app.models.resena import Resena
    from app.models.temporada import Temporada


class Titulo(Base):
    __tablename__ = "titulos"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    tmdb_id: Mapped[int] = mapped_column(Integer, unique=True, index=True, nullable=False)
    tipo: Mapped[str] = mapped_column(String(10), index=True, nullable=False)  # 'movie' | 'tv'
    nombre: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    sinopsis: Mapped[str | None] = mapped_column(Text, nullable=True)
    portada_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    anio_estreno: Mapped[int | None] = mapped_column(Integer, index=True, nullable=True)
    anio_fin: Mapped[int | None] = mapped_column(Integer, nullable=True)
    duracion: Mapped[int | None] = mapped_column(Integer, nullable=True)  # solo peliculas (minutos)
    director: Mapped[str | None] = mapped_column(String(150), index=True, nullable=True)
    guionista: Mapped[str | None] = mapped_column(String(150), index=True, nullable=True)
    pais: Mapped[str | None] = mapped_column(String(100), nullable=True)
    idioma_original: Mapped[str | None] = mapped_column(String(20), nullable=True)
    popularidad: Mapped[float] = mapped_column(Float, default=0.0, index=True, nullable=False)
    popularidad_percentil: Mapped[float] = mapped_column(Float, default=0.0, index=True, nullable=False)
    vote_average_tmdb: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    vote_count_tmdb: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    rating_unificado: Mapped[float] = mapped_column(Float, default=0.0, index=True, nullable=False)
    status_tmdb: Mapped[str | None] = mapped_column(String(50), nullable=True)  # Ended, Returning Series, Canceled
    proximo_episodio_fecha: Mapped[date | None] = mapped_column(Date, nullable=True)

    # Relaciones Muchos a Muchos
    generos: Mapped[list["Genero"]] = relationship(
        secondary=titulos_generos,
        back_populates="titulos"
    )
    actores: Mapped[list["Actor"]] = relationship(
        secondary=titulos_elenco,
        back_populates="titulos",
        overlaps="elenco,participaciones,titulo,actor"
    )
    elenco: Mapped[list["TituloElenco"]] = relationship(
        back_populates="titulo",
        cascade="all, delete-orphan",
        order_by="TituloElenco.orden",
        overlaps="actores,titulos"
    )

    # Relaciones Uno a Muchos
    temporadas: Mapped[list["Temporada"]] = relationship(
        back_populates="titulo",
        cascade="all, delete-orphan",
        order_by="Temporada.numero"
    )
    estados: Mapped[list["EstadoUsuarioTitulo"]] = relationship(
        back_populates="titulo",
        cascade="all, delete-orphan"
    )
    resenas: Mapped[list["Resena"]] = relationship(
        back_populates="titulo",
        cascade="all, delete-orphan"
    )
