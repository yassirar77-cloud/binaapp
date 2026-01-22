"""
Authentication Endpoints
Handles user registration, login, and authentication
"""

from fastapi import APIRouter, HTTPException, status, Depends
from loguru import logger

from app.models.schemas import (
    UserCreate,
    UserLogin,
    UserResponse,
    SubscriptionTier
)
from app.services.supabase_client import supabase_service
from app.core.security import create_access_token, get_current_user

router = APIRouter()


@router.post("/register", response_model=dict, status_code=status.HTTP_201_CREATED)
async def register(user_data: UserCreate):
    """
    Register a new user
    """
    try:
        # Create user in Supabase Auth
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

        # Create JWT token
        access_token = create_access_token(
            data={
                "sub": user_id,
                "email": user_email
            }
        )

        # Initialize free subscription
        await supabase_service.update_subscription(user_id, {
            'tier': SubscriptionTier.FREE,
            'status': 'active'
        })

        logger.info(f"User registered: {user_email}")

        return {
            "message": "User registered successfully",
            "access_token": access_token,
            "token_type": "bearer",
            "user": {
                "id": user_id,
                "email": user_email,
                "full_name": user_data.full_name
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Registration error: {e}")
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

        return {
            "id": user_id,
            "email": user.email,
            "full_name": user.user_metadata.get("full_name"),
            "subscription_tier": subscription.get("tier") if subscription else "free",
            "websites_count": len(websites)
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
