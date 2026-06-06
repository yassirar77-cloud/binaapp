"""
Authentication Endpoints
Handles user registration, login, and authentication
"""

from datetime import datetime, timedelta

from fastapi import APIRouter, HTTPException, status, Depends, Request
from loguru import logger

from app.models.schemas import (
    UserCreate,
    UserLogin,
    VerifyEmailRequest,
)
from app.services.supabase_client import supabase_service
from app.services.email_service import email_service
from app.core.config import settings
from app.core.security import create_access_token, get_current_user, decode_token_for_refresh
from app.core.verification import generate_code, hash_code, verify_code

router = APIRouter()


async def _issue_verification_code(user_id: str, email: str, full_name: str = None) -> bool:
    """
    Generate a fresh 6-digit code, persist its hash, and email it.

    Best-effort: returns whether the email was dispatched. Callers should NOT
    fail the parent request if this returns False (the user can request a
    resend) — but they should surface that the email is pending.
    """
    code = generate_code()
    ttl = settings.EMAIL_VERIFICATION_CODE_TTL_MINUTES
    expires_at = (datetime.utcnow() + timedelta(minutes=ttl)).isoformat()

    stored = await supabase_service.create_verification_code(
        user_id=user_id,
        code_hash=hash_code(user_id, code),
        expires_at_iso=expires_at,
    )
    if not stored:
        logger.error(f"Failed to store verification code for {email}")
        return False

    sent = await email_service.send_verification_code(
        user_email=email,
        user_name=full_name or (email.split("@")[0] if email else ""),
        code=code,
        ttl_minutes=ttl,
    )
    if not sent:
        logger.warning(f"Verification code stored but email send failed for {email}")
    return sent


@router.post("/register", response_model=dict, status_code=status.HTTP_201_CREATED)
async def register(user_data: UserCreate):
    """
    Register a new user.

    Flow:
    1. Create auth user via Supabase Admin API (bypasses RLS)
    2. The handle_new_user Postgres trigger (migration 035) creates the
       profiles row AND an active 'free' subscription automatically.
    3. Return JWT token

    The backend does NOT insert into profiles itself. Doing so collided with
    the trigger-created row on the primary key (409), which used to trigger a
    rollback (auth user deleted) and surface as a 500 on signup.
    """
    try:
        # STEP 1: Create user in Supabase Auth using Admin API.
        # full_name is passed as user_metadata; the trigger reads
        # raw_user_meta_data->>'full_name' to populate profiles.full_name.
        response = await supabase_service.create_user(
            email=user_data.email,
            password=user_data.password,
            full_name=user_data.full_name
        )

        if not response or not response.get("user"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to create user"
            )

        user = response["user"]
        user_id = user.get("id")
        user_email = user.get("email")

        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to create user - no user ID returned"
            )

        # NOTE: the profiles row and the active 'free' subscription are both
        # created by the on_auth_user_created trigger (migration 035). The
        # backend no longer inserts into profiles — that INSERT collided with
        # the trigger-created row on the primary key (409) and caused signup to
        # 500. If we ever collect profile fields the trigger doesn't set (e.g.
        # phone, business_name), do an UPDATE on profiles here — never an
        # INSERT, which would conflict with the trigger-created row.

        # STEP 2: Create JWT token.
        # The account starts UNVERIFIED (profiles.email_verified defaults to
        # false via migration 045). We still issue the JWT so the user can log
        # in and use the builder immediately — verification is only required
        # before publishing or paying (enforced by require_verified_email).
        access_token = create_access_token(
            data={
                "sub": user_id,
                "email": user_email
            }
        )

        # STEP 3: Send the 6-digit verification code (best-effort). A failure
        # here must NOT fail registration — the user can request a resend.
        email_sent = False
        if settings.EMAIL_VERIFICATION_ENABLED:
            try:
                email_sent = await _issue_verification_code(
                    user_id=user_id,
                    email=user_email,
                    full_name=user_data.full_name,
                )
            except Exception as e:
                logger.error(f"Verification code issuance failed for {user_email}: {e}")

        logger.info(f"✅ User registered successfully: {user_email} (verification email sent: {email_sent})")

        return {
            "message": "User registered successfully",
            "access_token": access_token,
            "token_type": "bearer",
            "email_verified": False,
            "verification_required": settings.EMAIL_VERIFICATION_ENABLED,
            "verification_email_sent": email_sent,
            "user": {
                "id": user_id,
                "email": user_email,
                "full_name": user_data.full_name,
                "email_verified": False
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Registration error: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/login", response_model=dict)
async def login(credentials: UserLogin):
    """
    Login user and return access token
    """
    try:
        # Sign in with Supabase
        response = await supabase_service.sign_in(
            email=credentials.email,
            password=credentials.password
        )

        if not response or not response.get("user"):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials"
            )

        user = response["user"]
        user_id = user.get("id")
        user_email = user.get("email")

        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials"
            )

        # Create JWT token
        access_token = create_access_token(
            data={
                "sub": user_id,
                "email": user_email
            }
        )

        logger.info(f"User logged in: {user_email}")

        return {
            "message": "Login successful",
            "access_token": access_token,
            "token_type": "bearer",
            "user": {
                "id": user_id,
                "email": user_email
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login error: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials"
        )


@router.post("/verify-email", response_model=dict)
async def verify_email(
    payload: VerifyEmailRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Confirm the authenticated user's email with the 6-digit code.

    Requires the user's own JWT (so a code can only be redeemed by the account
    it was issued to). On success, flips profiles.email_verified = true, which
    unlocks publish + payment.
    """
    user_id = current_user.get("sub") or current_user.get("id")
    email = current_user.get("email")

    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token - please login again"
        )

    # Already verified? Idempotent success.
    if await supabase_service.is_email_verified(user_id):
        return {"message": "Email already verified", "email_verified": True}

    record = await supabase_service.get_active_verification_code(user_id)
    if not record:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tiada kod aktif. Sila minta kod baharu. / No active code. Please request a new one.",
        )

    # Expiry check.
    expires_at = record.get("expires_at")
    try:
        exp_dt = datetime.fromisoformat(str(expires_at).replace("Z", "+00:00"))
        expired = datetime.now(exp_dt.tzinfo) >= exp_dt
    except Exception:
        expired = False
    if expired:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Kod telah tamat tempoh. Sila minta kod baharu. / Code expired. Please request a new one.",
        )

    # Attempt-limit check (prevents brute force on the 6-digit space).
    attempts = int(record.get("attempts") or 0)
    if attempts >= settings.EMAIL_VERIFICATION_MAX_ATTEMPTS:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Terlalu banyak percubaan. Sila minta kod baharu. / Too many attempts. Please request a new one.",
        )

    # Validate the submitted code.
    if not verify_code(user_id, payload.code, record.get("code_hash", "")):
        await supabase_service.increment_verification_attempts(record["id"], attempts + 1)
        remaining = max(0, settings.EMAIL_VERIFICATION_MAX_ATTEMPTS - (attempts + 1))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Kod tidak sah. Percubaan berbaki: {remaining}. / Invalid code. Attempts left: {remaining}.",
        )

    # Success: consume the code and mark verified.
    await supabase_service.consume_verification_code(record["id"])
    marked = await supabase_service.mark_email_verified(user_id)
    if not marked:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Gagal mengemas kini status pengesahan. / Failed to update verification status.",
        )

    logger.info(f"✅ Email verified for user: {email}")
    return {"message": "Email verified successfully", "email_verified": True}


@router.post("/resend-verification", response_model=dict)
async def resend_verification(current_user: dict = Depends(get_current_user)):
    """
    Re-issue and resend a verification code to the authenticated user.

    Invalidates any previous code. No-op (success) if already verified.
    """
    user_id = current_user.get("sub") or current_user.get("id")
    email = current_user.get("email")

    if not user_id or not email:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token - please login again"
        )

    if await supabase_service.is_email_verified(user_id):
        return {"message": "Email already verified", "email_verified": True}

    sent = await _issue_verification_code(user_id=user_id, email=email)
    return {
        "message": "Verification code sent" if sent else "Could not send verification email, please try again",
        "email_verified": False,
        "verification_email_sent": sent,
    }


@router.get("/me", response_model=dict)
async def get_current_user_info(current_user: dict = Depends(get_current_user)):
    """
    Get current authenticated user information
    """
    try:
        user_id = current_user.get("sub")

        # Get user details from Supabase
        user = await supabase_service.get_user(user_id)

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        # Get subscription info
        subscription = await supabase_service.get_user_subscription(user_id)

        # Get website count
        websites = await supabase_service.get_user_websites(user_id)

        # Email verification status (gates publish + pay)
        email_verified = await supabase_service.is_email_verified(user_id)

        return {
            "id": user_id,
            "email": user.email,
            "full_name": user.user_metadata.get("full_name"),
            "subscription_tier": subscription.get("tier") if subscription else "free",
            "websites_count": len(websites),
            "email_verified": email_verified
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting user info: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get user information"
        )


@router.post("/logout")
async def logout(current_user: dict = Depends(get_current_user)):
    """
    Logout user (client should discard token)
    """
    logger.info(f"User logged out: {current_user.get('email')}")

    return {
        "message": "Logged out successfully"
    }


@router.post("/refresh", response_model=dict)
async def refresh_token(request: Request):
    """
    Refresh an authentication token.

    Accepts an expired (but valid signature) token and returns a new token.
    This allows users to stay logged in without re-entering credentials.

    The token must have a valid signature - only the expiration is ignored.
    """
    # Get authorization header
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid authorization header"
        )

    token = auth_header.replace("Bearer ", "")

    # Decode the token (allows expired but requires valid signature)
    payload = decode_token_for_refresh(token)

    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token - please login again"
        )

    user_id = payload.get("sub")
    email = payload.get("email")

    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload - please login again"
        )

    # Create a new token with the same claims
    new_token = create_access_token(
        data={
            "sub": user_id,
            "email": email
        }
    )

    logger.info(f"Token refreshed for user: {email}")

    return {
        "message": "Token refreshed successfully",
        "access_token": new_token,
        "token_type": "bearer",
        "user": {
            "id": user_id,
            "email": email
        }
    }
