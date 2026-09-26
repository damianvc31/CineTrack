from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field


class UserRegister(BaseModel):
    nombre_usuario: str = Field(..., min_length=3, max_length=50, description="Nombre de usuario único")
    password: str = Field(..., min_length=6, max_length=100, description="Contraseña")
    pais: str | None = Field(default=None, max_length=100)
    ciudad: str | None = Field(default=None, max_length=100)
    descripcion: str | None = Field(default=None, max_length=500)
    avatar_url: str | None = Field(default=None, max_length=500)


class UserLogin(BaseModel):
    nombre_usuario: str = Field(..., description="Nombre de usuario")
    password: str = Field(..., description="Contraseña")


from app.core.config import VarietyLevel


class UserResponse(BaseModel):
    id: int
    nombre_usuario: str
    pais: str | None = None
    ciudad: str | None = None
    descripcion: str | None = None
    avatar_url: str | None = None
    es_admin: bool = False
    fecha_registro: datetime
    preferencia_variedad_ia: VarietyLevel = VarietyLevel.MEDIUM

    model_config = ConfigDict(from_attributes=True)


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


class UserUpdate(BaseModel):
    pais: str | None = Field(default=None, max_length=100)
    ciudad: str | None = Field(default=None, max_length=100)
    descripcion: str | None = Field(default=None, max_length=500)
    avatar_url: str | None = Field(default=None, max_length=500)
    preferencia_variedad_ia: VarietyLevel | None = Field(default=None)


class PasswordChangeRequest(BaseModel):
    current_password: str = Field(..., description="Contraseña actual")
    new_password: str = Field(..., min_length=6, max_length=100, description="Nueva contraseña")


class AvatarUploadPayload(BaseModel):
    image_base64: str = Field(..., description="Data URI o imagen codificada en base64")
