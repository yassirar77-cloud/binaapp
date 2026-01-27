"""
Supabase Client Dependency
Provides Supabase client for FastAPI dependency injection
"""
import os
from supabase import create_client, Client
from typing import Optional
from loguru import logger


# Global Supabase client instance
_supabase_client: Optional[Client] = None


def get_supabase_client() -> Client:
    """
    Get or create Supabase client for dependency injection.
    This can be used with FastAPI's Depends().

    Usage:
        @app.get("/endpoint")
        async def endpoint(supabase: Client = Depends(get_supabase_client)):
            result = supabase.table("table").select("*").execute()
    """
    global _supabase_client

    # Return existing client if available
    if _supabase_client is not None:
        return _supabase_client

    # Create new client
    SUPABASE_URL = os.getenv("SUPABASE_URL", "")

    # Try multiple possible key names
    SUPABASE_KEY = (
        os.getenv("SUPABASE_SERVICE_KEY") or
        os.getenv("SUPABASE_SERVICE_ROLE_KEY") or
        os.getenv("SUPABASE_KEY") or
        os.getenv("SUPABASE_ANON_KEY") or
        ""
    )

    if not SUPABASE_URL or not SUPABASE_KEY:
        logger.error("❌ Supabase credentials not found in environment variables")
        raise RuntimeError("Supabase not configured. Please set SUPABASE_URL and SUPABASE_SERVICE_KEY")

    try:
        _supabase_client = create_client(SUPABASE_URL, SUPABASE_KEY)
        logger.info("✅ Supabase client created for API endpoints")
        return _supabase_client
    except Exception as e:
        logger.error(f"❌ Failed to create Supabase client: {e}")
        raise RuntimeError(f"Failed to initialize Supabase client: {str(e)}")


def init_supabase() -> Optional[Client]:
    """
    Initialize Supabase client on application startup.
    Call this from main.py startup event.
    """
    global _supabase_client

    try:
        _supabase_client = get_supabase_client()
        logger.info("✅ Supabase initialized successfully")
        return _supabase_client
    except Exception as e:
        logger.error(f"❌ Failed to initialize Supabase: {e}")
        return None
