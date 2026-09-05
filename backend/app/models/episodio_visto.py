from datetime import datetime
from typing import TYPE_CHECKING
from sqlalchemy import DateTime, ForeignKey, Integer, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.episodio import Episodio
    from app.models.usuario import Usuario


class EpisodioVisto(Base):
    __tablename__ = "episodios_vistos"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id", ondelete="CASCADE"), nullable=False, index=True)
    episodio_id: Mapped[int] = mapped_column(ForeignKey("episodios.id", ondelete="CASCADE"), nullable=False, index=True)
    fecha_visto: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relaciones
    usuario: Mapped["Usuario"] = relationship(back_populates="episodios_vistos")
    episodio: Mapped["Episodio"] = relationship(back_populates="episodios_vistos")

    __table_args__ = (
        UniqueConstraint("usuario_id", "episodio_id", name="uq_usuario_episodio_visto"),
    )
