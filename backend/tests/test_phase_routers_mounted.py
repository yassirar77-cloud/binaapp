"""
The AI Control System phase 2 and phase 3 routers must be mounted.

Each of `ai_phase2_router.setup_phase2_routes` and
`ai_phase3_router.setup_phase3_routes` was shipped with a docstring saying
"add these two lines to main.py" — and the lines were never added. Every
frontend page built on those endpoints (/admin, /founder, /monitor,
/webhooks, /sla, /trust-score, /notifications, /referrals, /ai-support,
/ai-chat-settings, /website-health, /website-rebuild) received a 404 for
every request, with no type-check, lint or build failure to show for it.

This test pins the paths the frontend actually calls, so an accidental
removal of the mount lines fails CI instead of silently blanking a dozen
pages again.
"""

import pytest


# One representative path per frontend page, copied from the frontend's
# fetch calls (frontend/src/app/<page>/page.tsx).
FRONTEND_PATHS = [
    ("GET", "/api/v1/admin/dashboard"),                # /admin
    ("GET", "/api/v1/admin/disputes/escalated"),       # /admin
    ("GET", "/api/v1/founder/overview"),               # /founder
    ("GET", "/api/v1/monitor/events"),                 # /monitor
    ("GET", "/api/v1/webhooks"),                       # /webhooks
    ("GET", "/api/v1/sla/my-sla"),                     # /sla
    ("GET", "/api/v1/trust/my-score"),                 # /trust-score
    ("GET", "/api/v1/notifications"),                  # /notifications
    ("GET", "/api/v1/referrals/stats"),                # /referrals
    ("POST", "/api/v1/ai-chat/start"),                 # /ai-support/chat
    ("GET", "/api/v1/ai-chat-settings/{website_id}"),  # /ai-chat-settings
    ("POST", "/api/v1/website-health/scan/{website_id}"),  # /website-health
    ("GET", "/api/v1/website-rebuild/{website_id}"),   # /website-rebuild
]


@pytest.fixture(scope="module")
def openapi_paths():
    from app.main import app

    return app.openapi()["paths"]


@pytest.mark.parametrize("method,path", FRONTEND_PATHS)
def test_frontend_path_is_mounted(openapi_paths, method, path):
    assert path in openapi_paths, f"{path} is not mounted on the app"
    assert method.lower() in openapi_paths[path], (
        f"{method} {path} is not mounted (have {sorted(openapi_paths[path])})"
    )


def test_unmounted_path_fails_this_check():
    """Sanity: the assertion above is strict, not vacuous."""
    from app.main import app

    assert "/api/v1/this-route-does-not-exist" not in app.openapi()["paths"]
