from datetime import date
from typing import TYPE_CHECKING
from sqlalchemy import Date, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.episodio_visto import EpisodioVisto
    from app.models.temporada import Temporada


class Episodio(Base):
    __tablename__ = "episodios"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    temporada_id: Mapped[int] = mapped_column(ForeignKey("temporadas.id", ondelete="CASCADE"), nullable=False, index=True)
    numero: Mapped[int] = mapped_column(Integer, nullable=False)
    nombre: Mapped[str] = mapped_column(String(255), nullable=False)
    fecha_estreno: Mapped[date | None] = mapped_column(Date, nullable=True)
    duracion: Mapped[int | None] = mapped_column(Integer, nullable=True)  # minutos

    # Relaciones
    temporada: Mapped["Temporada"] = relationship(back_populates="episodios")
    episodios_vistos: Mapped[list["EpisodioVisto"]] = relationship(
        back_populates="episodio",
        cascade="all, delete-orphan"
    )

    __table_args__ = (
        UniqueConstraint("temporada_id", "numero", name="uq_episodio_temporada_numero"),
    )
