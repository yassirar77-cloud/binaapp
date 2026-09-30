"""TikTok publishing — the pure rules and the admin-guarded routes.

Covers:
- Fernet token vault round trip; key derivation from the client secret.
- Chunk planning against the Media Transfer Guide rules.
- Content Sharing Guidelines validation (privacy required, options honoured,
  branded content never private, caption limits, duration cap).
- post_info construction honouring creator_info disabled interactions and
  the photo-post field set.
- status/fetch payload → row patch mapping.
- OAuth state checks (unknown, other user, expired).
- Route guard: non-admins get 403; admins reach the config endpoint; the
  media endpoint rejects malformed keys without touching storage.

Every TikTok / Supabase call is mocked — no network.
"""

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch

import pytest

from app.services.social import tiktok_accounts, tiktok_client, tiktok_publisher, token_vault
from app.services.social.tiktok_client import MB, ChunkPlan, TikTokAPIError, plan_chunks
from app.services.social.tiktok_publisher import PostRequest, apply_status_payload, build_post_info, validate_post


# --------------------------------------------------------------------------
# token vault
# --------------------------------------------------------------------------

class TestTokenVault:
    def test_round_trip_with_derived_key(self, monkeypatch):
        from app.core.config import settings

        monkeypatch.setattr(settings, "TIKTOK_TOKEN_ENCRYPTION_KEY", "")
        monkeypatch.setattr(settings, "TIKTOK_CLIENT_SECRET", "super-secret")
        cipher = token_vault.encrypt_token("act.abc123")
        assert cipher != "act.abc123"
        assert "act.abc123" not in cipher
        assert token_vault.decrypt_token(cipher) == "act.abc123"

    def test_explicit_key_wins_and_wrong_key_fails(self, monkeypatch):
        from cryptography.fernet import Fernet

        from app.core.config import settings

        monkeypatch.setattr(settings, "TIKTOK_CLIENT_SECRET", "irrelevant")
        monkeypatch.setattr(settings, "TIKTOK_TOKEN_ENCRYPTION_KEY", Fernet.generate_key().decode())
        cipher = token_vault.encrypt_token("rft.xyz")
        monkeypatch.setattr(settings, "TIKTOK_TOKEN_ENCRYPTION_KEY", Fernet.generate_key().decode())
        with pytest.raises(token_vault.TokenVaultError):
            token_vault.decrypt_token(cipher)

    def test_unconfigured_vault_raises(self, monkeypatch):
        from app.core.config import settings

        monkeypatch.setattr(settings, "TIKTOK_TOKEN_ENCRYPTION_KEY", "")
        monkeypatch.setattr(settings, "TIKTOK_CLIENT_SECRET", "")
        with pytest.raises(token_vault.TokenVaultError):
            token_vault.encrypt_token("x")


# --------------------------------------------------------------------------
# chunk planning
# --------------------------------------------------------------------------

class TestChunkPlan:
    def test_small_video_is_one_whole_chunk(self):
        plan = plan_chunks(3 * MB)
        assert plan == ChunkPlan(3 * MB, 3 * MB, 1)
        assert plan.ranges() == [(0, 3 * MB - 1)]

    def test_medium_video_uses_default_chunks_and_merges_remainder(self):
        size = 27 * MB + 123
        plan = plan_chunks(size)
        assert plan.chunk_size == 10 * MB
        assert plan.total_chunk_count == 2  # floor(27.0/10)
        ranges = plan.ranges()
        assert ranges[0] == (0, 10 * MB - 1)
        assert ranges[-1] == (10 * MB, size - 1)  # final chunk absorbs 17 MB + 123 B
        assert ranges[-1][1] - ranges[-1][0] + 1 <= 128 * MB

    def test_chunk_count_never_exceeds_1000(self):
        size = 3 * 1024 * MB  # 3 GB
        plan = plan_chunks(size, preferred_chunk=5 * MB)
        assert plan.total_chunk_count <= 1000
        assert 5 * MB <= plan.chunk_size <= 64 * MB

    def test_source_info_shape(self):
        info = plan_chunks(12 * MB).source_info()
        assert info == {
            "source": "FILE_UPLOAD",
            "video_size": 12 * MB,
            "chunk_size": 10 * MB,
            "total_chunk_count": 1,
        }

    def test_rejects_bad_sizes(self):
        with pytest.raises(ValueError):
            plan_chunks(0)
        with pytest.raises(ValueError):
            plan_chunks(5 * 1024 * MB)


# --------------------------------------------------------------------------
# validation + post_info
# --------------------------------------------------------------------------

CREATOR = {
    "creator_nickname": "BinaApp",
    "privacy_level_options": ["PUBLIC_TO_EVERYONE", "MUTUAL_FOLLOW_FRIENDS", "SELF_ONLY"],
    "comment_disabled": False,
    "duet_disabled": True,
    "stitch_disabled": False,
    "max_video_post_duration_sec": 600,
}


def _req(**over):
    base = dict(mode="direct", media_type="video", title="Hello #BinaApp", privacy_level="SELF_ONLY")
    base.update(over)
    return PostRequest(**base)


class TestValidation:
    def test_privacy_required_for_direct_post(self):
        errors = validate_post(_req(privacy_level=None), CREATOR)
        assert any("privacy" in e.lower() for e in errors)

    def test_privacy_must_be_one_of_creator_options(self):
        errors = validate_post(_req(privacy_level="FOLLOWER_OF_CREATOR"), CREATOR)
        assert errors and "not available" in errors[0]

    def test_branded_content_cannot_be_private(self):
        errors = validate_post(_req(privacy_level="SELF_ONLY", brand_content_toggle=True), CREATOR)
        assert "Branded content visibility cannot be set to private." in errors

    def test_caption_limit_is_utf16_units(self):
        emoji_caption = "😀" * 1101  # 2202 UTF-16 units
        assert validate_post(_req(title=emoji_caption), CREATOR)
        assert not validate_post(_req(title="😀" * 1100), CREATOR)

    def test_photo_limits(self):
        assert validate_post(_req(media_type="photo", title="x" * 91), CREATOR)
        assert validate_post(_req(media_type="photo", title="ok", description="y" * 4001), CREATOR)
        assert not validate_post(_req(media_type="photo", title="ok", description="fine"), CREATOR)

    def test_duration_checked_against_creator_cap(self):
        assert validate_post(_req(duration_sec=601), CREATOR)
        assert not validate_post(_req(duration_sec=600), CREATOR)

    def test_inbox_mode_needs_no_privacy(self):
        assert validate_post(_req(mode="inbox", privacy_level=None), CREATOR) == []


class TestBuildPostInfo:
    def test_video_post_info_honours_creator_disabled_interactions(self):
        req = _req(disable_comment=False, disable_duet=False, disable_stitch=False, is_aigc=True,
                   brand_organic_toggle=True, video_cover_timestamp_ms=1500)
        info = build_post_info(req, CREATOR)
        assert info["privacy_level"] == "SELF_ONLY"
        assert info["disable_comment"] is False
        assert info["disable_duet"] is True  # creator has duet disabled → forced
        assert info["disable_stitch"] is False
        assert info["is_aigc"] is True
        assert info["brand_organic_toggle"] is True
        assert "brand_content_toggle" not in info
        assert info["video_cover_timestamp_ms"] == 1500

    def test_photo_post_info_has_no_duet_or_stitch(self):
        req = _req(media_type="photo", title="Title", description="Desc", disable_comment=False)
        info = build_post_info(req, CREATOR)
        assert info == {
            "title": "Title",
            "privacy_level": "SELF_ONLY",
            "disable_comment": False,
            "description": "Desc",
        }


# --------------------------------------------------------------------------
# status mapping
# --------------------------------------------------------------------------

class TestStatusMapping:
    def test_processing(self):
        patch_ = apply_status_payload({}, {"status": "PROCESSING_UPLOAD", "uploaded_bytes": 1024})
        assert patch_["status"] == "processing"
        assert patch_["uploaded_bytes"] == 1024
        assert "finished_at" not in patch_

    def test_published_with_post_ids(self):
        patch_ = apply_status_payload({}, {"status": "PUBLISH_COMPLETE", "publicaly_available_post_id": [7]})
        assert patch_["status"] == "published"
        assert patch_["public_post_ids"] == [7]
        assert patch_["finished_at"]

    def test_failed_carries_human_reason(self):
        patch_ = apply_status_payload({}, {"status": "FAILED", "fail_reason": "spam_risk_unaudited_client"})
        assert patch_["status"] == "failed"
        assert patch_["fail_reason"] == "spam_risk_unaudited_client"
        assert "Only you" in patch_["error"]

    def test_inbox_terminal(self):
        assert apply_status_payload({}, {"status": "SEND_TO_USER_INBOX"})["status"] == "sent_to_inbox"

    def test_unaudited_api_error_is_explained(self):
        exc = TikTokAPIError("unaudited_client_can_only_post_to_private_accounts", "x")
        assert "SELF_ONLY" in tiktok_publisher.humanize_api_error(exc)


# --------------------------------------------------------------------------
# OAuth state
# --------------------------------------------------------------------------

class TestOAuthState:
    NOW = datetime(2026, 9, 30, 12, 0, tzinfo=timezone.utc)

    def _row(self, **over):
        row = {
            "state": "abc",
            "user_id": "admin-1",
            "redirect_uri": "https://binaapp.my/api/tiktok/callback",
            "expires_at": (self.NOW + timedelta(minutes=5)).isoformat(),
        }
        row.update(over)
        return row

    def test_valid_state_returns_redirect_uri(self):
        assert tiktok_accounts.check_oauth_state(self._row(), "admin-1", self.NOW).endswith("/api/tiktok/callback")

    def test_unknown_state(self):
        with pytest.raises(tiktok_accounts.OAuthStateError):
            tiktok_accounts.check_oauth_state(None, "admin-1", self.NOW)

    def test_other_user(self):
        with pytest.raises(tiktok_accounts.OAuthStateError):
            tiktok_accounts.check_oauth_state(self._row(), "someone-else", self.NOW)

    def test_expired(self):
        row = self._row(expires_at=(self.NOW - timedelta(seconds=1)).isoformat())
        with pytest.raises(tiktok_accounts.OAuthStateError):
            tiktok_accounts.check_oauth_state(row, "admin-1", self.NOW)

    def test_authorize_url_has_required_params(self):
        url = tiktok_client.build_authorize_url("ck", "https://binaapp.my/api/tiktok/callback", "st4te")
        assert url.startswith("https://www.tiktok.com/v2/auth/authorize/?")
        assert "client_key=ck" in url
        assert "scope=user.info.basic%2Cvideo.upload%2Cvideo.publish" in url
        assert "response_type=code" in url
        assert "redirect_uri=https%3A%2F%2Fbinaapp.my%2Fapi%2Ftiktok%2Fcallback" in url
        assert "state=st4te" in url

    def test_public_view_never_leaks_tokens(self):
        view = tiktok_accounts.public_view(
            {"id": "1", "open_id": "o", "access_token_enc": "gAAA", "refresh_token_enc": "gAAA", "scopes": "a,b"}
        )
        assert "access_token_enc" not in view and "refresh_token_enc" not in view
        assert view["scopes"] == ["a", "b"]


# --------------------------------------------------------------------------
# routes
# --------------------------------------------------------------------------

class TestRoutes:
    def test_non_admin_gets_403(self, client, auth_headers):
        with patch("app.services.subscription_service.subscription_service._is_admin", new=AsyncMock(return_value=False)), \
             patch("app.core.admin.admin_emails", return_value={"founder@binaapp.my"}):
            resp = client.get("/api/v1/social/tiktok/config", headers=auth_headers)
        assert resp.status_code == 403

    def test_no_token_gets_401(self, client):
        assert client.get("/api/v1/social/tiktok/config").status_code in (401, 403)

    def test_admin_by_role_reads_config(self, client, auth_headers):
        with patch("app.services.subscription_service.subscription_service._is_admin", new=AsyncMock(return_value=True)), \
             patch("app.core.admin.admin_emails", return_value=set()):
            resp = client.get("/api/v1/social/tiktok/config", headers=auth_headers)
        assert resp.status_code == 200
        body = resp.json()
        assert body["scopes"] == ["user.info.basic", "video.upload", "video.publish"]
        assert body["limits"]["video_title_max"] == 2200
        assert "music_usage_confirmation" in body["policy_links"]

    def test_admin_by_email_reads_config(self, client, auth_headers, test_user_email):
        with patch("app.core.admin.admin_emails", return_value={test_user_email}):
            resp = client.get("/api/v1/social/tiktok/config", headers=auth_headers)
        assert resp.status_code == 200

    def test_oauth_start_requires_configuration(self, client, auth_headers, test_user_email, monkeypatch):
        from app.core.config import settings

        monkeypatch.setattr(settings, "TIKTOK_CLIENT_KEY", "")
        with patch("app.core.admin.admin_emails", return_value={test_user_email}):
            resp = client.post("/api/v1/social/tiktok/oauth/start", headers=auth_headers)
        assert resp.status_code == 503
        assert resp.json()["detail"]["error"] == "tiktok_not_configured"

    def test_oauth_start_returns_authorize_url(self, client, auth_headers, test_user_email, monkeypatch):
        from app.core.config import settings

        monkeypatch.setattr(settings, "TIKTOK_CLIENT_KEY", "ck")
        monkeypatch.setattr(settings, "TIKTOK_CLIENT_SECRET", "cs")
        monkeypatch.setattr(settings, "TIKTOK_REDIRECT_URI", "https://binaapp.my/api/tiktok/callback")
        with patch("app.core.admin.admin_emails", return_value={test_user_email}), \
             patch("app.services.social.tiktok_accounts.create_oauth_state", new=AsyncMock(return_value="S1")):
            resp = client.post("/api/v1/social/tiktok/oauth/start", headers=auth_headers)
        assert resp.status_code == 200
        assert "state=S1" in resp.json()["authorize_url"]
        assert resp.json()["redirect_uri"] == "https://binaapp.my/api/tiktok/callback"

    def test_callback_rejects_bad_state(self, client, auth_headers, test_user_email, monkeypatch):
        from app.core.config import settings

        monkeypatch.setattr(settings, "TIKTOK_CLIENT_KEY", "ck")
        monkeypatch.setattr(settings, "TIKTOK_CLIENT_SECRET", "cs")
        with patch("app.core.admin.admin_emails", return_value={test_user_email}), \
             patch("app.services.social.tiktok_accounts.db_select", new=AsyncMock(return_value=[])):
            resp = client.post(
                "/api/v1/social/tiktok/oauth/callback",
                headers=auth_headers,
                json={"code": "c0de", "state": "nope"},
            )
        assert resp.status_code == 400
        assert resp.json()["detail"]["error"] == "invalid_state"

    def test_account_when_nothing_connected(self, client, auth_headers, test_user_email):
        with patch("app.core.admin.admin_emails", return_value={test_user_email}), \
             patch("app.services.social.tiktok_accounts.get_account", new=AsyncMock(return_value=None)):
            resp = client.get("/api/v1/social/tiktok/account", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json() == {"connected": False, "account": None}

    def test_media_endpoint_rejects_malformed_keys(self, client):
        # Anything that is not <32 hex>.<jpg|jpeg|png|webp> never reaches storage.
        assert client.get("/api/v1/social/tiktok/media/not-a-key.jpg").status_code == 404
        assert client.get("/api/v1/social/tiktok/media/" + "a" * 32 + ".svg").status_code == 404
        assert client.get("/api/v1/social/tiktok/media/" + "A" * 32 + ".jpg").status_code == 404
