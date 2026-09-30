"""Admin-only dependency for FastAPI routes.

Two admin conventions coexist in this codebase:

  * an email allowlist (``ADMIN_EMAILS``, default the founder's address) used
    by the admin dashboard and monitor endpoints, and
  * ``public.users.role = 'admin'`` used by the newer admin routers through
    ``subscription_service._is_admin``.

``require_admin`` accepts either, so a route guarded with it works for the
founder account today and for any account later promoted by role. It fails
closed: no identity, no match, no access.
"""

from __future__ import annotations

import os
from typing import Any, Dict

from fastapi import Depends, HTTPException, status

from app.core.security import get_current_user


def admin_emails() -> set[str]:
    raw = os.getenv("ADMIN_EMAILS", "yassirar77@gmail.com")
    return {e.strip().lower() for e in raw.split(",") if e.strip()}


async def require_admin(
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    """Return the JWT payload when the caller is an admin, else 403."""
    user_id = current_user.get("sub") or current_user.get("id")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized"
        )

    email = (current_user.get("email") or "").strip().lower()
    if email and email in admin_emails():
        return current_user

    # Imported lazily: subscription_service pulls in the Supabase REST client
    # and we do not want that on the import path of every router that only
    # needs the email allowlist.
    from app.services.subscription_service import subscription_service

    if await subscription_service._is_admin(str(user_id)):
        return current_user

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required"
    )
