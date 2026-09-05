from datetime import datetime
from typing import TYPE_CHECKING
from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.titulo import Titulo
    from app.models.usuario import Usuario


class EstadoUsuarioTitulo(Base):
    __tablename__ = "estados_usuario_titulos"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id", ondelete="CASCADE"), nullable=False, index=True)
    titulo_id: Mapped[int] = mapped_column(ForeignKey("titulos.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Favorito independiente
    favorito: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    fecha_favorito: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Estado mutuamente excluyente: 'watchlist' | 'siguiendo' | 'vista' | None
    estado: Mapped[str | None] = mapped_column(String(20), nullable=True, index=True)
    fecha_estado: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relaciones
    usuario: Mapped["Usuario"] = relationship(back_populates="estados")
    titulo: Mapped["Titulo"] = relationship(back_populates="estados")

    __table_args__ = (
        UniqueConstraint("usuario_id", "titulo_id", name="uq_usuario_titulo_estado"),
    )
