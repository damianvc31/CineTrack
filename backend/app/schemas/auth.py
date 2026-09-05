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


class UserResponse(BaseModel):
    id: int
    nombre_usuario: str
    pais: str | None = None
    ciudad: str | None = None
    descripcion: str | None = None
    avatar_url: str | None = None
    fecha_registro: datetime

    model_config = ConfigDict(from_attributes=True)


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse
