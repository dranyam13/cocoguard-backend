from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from typing import Optional
import logging

from .database import SessionLocal
from . import models
from .auth_utils import decode_access_token

logger = logging.getLogger(__name__)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")
oauth2_scheme_optional = OAuth2PasswordBearer(tokenUrl="/auth/login", auto_error=False)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> models.User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        logger.debug(f"Received token (first 50 chars): {token[:50]}...")
        payload = decode_access_token(token)
        if payload is None:
            logger.warning(f"Failed to decode access token: {token[:50]}...")
            raise credentials_exception

        user_id_str: str = payload.get("sub")
        if user_id_str is None:
            logger.warning("No user_id in token payload")
            raise credentials_exception
        
        # Convert string user_id to integer
        try:
            user_id = int(user_id_str)
        except (ValueError, TypeError):
            logger.warning(f"Invalid user_id format in token: {user_id_str}")
            raise credentials_exception

        user = db.query(models.User).filter(models.User.id == user_id).first()
        if user is None:
            logger.warning(f"User {user_id} not found in database")
            raise credentials_exception
            
        if user.status != models.UserStatus.active:
            logger.warning(f"User {user_id} is not active (status: {user.status})")
            raise credentials_exception
            
        logger.debug(f"User {user_id} authenticated successfully")
        return user
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in get_current_user: {str(e)}", exc_info=True)
        raise credentials_exception


def get_optional_current_user(
    token: Optional[str] = Depends(oauth2_scheme_optional),
    db: Session = Depends(get_db),
) -> Optional[models.User]:
    """
    Get current user if authenticated, otherwise return None.
    Useful for endpoints that work for both authenticated and anonymous users.
    """
    if token is None:
        return None
    
    try:
        payload = decode_access_token(token)
        if payload is None:
            return None

        user_id_str: str = payload.get("sub")
        if user_id_str is None:
            return None
        
        try:
            user_id = int(user_id_str)
        except (ValueError, TypeError):
            return None

        user = db.query(models.User).filter(models.User.id == user_id).first()
        if user is None or user.status != models.UserStatus.active:
            return None
            
        return user
    except Exception:
        return None


def get_current_admin(
    current_user: models.User = Depends(get_current_user),
) -> models.User:
    if current_user.role != models.UserRole.admin:
        raise HTTPException(status_code=403, detail="Admins only")
    return current_user
