from datetime import datetime
from typing import TYPE_CHECKING
from sqlalchemy import CheckConstraint, DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.titulo import Titulo
    from app.models.usuario import Usuario


class Resena(Base):
    __tablename__ = "resenas"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    titulo_id: Mapped[int] = mapped_column(ForeignKey("titulos.id", ondelete="CASCADE"), nullable=False, index=True)
    usuario_id: Mapped[int | None] = mapped_column(ForeignKey("usuarios.id", ondelete="SET NULL"), nullable=True, index=True)
    autor_tmdb: Mapped[str | None] = mapped_column(String(100), nullable=True)
    puntaje: Mapped[float | None] = mapped_column(Float, nullable=True)  # 1.0 a 10.0, opcional
    texto: Mapped[str] = mapped_column(Text, nullable=False)
    fecha: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    tmdb_review_id: Mapped[str | None] = mapped_column(String(100), unique=True, nullable=True, index=True)

    # Relaciones
    titulo: Mapped["Titulo"] = relationship(back_populates="resenas")
    usuario: Mapped["Usuario | None"] = relationship(back_populates="resenas")

    __table_args__ = (
        CheckConstraint("(usuario_id IS NOT NULL) OR (autor_tmdb IS NOT NULL)", name="chk_resena_autor_presente"),
    )
