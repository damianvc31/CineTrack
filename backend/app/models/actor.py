from typing import TYPE_CHECKING
from sqlalchemy import Column, ForeignKey, Integer, String, Table
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.titulo import Titulo

# Tabla asociativa Muchos a Muchos: Titulos <-> Actores
titulos_elenco = Table(
    "titulos_elenco",
    Base.metadata,
    Column("titulo_id", Integer, ForeignKey("titulos.id", ondelete="CASCADE"), primary_key=True),
    Column("actor_id", Integer, ForeignKey("actores.id", ondelete="CASCADE"), primary_key=True),
    Column("personaje", String(150), nullable=True),
    Column("orden", Integer, default=0, nullable=False),
)


class TituloElenco(Base):
    __table__ = titulos_elenco

    # Relaciones explícitas para acceder a actor + personaje + orden
    titulo: Mapped["Titulo"] = relationship(back_populates="elenco", overlaps="actores,titulos")
    actor: Mapped["Actor"] = relationship(back_populates="participaciones", overlaps="actores,titulos")


class Actor(Base):
    __tablename__ = "actores"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    tmdb_id: Mapped[int | None] = mapped_column(Integer, unique=True, nullable=True, index=True)
    nombre: Mapped[str] = mapped_column(String(150), nullable=False, index=True)

    # Relación directa simple Many-to-Many
    titulos: Mapped[list["Titulo"]] = relationship(
        secondary=titulos_elenco,
        back_populates="actores",
        overlaps="elenco,participaciones,titulo,actor"
    )

    # Participaciones detalladas con personaje y orden
    participaciones: Mapped[list["TituloElenco"]] = relationship(
        back_populates="actor",
        cascade="all, delete-orphan",
        overlaps="actores,titulos"
    )
