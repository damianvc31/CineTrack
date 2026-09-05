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
)


class Actor(Base):
    __tablename__ = "actores"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    tmdb_id: Mapped[int | None] = mapped_column(Integer, unique=True, nullable=True, index=True)
    nombre: Mapped[str] = mapped_column(String(150), nullable=False, index=True)

    # Relación inversa
    titulos: Mapped[list["Titulo"]] = relationship(
        secondary=titulos_elenco,
        back_populates="actores"
    )
