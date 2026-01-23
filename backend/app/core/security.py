"""
Security utilities for authentication and authorization
"""

from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from loguru import logger
import os

from app.core.config import settings

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Bearer token security
security = HTTPBearer()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash"""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Generate password hash"""
    return pwd_context.hash(password)


def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """Create JWT access token"""
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(hours=settings.JWT_EXPIRATION_HOURS)

    to_encode.update({"exp": expire, "iat": datetime.utcnow()})

    encoded_jwt = jwt.encode(
        to_encode,
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM
    )

    return encoded_jwt


def decode_access_token(token: str) -> Dict[str, Any]:
    """Decode and verify JWT token"""
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM]
        )
        return payload
    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        ) from e


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> Dict[str, Any]:
    """
    Get current authenticated user from token.

    Verifies JWT tokens LOCALLY without network calls for speed.

    Order of verification:
    1. Custom JWT_SECRET_KEY (tokens created by our backend)
    2. SUPABASE_JWT_SECRET (tokens created by Supabase)
    """
    token = credentials.credentials

    # FIRST: Try to decode with our custom JWT secret (tokens we create)
    try:
        payload = decode_access_token(token)
        user_id = payload.get("sub")
        if user_id:
            logger.debug(f"Token verified with custom JWT secret for user: {user_id}")
            return payload
    except Exception as e:
        logger.debug(f"Custom JWT verification failed: {e}")

    # SECOND: Try SUPABASE_JWT_SECRET (for Supabase-signed tokens)
    if settings.SUPABASE_JWT_SECRET:
        try:
            # Supabase tokens use HS256 algorithm
            # Disable audience verification for compatibility
            payload = jwt.decode(
                token,
                settings.SUPABASE_JWT_SECRET,
                algorithms=["HS256"],
                options={"verify_aud": False}
            )
            user_id = payload.get("sub")
            if user_id:
                logger.debug(f"Token verified with Supabase JWT secret for user: {user_id}")
                return payload
        except JWTError as e:
            logger.debug(f"Supabase JWT verification failed: {e}")

    # If all local verification fails, reject the token
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials - please login again",
        headers={"WWW-Authenticate": "Bearer"},
    )


def verify_api_key(api_key: str) -> bool:
    """
    Verify API key for external integrations.

    SECURITY: Checks against configured API keys in environment or database.

    For production, set BINAAPP_API_KEYS environment variable with comma-separated keys:
    BINAAPP_API_KEYS="bina_abc123...,bina_xyz789..."

    Returns:
        bool: True if API key is valid, False otherwise
    """
    if not api_key:
        return False

    # Check environment variable for configured API keys
    configured_keys = settings.BINAAPP_API_KEYS if hasattr(settings, 'BINAAPP_API_KEYS') else None

    if configured_keys:
        # Support comma-separated list of keys
        valid_keys = [k.strip() for k in configured_keys.split(',') if k.strip()]

        # SECURITY: Use constant-time comparison to prevent timing attacks
        import hmac
        for valid_key in valid_keys:
            if hmac.compare_digest(api_key, valid_key):
                return True
        return False

    # If no API keys configured, reject all (secure by default)
    # To enable API key authentication, set BINAAPP_API_KEYS environment variable
    logger.warning(
        "API key validation attempted but no BINAAPP_API_KEYS configured. "
        "Set BINAAPP_API_KEYS environment variable to enable API key authentication."
    )
    return False


def generate_api_key() -> str:
    """Generate a new API key"""
    import secrets
    return f"bina_{secrets.token_urlsafe(32)}"
