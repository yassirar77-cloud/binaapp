"""
Database module - provides Supabase client access for middleware and services.

This module provides get_supabase() which returns a Supabase Python client
using the service role key (bypasses RLS) for server-side operations like
the subdomain middleware.
"""
import os
from typing import Optional
from loguru import logger
from supabase import create_client, Client


_supabase_client: Optional[Client] = None


def get_supabase() -> Client:
    """
    Get or create the Supabase client instance.

    Uses service role key for full admin access (bypasses RLS).
    This is appropriate for middleware that needs to look up any website
    regardless of the requesting user.

    Returns:
        Supabase Client instance

    Raises:
        RuntimeError: If Supabase credentials are not configured
    """
    global _supabase_client

    if _supabase_client is not None:
        return _supabase_client

    SUPABASE_URL = os.getenv("SUPABASE_URL", "")

    # Try multiple possible key names for flexibility
    SUPABASE_KEY = (
        os.getenv("SUPABASE_SERVICE_KEY") or
        os.getenv("SUPABASE_SERVICE_ROLE_KEY") or
        os.getenv("SUPABASE_KEY") or
        os.getenv("SUPABASE_ANON_KEY") or
        ""
    )

    if not SUPABASE_URL or not SUPABASE_KEY:
        logger.error("Supabase credentials not found for database module")
        raise RuntimeError(
            "Supabase not configured. Set SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY."
        )

    try:
        _supabase_client = create_client(SUPABASE_URL, SUPABASE_KEY)
        logger.info("Supabase client created via database module")
        return _supabase_client
    except Exception as e:
        logger.error(f"Failed to create Supabase client in database module: {e}")
        raise RuntimeError(f"Failed to initialize Supabase client: {e}")
