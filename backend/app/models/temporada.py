from datetime import date
from typing import TYPE_CHECKING
from sqlalchemy import Date, ForeignKey, Integer, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.episodio import Episodio
    from app.models.titulo import Titulo


class Temporada(Base):
    __tablename__ = "temporadas"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    titulo_id: Mapped[int] = mapped_column(ForeignKey("titulos.id", ondelete="CASCADE"), nullable=False, index=True)
    numero: Mapped[int] = mapped_column(Integer, nullable=False)
    sinopsis: Mapped[str | None] = mapped_column(Text, nullable=True)
    fecha_estreno: Mapped[date | None] = mapped_column(Date, nullable=True)

    # Relaciones
    titulo: Mapped["Titulo"] = relationship(back_populates="temporadas")
    episodios: Mapped[list["Episodio"]] = relationship(
        back_populates="temporada",
        cascade="all, delete-orphan",
        order_by="Episodio.numero"
    )

    __table_args__ = (
        UniqueConstraint("titulo_id", "numero", name="uq_temporada_titulo_numero"),
    )
