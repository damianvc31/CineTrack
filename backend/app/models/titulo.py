from datetime import date
from typing import TYPE_CHECKING
from sqlalchemy import Date, Float, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.actor import titulos_elenco
from app.models.genero import titulos_generos
try:
    from pgvector.sqlalchemy import Vector
except ImportError:  # pragma: no cover
    from sqlalchemy import JSON as Vector

if TYPE_CHECKING:
    from app.models.actor import Actor, TituloElenco
    from app.models.estado import EstadoUsuarioTitulo
    from app.models.genero import Genero
    from app.models.resena import Resena
    from app.models.temporada import Temporada


class Titulo(Base):
    __tablename__ = "titulos"
    __table_args__ = (
        UniqueConstraint("tmdb_id", "tipo", name="uq_titulos_tmdb_id_tipo"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    tmdb_id: Mapped[int] = mapped_column(Integer, index=True, nullable=False)
    tipo: Mapped[str] = mapped_column(String(10), index=True, nullable=False)  # 'movie' | 'tv'
    nombre: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    sinopsis: Mapped[str | None] = mapped_column(Text, nullable=True)
    portada_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    fecha_estreno: Mapped[date | None] = mapped_column(Date, index=True, nullable=True)
    fecha_fin: Mapped[date | None] = mapped_column(Date, nullable=True)
    duracion: Mapped[int | None] = mapped_column(Integer, nullable=True)  # solo peliculas (minutos)

    @property
    def anio_estreno(self) -> int | None:
        return self.fecha_estreno.year if self.fecha_estreno else None

    @anio_estreno.setter
    def anio_estreno(self, val: int | None) -> None:
        if val is not None:
            self.fecha_estreno = date(val, 1, 1)
        else:
            self.fecha_estreno = None

    @property
    def anio_fin(self) -> int | None:
        return self.fecha_fin.year if self.fecha_fin else None

    @anio_fin.setter
    def anio_fin(self, val: int | None) -> None:
        if val is not None:
            self.fecha_fin = date(val, 1, 1)
        else:
            self.fecha_fin = None

    @property
    def titulo(self) -> str:
        return self.nombre

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
    embedding: Mapped[list[float] | None] = mapped_column(Vector(768), nullable=True)

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
