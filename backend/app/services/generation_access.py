"""Who may start a generation, and how often.

``/api/generate/start`` used to read ``user_id`` and ``email`` from the
JSON body. Anyone could start builds charged to another merchant's
plan, and the legacy founder bypass (``UNLIMITED_ACCESS_EMAILS``) was
granted to whoever typed a founder's address into the body. The caller
is now the subject of a verified Bearer token, and the body's identity
fields are ignored.

Every start is also rate limited, before any model is called:

- per user: ``GENERATE_RATE_USER_PER_10MIN`` starts in 10 minutes and
  ``GENERATE_RATE_USER_PER_DAY`` in 24 hours;
- per client IP: ``GENERATE_RATE_IP_PER_HOUR`` starts in an hour (several
  accounts from one machine);
- per user: at most ``GENERATE_MAX_CONCURRENT`` jobs still processing,
  counted from ``generation_jobs`` so a restart does not reset it.

Admins (``subscription_service._is_admin``) skip the per-user limits.
The windows are in-process memory: Render runs one uvicorn worker, so
one process sees every request. A restart forgets the windows, which
errs on the side of letting a merchant through; the concurrency cap is
read from the database and survives it.

``GENERATE_ALLOW_ANONYMOUS=true`` restores tokenless starts as user
"anonymous" (emergency switch only). Even then the body's identity is
never trusted.
"""

from __future__ import annotations

import os
import threading
import time
from collections import defaultdict, deque
from dataclasses import dataclass
from typing import Any, Deque, Dict, Mapping, Optional, Tuple

from loguru import logger

ANONYMOUS = "anonymous"

AUTH_REQUIRED_MESSAGE = "Sila log masuk semula untuk menjana website."
RATE_LIMITED_MESSAGE = "Terlalu banyak penjanaan dalam masa singkat. Sila cuba lagi dalam {minutes} minit."
CONCURRENT_MESSAGE = "Anda sudah ada {n} penjanaan sedang berjalan. Tunggu sehingga ia siap, kemudian cuba lagi."
NOT_YOUR_JOB_MESSAGE = "Pratonton ini bukan milik akaun anda."


def _env_int(name: str, default: int) -> int:
    try:
        return max(0, int(os.getenv(name, str(default))))
    except (TypeError, ValueError):
        return default


def allow_anonymous() -> bool:
    return os.getenv("GENERATE_ALLOW_ANONYMOUS", "false").strip().lower() in ("1", "true", "yes", "on")


def limits() -> Dict[str, int]:
    """Read at call time so env flips and test patches take effect."""
    return {
        "user_per_10min": _env_int("GENERATE_RATE_USER_PER_10MIN", 5),
        "user_per_day": _env_int("GENERATE_RATE_USER_PER_DAY", 30),
        "ip_per_hour": _env_int("GENERATE_RATE_IP_PER_HOUR", 20),
        "max_concurrent": _env_int("GENERATE_MAX_CONCURRENT", 2),
    }


# ---------------------------------------------------------------------------
# Identity
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Identity:
    user_id: str
    email: str = ""
    authenticated: bool = True

    @property
    def anonymous(self) -> bool:
        return not self.authenticated


def bearer_token(headers: Mapping[str, str]) -> Optional[str]:
    raw = (headers.get("authorization") or headers.get("Authorization") or "").strip()
    if not raw.lower().startswith("bearer "):
        return None
    token = raw[7:].strip()
    if not token or token in ("undefined", "null", "None"):
        return None
    return token


def _email_of(payload: Dict[str, Any]) -> str:
    email = payload.get("email")
    if not email and isinstance(payload.get("user_metadata"), dict):
        email = payload["user_metadata"].get("email")
    return str(email or "").strip()


async def verify_token(token: str) -> Optional[Dict[str, Any]]:
    """The token's payload when it verifies (our JWT secret, then the
    Supabase secret), else None. Same rules as get_current_user."""
    from fastapi.security import HTTPAuthorizationCredentials

    from app.core.security import get_optional_current_user
    try:
        payload = await get_optional_current_user(HTTPAuthorizationCredentials(scheme="Bearer", credentials=token))
    except Exception as err:  # pragma: no cover - defensive
        logger.warning(f"🔐 Token verification raised: {err}")
        return None
    if isinstance(payload, dict) and payload.get("sub"):
        return payload
    return None


async def resolve_identity(headers: Mapping[str, str], body: Optional[Mapping[str, Any]] = None) -> Optional[Identity]:
    """The verified caller, or None when there is none (the endpoint then
    answers 401). A body that names a different user is logged: it is
    either a stale client or an impersonation attempt."""
    token = bearer_token(headers)
    payload = await verify_token(token) if token else None
    claimed = str((body or {}).get("user_id") or "").strip()
    if payload:
        ident = Identity(user_id=str(payload["sub"]), email=_email_of(payload), authenticated=True)
        if claimed and claimed not in (ident.user_id, ANONYMOUS):
            logger.warning(
                f"🔐 GENERATE_IDENTITY_MISMATCH body user_id={claimed!r} token sub={ident.user_id!r}: using the token"
            )
        return ident
    if allow_anonymous():
        if claimed and claimed != ANONYMOUS:
            logger.warning(f"🔐 Tokenless start claimed user_id={claimed!r}: treated as anonymous")
        return Identity(user_id=ANONYMOUS, email="", authenticated=False)
    logger.warning(
        f"🔐 GENERATE_AUTH_REQUIRED {'invalid' if token else 'missing'} token"
        + (f" (body claimed user_id={claimed!r})" if claimed else "")
    )
    return None


def apply_identity(body: Dict[str, Any], identity: Identity) -> Dict[str, Any]:
    """The body with its identity fields replaced by the verified ones, so
    the job row, the stashed request (refine) and the input payload all
    carry who actually asked."""
    return {**body, "user_id": identity.user_id, "email": identity.email}


# ---------------------------------------------------------------------------
# Client IP
# ---------------------------------------------------------------------------

def client_ip(headers: Mapping[str, str], fallback: Optional[str] = None) -> str:
    """The client address behind Render's proxy. Proxies APPEND to
    X-Forwarded-For, so its last entry is the one our edge added; a
    client-supplied first entry is ignored. The per-IP limit is defence in
    depth: the per-user limit, keyed on the verified token, is the one
    that cannot be spoofed."""
    for name in ("cf-connecting-ip", "true-client-ip"):
        value = (headers.get(name) or "").strip()
        if value:
            return value
    xff = headers.get("x-forwarded-for") or headers.get("X-Forwarded-For") or ""
    parts = [p.strip() for p in xff.split(",") if p.strip()]
    if parts:
        return parts[-1]
    return fallback or "unknown"


# ---------------------------------------------------------------------------
# Sliding windows
# ---------------------------------------------------------------------------

class SlidingWindow:
    """Timestamps per key; ``allowed`` answers for a window and a cap."""

    def __init__(self) -> None:
        self._hits: Dict[str, Deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def _prune(self, key: str, now: float, horizon: float) -> Deque[float]:
        q = self._hits[key]
        while q and q[0] <= now - horizon:
            q.popleft()
        return q

    def check(self, key: str, window_seconds: float, cap: int, *, now: Optional[float] = None,
              horizon: float = 86400.0) -> Tuple[bool, int]:
        """(allowed, retry_after_seconds)."""
        if cap <= 0:
            return True, 0
        now = time.time() if now is None else now
        with self._lock:
            q = self._prune(key, now, max(horizon, window_seconds))
            recent = [t for t in q if t > now - window_seconds]
            if len(recent) < cap:
                return True, 0
            oldest = recent[-cap]
            return False, max(1, int(oldest + window_seconds - now) + 1)

    def record(self, key: str, *, now: Optional[float] = None) -> None:
        now = time.time() if now is None else now
        with self._lock:
            self._hits[key].append(now)

    def reset(self) -> None:
        with self._lock:
            self._hits.clear()


_starts = SlidingWindow()


def reset_windows() -> None:
    """For tests."""
    _starts.reset()


@dataclass
class Decision:
    allowed: bool
    reason: str = ""
    retry_after: int = 0
    message: str = ""
    status: int = 200

    def response_content(self) -> Dict[str, Any]:
        return {"success": False, "error": self.reason, "message": self.message, "retry_after": self.retry_after}


def _minutes(seconds: int) -> int:
    return max(1, (seconds + 59) // 60)


def check_rate(identity: Identity, ip: str, *, is_admin: bool = False, now: Optional[float] = None) -> Decision:
    """Window limits for one start. Nothing is recorded here: call
    ``record_start`` once the job really exists, so a 400/409 on the
    merchant's input never burns their allowance."""
    lim = limits()
    ok, retry = _starts.check(f"ip:{ip}", 3600, lim["ip_per_hour"], now=now)
    if not ok:
        logger.warning(f"🚦 GENERATE_RATE_LIMITED ip={ip} cap={lim['ip_per_hour']}/h retry={retry}s")
        return Decision(False, "rate_limited", retry, RATE_LIMITED_MESSAGE.format(minutes=_minutes(retry)), 429)
    if is_admin:
        return Decision(True)
    key = f"user:{identity.user_id}"
    for window, cap, label in ((600, lim["user_per_10min"], "10min"), (86400, lim["user_per_day"], "day")):
        ok, retry = _starts.check(key, window, cap, now=now)
        if not ok:
            logger.warning(f"🚦 GENERATE_RATE_LIMITED user={identity.user_id} cap={cap}/{label} retry={retry}s")
            return Decision(False, "rate_limited", retry, RATE_LIMITED_MESSAGE.format(minutes=_minutes(retry)), 429)
    return Decision(True)


def record_start(identity: Identity, ip: str, *, now: Optional[float] = None) -> None:
    _starts.record(f"ip:{ip}", now=now)
    _starts.record(f"user:{identity.user_id}", now=now)


def check_concurrency(identity: Identity, processing_jobs: int, *, is_admin: bool = False) -> Decision:
    cap = limits()["max_concurrent"]
    if is_admin or identity.anonymous or cap <= 0 or processing_jobs < cap:
        return Decision(True)
    logger.warning(f"🚦 GENERATE_CONCURRENCY_LIMITED user={identity.user_id} processing={processing_jobs} cap={cap}")
    return Decision(False, "too_many_running", 60, CONCURRENT_MESSAGE.format(n=processing_jobs), 429)


def count_processing_jobs(supabase: Any, user_id: str, *, stale_seconds: int = 1800) -> int:
    """Jobs of this user still 'processing' and touched within
    ``stale_seconds`` (a row abandoned by a dead worker does not lock the
    merchant out). 0 when the table cannot be read."""
    if not supabase or not user_id or user_id == ANONYMOUS:
        return 0
    try:
        from datetime import datetime, timedelta
        cutoff = (datetime.now() - timedelta(seconds=stale_seconds)).isoformat()
        res = (
            supabase.table("generation_jobs")
            .select("job_id")
            .eq("user_id", user_id)
            .eq("status", "processing")
            .gte("updated_at", cutoff)
            .limit(10)
            .execute()
        )
        return len(res.data or [])
    except Exception as err:
        logger.warning(f"🚦 Could not count running jobs for {user_id}: {err}")
        return 0
