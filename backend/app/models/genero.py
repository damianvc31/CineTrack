from typing import TYPE_CHECKING
from sqlalchemy import Column, ForeignKey, Integer, String, Table
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.titulo import Titulo

# Tabla asociativa Muchos a Muchos: Titulos <-> Generos
titulos_generos = Table(
    "titulos_generos",
    Base.metadata,
    Column("titulo_id", Integer, ForeignKey("titulos.id", ondelete="CASCADE"), primary_key=True),
    Column("genero_id", Integer, ForeignKey("generos.id", ondelete="CASCADE"), primary_key=True),
)


class Genero(Base):
    __tablename__ = "generos"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    tmdb_id: Mapped[int | None] = mapped_column(Integer, unique=True, nullable=True, index=True)
    nombre: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)

    # Relación inversa
    titulos: Mapped[list["Titulo"]] = relationship(
        secondary=titulos_generos,
        back_populates="generos"
    )
