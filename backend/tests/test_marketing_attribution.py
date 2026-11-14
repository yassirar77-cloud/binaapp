"""Marketing attribution (migration 067): normalisation and rollups."""
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.v1.endpoints import marketing
from app.core.security import get_current_user
from app.services.marketing_attribution import (
    canonical_source,
    clean_label,
    normalize_attribution,
    profile_columns,
    referrer_domain,
    summarize,
)


class TestCleaning:
    def test_label_is_lowercased_and_bounded(self):
        assert clean_label("  TikTok Ads! ") == "tiktok-ads"
        assert len(clean_label("x" * 500)) == 60

    def test_label_rejects_non_strings(self):
        assert clean_label(None) == ""
        assert clean_label({"$ne": 1}) == ""

    def test_label_cannot_carry_markup_or_sql(self):
        assert clean_label("<script>alert(1)</script>") == "script-alert-1-script"
        assert clean_label("a'; DROP TABLE profiles;--") == "a-drop-table-profiles"

    def test_referrer_domain(self):
        assert referrer_domain("https://www.tiktok.com/@x/video/1?a=b") == "tiktok.com"
        assert referrer_domain("m.facebook.com") == "m.facebook.com"
        assert referrer_domain("") == ""
        assert referrer_domain("garbage") == ""

    def test_own_site_is_not_a_referrer(self):
        assert referrer_domain("https://binaapp.my/login") == ""
        assert referrer_domain("https://kedai.binaapp.my/") == ""

    def test_aliases_collapse_to_one_channel(self):
        assert canonical_source("m.facebook.com") == "facebook"
        assert canonical_source("fb") == "facebook"
        assert canonical_source("wa.me") == "whatsapp"
        assert canonical_source("google.com.my") == "google"
        assert canonical_source("kedaikopi.com") == "kedaikopi.com"


class TestNormalize:
    def test_utm_source_wins_over_referrer(self):
        a = normalize_attribution(
            {"utm_source": "TikTok", "utm_campaign": "Warung Demo", "referrer": "https://google.com/"}
        )
        assert a["source"] == "tiktok"
        assert a["campaign"] == "warung-demo"
        assert a["referrer"] == "google.com"

    def test_referrer_only_is_organic(self):
        a = normalize_attribution({"referrer": "https://www.google.com/search?q=x"})
        assert (a["source"], a["medium"]) == ("google", "organic")

    def test_referral_code(self):
        a = normalize_attribution({"ref": "ALI123"})
        assert (a["source"], a["medium"], a["campaign"]) == ("referral", "referral", "ali123")

    def test_nothing_is_direct(self):
        for raw in (None, {}, {"referrer": "https://binaapp.my/"}, "junk"):
            assert normalize_attribution(raw)["source"] == "direct"

    def test_landing_path_drops_query(self):
        a = normalize_attribution({"landing_path": "/register?token=secret#x"})
        assert a["landing_path"] == "/register"

    def test_profile_columns(self):
        cols = profile_columns(normalize_attribution({"utm_source": "ig"}))
        assert cols["signup_source"] == "instagram"
        assert cols["signup_campaign"] is None


class TestSummarize:
    def test_rolls_up_per_source(self):
        visits = [
            {"source": "tiktok", "visits": 40},
            {"source": "tiktok", "visits": 10},
            {"source": "direct", "visits": 5},
        ]
        signups = [
            {"id": "a", "signup_source": "tiktok"},
            {"id": "b", "signup_source": "tiktok"},
            {"id": "c", "signup_source": None},
        ]
        rows = summarize(visits, signups, {"a"})
        by = {r["source"]: r for r in rows}
        assert rows[0]["source"] == "tiktok"
        assert by["tiktok"] == {
            "source": "tiktok", "visits": 50, "signups": 2, "paid": 1, "signup_rate": 4.0,
        }
        assert by["direct"]["signups"] == 0
        assert by["unknown"]["signup_rate"] is None


def _client(monkeypatch, recorded):
    async def fake_record(raw):
        recorded.append(raw)
        return True

    monkeypatch.setattr(marketing, "record_visit", fake_record)
    app = FastAPI()
    app.include_router(marketing.router, prefix="/api/v1")
    return app, TestClient(app)


class TestVisitEndpoint:
    def test_counts_a_normal_visit(self, monkeypatch):
        recorded = []
        _, client = _client(monkeypatch, recorded)
        r = client.post(
            "/api/v1/marketing/visit",
            json={"utm_source": "tiktok"},
            headers={"user-agent": "Mozilla/5.0 (iPhone)"},
        )
        assert r.status_code == 204
        assert recorded and recorded[0]["utm_source"] == "tiktok"

    def test_drops_dnt_gpc_and_bots(self, monkeypatch):
        recorded = []
        _, client = _client(monkeypatch, recorded)
        for headers in (
            {"user-agent": "Mozilla/5.0", "dnt": "1"},
            {"user-agent": "Mozilla/5.0", "sec-gpc": "1"},
            {"user-agent": "Googlebot/2.1"},
        ):
            assert client.post("/api/v1/marketing/visit", json={}, headers=headers).status_code == 204
        assert recorded == []

    def test_rejects_oversized_fields(self, monkeypatch):
        _, client = _client(monkeypatch, [])
        r = client.post("/api/v1/marketing/visit", json={"utm_source": "x" * 5000})
        assert r.status_code == 422


class TestSummaryEndpoint:
    def test_requires_login(self, monkeypatch):
        _, client = _client(monkeypatch, [])
        assert client.get("/api/v1/marketing/summary").status_code in (401, 403)

    def test_non_admin_is_refused(self, monkeypatch):
        app, client = _client(monkeypatch, [])

        async def not_admin(_user_id):
            return False

        from app.services.subscription_service import subscription_service

        monkeypatch.setattr(subscription_service, "_is_admin", not_admin)
        app.dependency_overrides[get_current_user] = lambda: {"sub": "u1", "email": "someone@example.com"}
        assert client.get("/api/v1/marketing/summary").status_code == 403


class TestReferralCode:
    def test_well_formed_code_is_kept_upper_cased(self):
        a = normalize_attribution({"ref": " bina-ab12-cd34 "})
        assert a["ref_code"] == "BINA-AB12-CD34"
        assert profile_columns(a)["signup_ref_code"] == "BINA-AB12-CD34"

    def test_malformed_code_is_dropped(self):
        for bad in ("ALI123", "BINA-AB12", "BINA-AB12-CD34; DROP", None, 5):
            assert normalize_attribution({"ref": bad})["ref_code"] == ""
        assert profile_columns(normalize_attribution({"ref": "x"}))["signup_ref_code"] is None
