"""
Autenticación JWT y API Keys para la API de auditoría financiera.
Proporciona dependencias de FastAPI para proteger los endpoints.
"""
from datetime import datetime, timedelta
from typing import Optional, Annotated

from fastapi import Depends, HTTPException, Security, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials, APIKeyHeader
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel

from config.settings import settings

# Contexto de hashing de contraseñas
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Esquemas de seguridad
bearer_scheme = HTTPBearer(auto_error=False)
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


class TokenData(BaseModel):
    """Datos extraídos del token JWT."""
    username: Optional[str] = None
    scopes: list[str] = []


class Token(BaseModel):
    """Respuesta de autenticación con token JWT."""
    access_token: str
    token_type: str = "bearer"
    expires_in: int


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Crea un token JWT firmado con los datos proporcionados."""
    to_encode = data.copy()
    expire = datetime.utcnow() + (
        expires_delta or timedelta(minutes=settings.access_token_expire_minutes)
    )
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifica si una contraseña en texto plano coincide con el hash."""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Genera el hash bcrypt de una contraseña."""
    return pwd_context.hash(password)


def decode_token(token: str) -> TokenData:
    """Decodifica y valida un token JWT. Lanza HTTPException si es inválido."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="No se pudo validar las credenciales",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        username: Optional[str] = payload.get("sub")
        if username is None:
            raise credentials_exception
        return TokenData(username=username, scopes=payload.get("scopes", []))
    except JWTError:
        raise credentials_exception


async def get_current_user(
    bearer: Optional[HTTPAuthorizationCredentials] = Security(bearer_scheme),
    api_key: Optional[str] = Security(api_key_header),
) -> TokenData:
    """
    Dependencia FastAPI que valida autenticación por JWT Bearer o API Key.
    Lanza 401 si ninguna credencial es válida.
    """
    # Intentar autenticación por API Key primero
    if api_key and api_key == settings.api_key_secret:
        return TokenData(username="api_key_user", scopes=["read", "write"])

    # Intentar autenticación por JWT Bearer
    if bearer:
        return decode_token(bearer.credentials)

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Se requiere autenticación: Bearer token o API Key",
        headers={"WWW-Authenticate": "Bearer"},
    )


# Dependencia reutilizable
CurrentUser = Annotated[TokenData, Depends(get_current_user)]
