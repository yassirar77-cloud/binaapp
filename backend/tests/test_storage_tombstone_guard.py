"""Backend C: DELETE .../.deleted 400 on every publish."""
from unittest.mock import AsyncMock, patch

import pytest

from app.services.storage_service import StorageService, TOMBSTONE_FILENAME


@pytest.mark.asyncio
async def test_tombstone_is_only_deleted_when_it_exists():
    svc = StorageService.__new__(StorageService)
    svc.bucket_name = "websites"
    svc.supabase = AsyncMock()
    svc.supabase.storage_object_exists = AsyncMock(return_value=False)
    svc.supabase.delete_file = AsyncMock(return_value=True)
    svc.supabase.upload_file = AsyncMock(return_value="https://x/1")
    with patch.object(StorageService, "_invalidate", create=True, return_value=None):
        try:
            await svc.publish_website(subdomain="nadira", html_content="<html></html>", website_id="w", user_id="u")
        except Exception:
            pass  # other collaborators are not the subject here
    svc.supabase.delete_file.assert_not_called()

    svc.supabase.storage_object_exists = AsyncMock(return_value=True)
    try:
        await svc.publish_website(subdomain="nadira", html_content="<html></html>", website_id="w", user_id="u")
    except Exception:
        pass
    svc.supabase.delete_file.assert_awaited_once_with("websites", f"nadira/{TOMBSTONE_FILENAME}")
