from datetime import datetime, timedelta, timezone
from typing import Any
import bcrypt
import jwt

from app.core.config import settings

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24 horas por defecto


def hash_password(password: str) -> str:
    """Hashea una contraseña usando bcrypt."""
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifica si la contraseña en texto plano coincide con el hash."""
    return bcrypt.checkpw(
        plain_password.encode("utf-8"),
        hashed_password.encode("utf-8")
    )


def create_access_token(subject: str | Any, expires_delta: timedelta | None = None) -> str:
    """Crea un token JWT firmado estrictamente con settings.AUTH_SECRET_KEY."""
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode = {
        "exp": expire,
        "sub": str(subject),
        "iat": datetime.now(timezone.utc)
    }
    encoded_jwt = jwt.encode(to_encode, settings.AUTH_SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def decode_access_token(token: str) -> dict[str, Any] | None:
    """Decodifica y valida un token JWT usando settings.AUTH_SECRET_KEY."""
    try:
        decoded = jwt.decode(token, settings.AUTH_SECRET_KEY, algorithms=[ALGORITHM])
        return decoded
    except jwt.PyJWTError:
        return None
