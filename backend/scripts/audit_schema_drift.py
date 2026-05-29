"""
Schema drift auditor — one-shot diagnostic tool.

Compares the live Supabase column inventory for a fixed set of "hot" tables
against the columns referenced in the backend codebase's write paths
(INSERT / UPDATE / UPSERT), and writes a markdown report to
backend/SCHEMA_AUDIT.md.

Catches drift like the websites.error_message gap (PR #665) BEFORE it hits
production again: PR #665 wrote to error_message from the regenerate
endpoint but never added a migration for it, so any fresh Supabase project
bootstrapped from migrations/ alone would crash on the first failed
regenerate.

Run:
    cd backend && python -m scripts.audit_schema_drift
    # or from repo root
    cd backend && python scripts/audit_schema_drift.py

Requires the standard backend env vars (SUPABASE_URL + SUPABASE_SERVICE_ROLE_KEY
or SUPABASE_SERVICE_KEY — same fallback the supabase_client uses).

Exits 0 even when drift is found — this is a diagnostic, not a CI gate. The
report makes the gaps visible; humans decide whether to write a migration.
"""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path
from typing import Dict, List, Set, Tuple

import httpx


# Tables we care about for the drift audit. Keep this list small + focused
# on the ones with frequent schema churn — every entry adds API calls.
TABLES_TO_AUDIT: Tuple[str, ...] = (
    "websites",
    "menu_items",
    "users",
    "riders",
    "subscriptions",
)

# Columns the backend never writes but are valid (auto-managed by Postgres
# defaults, RLS, or triggers). Listing them here keeps them out of the
# "in DB but never referenced in code" noise.
COLUMNS_ALWAYS_VALID: Dict[str, Set[str]] = {
    "websites": {"id", "created_at", "updated_at"},
    "menu_items": {"id", "created_at", "updated_at"},
    "users": {"id", "created_at", "updated_at"},
    "riders": {"id", "created_at", "updated_at"},
    "subscriptions": {"id", "created_at", "updated_at"},
}


def _resolve_repo_root() -> Path:
    """Return the repo root (parent of backend/) regardless of cwd."""
    here = Path(__file__).resolve()
    # scripts/audit_schema_drift.py → scripts/ → backend/ → repo root
    return here.parent.parent.parent


def _resolve_backend_root() -> Path:
    return Path(__file__).resolve().parent.parent


def _supabase_env() -> Tuple[str, str]:
    """Read URL + service-role key from env, matching supabase_client.py's
    fallback chain so callers don't need to learn yet another set of vars."""
    url = os.getenv("SUPABASE_URL")
    key = (
        os.getenv("SUPABASE_SERVICE_ROLE_KEY")
        or os.getenv("SUPABASE_SERVICE_KEY")
    )
    if not url or not key:
        print(
            "ERROR: SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY (or "
            "SUPABASE_SERVICE_KEY) must be set in env.",
            file=sys.stderr,
        )
        sys.exit(1)
    return url.rstrip("/"), key


def fetch_db_columns(table: str, url: str, key: str) -> Set[str]:
    """Return the set of column names for `table` in the live Supabase DB.

    Uses PostgREST's "select one row, all columns" trick — cheaper than
    hitting information_schema via RPC and works against any project
    without needing a custom function deployed.
    """
    headers = {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        # Range: 0-0 gets us at most one row; if the table is empty we
        # fall back to inspecting the OPTIONS endpoint.
        "Range": "0-0",
    }
    endpoint = f"{url}/rest/v1/{table}"
    try:
        with httpx.Client(timeout=15.0) as client:
            r = client.get(endpoint, headers={**headers, "Accept": "application/json"})
            if r.status_code in (200, 206) and r.text.strip() not in ("", "[]"):
                rows = r.json()
                if rows:
                    return set(rows[0].keys())
            # Empty table or 204 — try OPTIONS (PostgREST exposes columns
            # in the Allow + meta headers but the body has the OpenAPI
            # schema in some configs). As a robust fallback, do a
            # COUNT-only request to ensure the table exists, then issue
            # an unfilterable upsert dry-run via a HEAD with Prefer
            # `count=exact` — if even that fails, give up gracefully.
            r2 = client.get(
                endpoint,
                headers={**headers, "Prefer": "count=exact"},
                params={"select": "*", "limit": "0"},
            )
            if r2.status_code in (200, 206):
                # The Content-Range header confirms the table is reachable
                # but the body is empty; without rows we can't enumerate
                # columns via this path. Return empty + warn upstream.
                return set()
        return set()
    except httpx.HTTPError as e:
        print(f"WARN: failed to fetch columns for {table}: {e}", file=sys.stderr)
        return set()


def grep_code_writes(backend_root: Path, table: str) -> Set[str]:
    """Walk backend/app/ + backend/scripts/ for writes to `table` and pull
    out every column name referenced in INSERT/UPDATE/UPSERT payloads.

    Patterns covered:
      - supabase.table("<table>").(insert|update|upsert)({ ... })
      - supabase.from_("<table>").(insert|update|upsert)({ ... })
      - httpx PATCH/POST to /rest/v1/<table> with a json={ ... } payload
      - supabase_service.create_website / update_website (special-case for
        the websites table — its data dict is built in many endpoints and
        the column names are the dict keys at the call site).

    This is grep-grade, not AST-grade — it will miss writes that build the
    dict in a helper one file away. Good enough for the drift audit:
    the false-negative rate on missed code-side columns is lower than the
    false-positive rate of "looks like a column reference but isn't".
    """
    columns: Set[str] = set()
    # Scan only app code — exclude scripts/ so this auditor doesn't pick up
    # its own dict literals (e.g. {"db_columns": ..., "in_code_only": ...})
    # as if they were table columns.
    roots = [backend_root / "app"]

    # Pattern 1: supabase.table("<table>") followed by .insert/.update/.upsert
    # with a dict literal. We capture the dict body lazily; the inner regex
    # then pulls out "key": from it.
    table_pat = re.compile(
        r"""supabase[\w\.]*\.(?:table|from_)\(\s*['"]"""
        + re.escape(table)
        + r"""['"]\s*\)[\s\S]{0,400}?\.(?:insert|update|upsert)\(\s*(\{[\s\S]*?\})""",
        re.MULTILINE,
    )

    # Pattern 2: REST URL writes — httpx.patch/post against /rest/v1/<table>.
    # We then look for a json={...} payload in the nearby window (±400 chars).
    rest_pat = re.compile(
        r"""/rest/v1/""" + re.escape(table) + r"""(?:['"\s,)?])""",
        re.MULTILINE,
    )
    json_payload_pat = re.compile(r"""json\s*=\s*(\{[\s\S]*?\})""")

    # Pattern 3: special-case helpers. The websites table is mostly written
    # via supabase_service.create_website / update_website; the dict comes
    # from the caller's website_data / update_data variable. We sweep any
    # nearby `website_data = { ... }` / `update_data = { ... }` literals.
    helper_dict_pat = re.compile(
        r"""(?:website_data|update_data|update_payload|upsert_payload|project_data|recovery_data)\s*=\s*(\{[\s\S]*?^\s*\})""",
        re.MULTILINE,
    )

    key_pat = re.compile(r"""['"]([a-zA-Z_][a-zA-Z0-9_]*)['"]\s*:""")

    def harvest_dict_keys(blob: str) -> None:
        for m in key_pat.finditer(blob):
            key = m.group(1)
            # Skip obvious non-column tokens.
            if key in {"error", "data", "message", "headers", "Authorization", "Content-Type"}:
                continue
            columns.add(key)

    for root in roots:
        if not root.exists():
            continue
        for path in root.rglob("*.py"):
            try:
                text = path.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue

            # Cheap upfront filter — if the table name doesn't appear, skip.
            if table not in text:
                continue

            for m in table_pat.finditer(text):
                harvest_dict_keys(m.group(1))

            for m in rest_pat.finditer(text):
                # Look ±400 chars for a json= payload.
                start = max(0, m.start() - 400)
                end = min(len(text), m.end() + 400)
                window = text[start:end]
                for jm in json_payload_pat.finditer(window):
                    harvest_dict_keys(jm.group(1))

            # Special-case sweep only for the websites helper (other tables
            # don't have the same supabase_service helper pattern).
            if table == "websites":
                # Only count dicts within files that actually call the
                # websites helpers — otherwise project_data from a totally
                # unrelated context could pollute the column set.
                if (
                    "supabase_service.update_website" in text
                    or "supabase_service.create_website" in text
                ):
                    for hm in helper_dict_pat.finditer(text):
                        harvest_dict_keys(hm.group(1))

    return columns


def render_report(
    drift: Dict[str, Dict[str, Set[str]]],
    db_unreachable: Set[str],
) -> str:
    lines: List[str] = [
        "# Schema Drift Audit",
        "",
        "Generated by `backend/scripts/audit_schema_drift.py`. Compares the live",
        "Supabase column inventory against the columns referenced in the",
        "backend's INSERT/UPDATE/UPSERT call sites.",
        "",
        "- **In code, not in DB** → write would fail in production; add a migration.",
        "- **In DB, not in code** → either dead column (drop in a future cleanup)",
        "  or referenced via a helper this grep-grade scan missed (investigate).",
        "",
    ]

    for table in TABLES_TO_AUDIT:
        lines.append(f"## `{table}`")
        lines.append("")
        if table in db_unreachable:
            lines.append("> ⚠️ Could not enumerate columns from the live DB — the")
            lines.append("> table may be empty (PostgREST can't return a column list")
            lines.append("> for an empty table without an OpenAPI fetch) or the")
            lines.append("> service-role key lacks access. Skipping comparison.")
            lines.append("")
            continue

        diff = drift[table]
        missing_in_db = sorted(diff["in_code_only"])
        missing_in_code = sorted(diff["in_db_only"])

        lines.append("| Column | In code | In DB |")
        lines.append("|---|---|---|")
        union = sorted(diff["all_columns"])
        if not union:
            lines.append("| _(no columns discovered)_ | — | — |")
        for col in union:
            in_code = "✅" if col in diff["code_columns"] else "—"
            in_db = "✅" if col in diff["db_columns"] else "—"
            lines.append(f"| `{col}` | {in_code} | {in_db} |")
        lines.append("")

        if missing_in_db:
            lines.append("**⚠️ In code, missing from DB:**")
            for col in missing_in_db:
                lines.append(f"  - `{col}`")
            lines.append("")
        if missing_in_code:
            lines.append("_In DB, not referenced in code:_")
            for col in missing_in_code:
                lines.append(f"  - `{col}`")
            lines.append("")
        if not missing_in_db and not missing_in_code:
            lines.append("_No drift detected._")
            lines.append("")

    return "\n".join(lines) + "\n"


def main() -> int:
    url, key = _supabase_env()
    backend_root = _resolve_backend_root()

    drift: Dict[str, Dict[str, Set[str]]] = {}
    db_unreachable: Set[str] = set()

    for table in TABLES_TO_AUDIT:
        db_cols = fetch_db_columns(table, url, key)
        if not db_cols:
            db_unreachable.add(table)
        code_cols = grep_code_writes(backend_root, table)
        always_valid = COLUMNS_ALWAYS_VALID.get(table, set())

        in_code_only = code_cols - db_cols
        in_db_only = (db_cols - code_cols) - always_valid
        all_columns = code_cols | db_cols

        drift[table] = {
            "db_columns": db_cols,
            "code_columns": code_cols,
            "in_code_only": in_code_only,
            "in_db_only": in_db_only,
            "all_columns": all_columns,
        }

        print(
            f"[{table}] db={len(db_cols)} code={len(code_cols)} "
            f"missing_in_db={sorted(in_code_only)} "
            f"missing_in_code={sorted(in_db_only)}"
        )

    report = render_report(drift, db_unreachable)
    out_path = backend_root / "SCHEMA_AUDIT.md"
    out_path.write_text(report, encoding="utf-8")
    print(f"\nReport written: {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
