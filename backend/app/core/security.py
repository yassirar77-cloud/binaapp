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
    except jwt.ExpiredSignatureError as e:
        logger.info("Token expired - user needs to refresh or re-login")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session expired - please refresh or login again",
            headers={"WWW-Authenticate": "Bearer", "X-Token-Expired": "true"},
        ) from e
    except jwt.JWTClaimsError as e:
        logger.warning(f"Invalid JWT claims: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from e
    except JWTError as e:
        logger.warning(f"JWT verification failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials - please login again",
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
    is_token_expired = False

    # Check for common invalid token patterns
    if not token or token in ('undefined', 'null', 'None', ''):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No valid token provided - please login again",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # FIRST: Try to decode with our custom JWT secret (tokens we create)
    try:
        payload = decode_access_token(token)
        user_id = payload.get("sub")
        if user_id:
            return payload
        else:
            logger.warning("Token missing 'sub' claim")
    except HTTPException as e:
        # Check if token is expired
        if "expired" in str(e.detail).lower():
            is_token_expired = True
        logger.debug(f"Custom JWT verification failed: {e.detail}")
    except Exception as e:
        logger.debug(f"Custom JWT verification did not apply: {e}")

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
                return payload
        except jwt.ExpiredSignatureError:
            is_token_expired = True
            logger.debug("Supabase token expired")
        except JWTError as e:
            logger.debug(f"Supabase JWT verification failed: {e}")
    else:
        logger.warning("SUPABASE_JWT_SECRET is not configured")

    # If token was expired, return specific message
    if is_token_expired:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session expired - please refresh or login again",
            headers={"WWW-Authenticate": "Bearer", "X-Token-Expired": "true"},
        )

    # If all local verification fails, reject the token
    logger.warning("Authentication failed: token could not be verified")
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid authentication token - please login again",
        headers={"WWW-Authenticate": "Bearer"},
    )


async def require_verified_email(
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Dependency that requires the authenticated user to have a verified email.

    Layered on top of get_current_user, so the caller is already authenticated.
    Used to gate high-value actions (publish a website, pay/subscribe) while
    leaving signup and the builder open — the "try it now, verify before you
    publish/pay" model.

    Returns the user payload if verified; raises 403 with a machine-readable
    header (X-Email-Verification-Required) so the frontend can prompt the
    user to enter their code. Can be globally disabled via
    settings.EMAIL_VERIFICATION_ENABLED.
    """
    # Import here to avoid a circular import at module load time.
    from app.services.supabase_client import supabase_service

    if not getattr(settings, "EMAIL_VERIFICATION_ENABLED", True):
        return current_user

    user_id = current_user.get("sub") or current_user.get("id")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token - please login again",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        verified = await supabase_service.is_email_verified(user_id)
    except Exception as e:
        logger.error(f"Email verification check failed for {user_id}: {e}")
        verified = False

    if not verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                "Sila sahkan e-mel anda untuk meneruskan. "
                "/ Please verify your email to continue."
            ),
            headers={"X-Email-Verification-Required": "true"},
        )

    return current_user


def decode_token_for_refresh(token: str) -> Optional[Dict[str, Any]]:
    """
    Decode a JWT token for refresh purposes.
    Allows expired tokens but requires valid signature.

    Returns payload if token signature is valid (even if expired), None otherwise.
    """
    # Try our custom JWT secret first
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
            options={"verify_exp": False}  # Allow expired tokens
        )
        user_id = payload.get("sub")
        if user_id:
            logger.debug(f"Token decoded for refresh (custom secret) for user: {user_id}")
            return payload
    except JWTError as e:
        logger.debug(f"Custom JWT decode for refresh failed: {e}")

    # Try Supabase JWT secret
    if settings.SUPABASE_JWT_SECRET:
        try:
            payload = jwt.decode(
                token,
                settings.SUPABASE_JWT_SECRET,
                algorithms=["HS256"],
                options={"verify_exp": False, "verify_aud": False}
            )
            user_id = payload.get("sub")
            if user_id:
                logger.debug(f"Token decoded for refresh (Supabase secret) for user: {user_id}")
                return payload
        except JWTError as e:
            logger.debug(f"Supabase JWT decode for refresh failed: {e}")

    return None


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


# Optional Bearer token security (doesn't throw if missing)
optional_security = HTTPBearer(auto_error=False)


async def get_optional_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(optional_security)
) -> Optional[Dict[str, Any]]:
    """
    Get current authenticated user from token, or None if not authenticated.

    Use this for endpoints that support both authenticated and unauthenticated access.
    """
    if not credentials:
        return None

    token = credentials.credentials

    # Try to decode with our custom JWT secret
    try:
        payload = decode_access_token(token)
        user_id = payload.get("sub")
        if user_id:
            logger.debug(f"Optional auth: Token verified for user: {user_id}")
            return payload
    except Exception:
        pass

    # Try SUPABASE_JWT_SECRET
    if settings.SUPABASE_JWT_SECRET:
        try:
            payload = jwt.decode(
                token,
                settings.SUPABASE_JWT_SECRET,
                algorithms=["HS256"],
                options={"verify_aud": False}
            )
            user_id = payload.get("sub")
            if user_id:
                logger.debug(f"Optional auth: Supabase token verified for user: {user_id}")
                return payload
        except JWTError:
            pass

    # Token present but invalid - return None (don't throw)
    logger.debug("Optional auth: Invalid token provided, continuing without auth")
    return None
