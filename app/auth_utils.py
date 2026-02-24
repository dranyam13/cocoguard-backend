from datetime import datetime, timedelta, timezone
from typing import Optional
import logging

from jose import jwt, JWTError
from passlib.context import CryptContext
from .config import settings

# Support both argon2 and bcrypt for backward compatibility with existing password hashes
pwd_context = CryptContext(schemes=["argon2", "bcrypt"], deprecated="auto")

logger = logging.getLogger(__name__)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=settings.access_token_expire_minutes))
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)
    return encoded_jwt


def decode_access_token(token: str) -> Optional[dict]:
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        return payload
    except JWTError as e:
        logger.error(f"JWT decode error: {str(e)}, token preview: {token[:50]}...")
        return None
