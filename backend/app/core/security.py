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
    """Get current authenticated user from token"""
    import httpx

    token = credentials.credentials

    # Supabase Auth API requires an API key header. Prefer anon, fallback to service role.
    # Some deployments only set SUPABASE_SERVICE_ROLE_KEY (or SUPABASE_SERVICE_KEY / SUPABASE_KEY).
    supabase_api_key = (
        settings.SUPABASE_ANON_KEY
        or settings.SUPABASE_SERVICE_ROLE_KEY
        or os.getenv("SUPABASE_SERVICE_KEY", "")
        or os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
        or os.getenv("SUPABASE_KEY", "")
        or os.getenv("SUPABASE_ANON_KEY", "")
    )

    # Try to verify token using Supabase Auth API
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{settings.SUPABASE_URL}/auth/v1/user",
                headers={
                    "Authorization": f"Bearer {token}",
                    "apikey": supabase_api_key
                }
            )

            if response.status_code == 200:
                user_data = response.json()
                # Return user data in expected format
                return {
                    "sub": user_data.get("id"),
                    "email": user_data.get("email"),
                    **user_data
                }
            # Log non-200 for easier diagnosis of owner dashboard auth issues
            logger.debug(
                f"Supabase auth verification failed: status={response.status_code}, body={response.text[:200]}"
            )
    except Exception as e:
        logger.debug(f"Supabase auth verification exception: {e}")

    # Fallback: Try to decode token with Supabase JWT secret if available
    if settings.SUPABASE_JWT_SECRET:
        try:
            # SECURITY NOTE: Audience verification
            # - Supabase tokens have a non-standard 'aud' claim (usually 'authenticated')
            # - For enhanced security, set SUPABASE_JWT_AUDIENCE in environment
            # - If not set, audience verification is skipped (less secure but more compatible)
            # - Risk: If JWT secret is shared across services, tokens could be reused
            #
            # To enable audience verification:
            # 1. Set SUPABASE_JWT_AUDIENCE="authenticated" in environment
            # 2. Ensure it matches your Supabase project's audience claim

            decode_options = {"verify_aud": False}  # Default: disabled for compatibility

            # If audience is configured, enable verification
            if hasattr(settings, 'SUPABASE_JWT_AUDIENCE') and settings.SUPABASE_JWT_AUDIENCE:
                decode_options = {
                    "verify_aud": True,
                    "audience": settings.SUPABASE_JWT_AUDIENCE
                }
                logger.debug(f"JWT audience verification enabled: {settings.SUPABASE_JWT_AUDIENCE}")

            payload = jwt.decode(
                token,
                settings.SUPABASE_JWT_SECRET,
                algorithms=["HS256"],
                options=decode_options
            )
            return payload
        except JWTError as e:
            logger.debug(f"Supabase JWT verification failed: {e}")
            pass

    # Last resort: Try custom JWT secret (for backwards compatibility)
    try:
        payload = decode_access_token(token)
        user_id = payload.get("sub")
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return payload
    except Exception:
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
