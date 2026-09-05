from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.security import create_access_token
from app.db.session import get_db
from app.models.usuario import Usuario
from app.schemas.auth import Token, UserLogin, UserRegister, UserResponse
from app.services.auth_service import authenticate_user, register_user

router = APIRouter(prefix="/auth", tags=["Autenticación"])


@router.post("/register", response_model=Token, status_code=status.HTTP_201_CREATED)
async def register(
    user_in: UserRegister,
    db: AsyncSession = Depends(get_db)
) -> Token:
    """Registra un nuevo usuario y retorna su token JWT."""
    user = await register_user(db, user_in)
    access_token = create_access_token(subject=user.id)
    return Token(
        access_token=access_token,
        token_type="bearer",
        user=UserResponse.model_validate(user)
    )


@router.post("/login", response_model=Token)
async def login(
    login_in: UserLogin,
    db: AsyncSession = Depends(get_db)
) -> Token:
    """Inicia sesión y retorna token JWT para el usuario autenticado."""
    user = await authenticate_user(db, login_in)
    access_token = create_access_token(subject=user.id)
    return Token(
        access_token=access_token,
        token_type="bearer",
        user=UserResponse.model_validate(user)
    )


@router.get("/me", response_model=UserResponse)
async def get_me(
    current_user: Usuario = Depends(get_current_user)
) -> UserResponse:
    """Retorna el perfil del usuario autenticado."""
    return UserResponse.model_validate(current_user)
