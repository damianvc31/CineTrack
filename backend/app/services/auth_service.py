from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password, verify_password
from app.models.usuario import Usuario
from app.schemas.auth import UserLogin, UserRegister


async def register_user(db: AsyncSession, user_in: UserRegister) -> Usuario:
    """Registra un nuevo usuario con contraseña hasheada."""
    # Verificar si el nombre de usuario ya existe
    query = select(Usuario).where(Usuario.nombre_usuario == user_in.nombre_usuario)
    res = await db.execute(query)
    existing_user = res.scalar_one_or_none()

    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El nombre de usuario ya se encuentra registrado."
        )

    # Hashear contraseña y persistir
    db_user = Usuario(
        nombre_usuario=user_in.nombre_usuario,
        password_hash=hash_password(user_in.password),
        pais=user_in.pais,
        ciudad=user_in.ciudad,
        descripcion=user_in.descripcion,
        avatar_url=user_in.avatar_url
    )
    db.add(db_user)
    await db.commit()
    await db.refresh(db_user)
    return db_user


async def authenticate_user(db: AsyncSession, login_in: UserLogin) -> Usuario:
    """Autentica un usuario verificando credenciales."""
    query = select(Usuario).where(Usuario.nombre_usuario == login_in.nombre_usuario)
    res = await db.execute(query)
    user = res.scalar_one_or_none()

    if not user or not verify_password(login_in.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales inválidas.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user


async def get_user_by_id(db: AsyncSession, user_id: int) -> Usuario | None:
    """Busca un usuario por su ID primario."""
    query = select(Usuario).where(Usuario.id == user_id)
    res = await db.execute(query)
    return res.scalar_one_or_none()
