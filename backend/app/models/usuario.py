from datetime import datetime
from typing import TYPE_CHECKING
from sqlalchemy import DateTime, LargeBinary, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.estado import EstadoUsuarioTitulo
    from app.models.episodio_visto import EpisodioVisto
    from app.models.resena import Resena


class Usuario(Base):
    __tablename__ = "usuarios"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    nombre_usuario: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    pais: Mapped[str | None] = mapped_column(String(100), nullable=True)
    ciudad: Mapped[str | None] = mapped_column(String(100), nullable=True)
    descripcion: Mapped[str | None] = mapped_column(Text, nullable=True)
    fecha_registro: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    avatar_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    avatar_binario: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)

    # Relaciones
    estados: Mapped[list["EstadoUsuarioTitulo"]] = relationship(back_populates="usuario", cascade="all, delete-orphan")
    episodios_vistos: Mapped[list["EpisodioVisto"]] = relationship(back_populates="usuario", cascade="all, delete-orphan")
    resenas: Mapped[list["Resena"]] = relationship(back_populates="usuario", cascade="all, delete-orphan")
