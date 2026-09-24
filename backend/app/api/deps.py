from typing import Optional
from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import decode_access_token
from app.db.session import get_db
from app.models.usuario import Usuario
from app.services.auth_service import get_user_by_id

security = HTTPBearer()
optional_security = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
) -> Usuario:
    """Extrae y valida el usuario actual a partir del token JWT Bearer."""
    token = credentials.credentials
    payload = decode_access_token(token)

    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token de acceso inválido o expirado.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id_str = payload.get("sub")
    if not user_id_str:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token sin sujeto válido.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        user_id = int(user_id_str)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Identificador de usuario inválido en token.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = await get_user_by_id(db, user_id=user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario no encontrado.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user


async def get_optional_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(optional_security),
    db: AsyncSession = Depends(get_db)
) -> Optional[Usuario]:
    """Retorna el usuario si el token es válido, o None si no hay token o es inválido."""
    if not credentials:
        return None
    payload = decode_access_token(credentials.credentials)
    if not payload or not payload.get("sub"):
        return None
    try:
        user_id = int(payload["sub"])
        return await get_user_by_id(db, user_id=user_id)
    except Exception:
        return None


def get_optional_user_id(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(optional_security)
) -> Optional[int]:
    """Extrae el user_id verificado criptográficamente del token JWT sin consultar la base de datos."""
    if not credentials:
        return None
    payload = decode_access_token(credentials.credentials)
    if not payload or not payload.get("sub"):
        return None
    try:
        return int(payload["sub"])
    except (ValueError, TypeError):
        return None


async def get_current_admin(
    x_admin_key: Optional[str] = Header(default=None, alias="X-Admin-Key"),
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(optional_security),
    db: AsyncSession = Depends(get_db)
) -> Optional[Usuario]:
    """
    Verifica que la petición provenga de un administrador.
    Valida vía:
    1. Header 'X-Admin-Key' con la clave configurada en settings.ADMIN_API_KEY.
    2. O Token JWT de un usuario registrado con es_admin=True.
    """
    # 1. Validación vía Admin API Key
    if x_admin_key and x_admin_key == settings.ADMIN_API_KEY:
        return None

    # 2. Validación vía Token JWT
    if credentials:
        payload = decode_access_token(credentials.credentials)
        if payload and payload.get("sub"):
            try:
                user_id = int(payload["sub"])
                user = await get_user_by_id(db, user_id=user_id)
                if user and user.es_admin:
                    return user
                elif user:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Acceso denegado: se requieren privilegios de administrador."
                    )
            except ValueError:
                pass

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Credenciales administrativas requeridas (Token de admin o header X-Admin-Key válido).",
        headers={"WWW-Authenticate": "Bearer"},
    )
