"""
Learning loop (§9): the design_plans store and the weekly direction-stats
aggregation. HTTP is mocked; the aggregation is pure.
"""

import json
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.cron.design_stats_cron import FLAG_GAP_PCT, MIN_SAMPLE, aggregate, render_markdown, run_design_stats
from app.services import design_plan_store as store


@pytest.fixture(autouse=True)
def _clean_local():
    store.reset_local_history()
    store._disabled_reason = None
    yield
    store.reset_local_history()
    store._disabled_reason = None


def _client(get_json=None, status=200):
    resp = MagicMock()
    resp.status_code = status
    resp.json.return_value = get_json if get_json is not None else []
    resp.text = ""
    client = MagicMock()
    client.get = AsyncMock(return_value=resp)
    client.post = AsyncMock(return_value=resp)
    client.patch = AsyncMock(return_value=resp)
    ctx = MagicMock()
    ctx.__aenter__ = AsyncMock(return_value=client)
    ctx.__aexit__ = AsyncMock(return_value=False)
    return ctx, client


@pytest.mark.asyncio
async def test_local_history_rotates_without_a_database(monkeypatch):
    monkeypatch.setenv("DESIGN_PLAN_STORE_ENABLED", "false")
    assert await store.recent_directions("food") == []
    await store.record_plan(plan={"direction": "warung_cerah", "source": "ai"}, category="food")
    await store.record_plan(plan={"direction": "pasar_pagi", "source": "ai"}, category="food")
    await store.record_plan(plan={"direction": "warung_cerah", "source": "ai"}, category="food")
    assert await store.recent_directions("food") == ["warung_cerah", "pasar_pagi"]
    assert await store.recent_directions("salon") == []


@pytest.mark.asyncio
async def test_db_history_merges_with_local(monkeypatch):
    monkeypatch.setenv("DESIGN_PLAN_STORE_ENABLED", "true")
    monkeypatch.setenv("SUPABASE_URL", "https://x.supabase.co")
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "k")
    ctx, client = _client([{"direction": "kopi_moden"}, {"direction": "kopi_moden"}, {"direction": "laut_api"}])
    store.remember_locally("food", "halal_street")
    with patch("httpx.AsyncClient", return_value=ctx):
        recent = await store.recent_directions("food")
    assert recent == ["kopi_moden", "laut_api", "halal_street"]
    params = client.get.call_args.kwargs["params"]
    assert params["category"] == "eq.food" and params["order"] == "created_at.desc"


@pytest.mark.asyncio
async def test_record_plan_payload_and_missing_table(monkeypatch):
    monkeypatch.setenv("DESIGN_PLAN_STORE_ENABLED", "true")
    monkeypatch.setenv("SUPABASE_URL", "https://x.supabase.co")
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "k")
    ctx, client = _client([{"id": "row-1"}], status=201)
    with patch("httpx.AsyncClient", return_value=ctx):
        row_id = await store.record_plan(
            plan={"direction": "warung_cerah", "source": "fallback"}, category="food", job_id="j1",
            critique={"average": 7.5, "scores": {}}, lint={"ok": True}, html="<html></html>", attempts=2,
        )
    assert row_id == "row-1"
    body = client.post.call_args.kwargs["json"]
    assert body["direction"] == "warung_cerah" and body["plan_source"] == "fallback" and body["critique_avg"] == 7.5
    assert body["html_sha256"] == store.html_hash("<html></html>") and body["attempts"] == 2
    # A 404 (table not migrated) disables the store for the process, quietly.
    ctx404, _ = _client([], status=404)
    with patch("httpx.AsyncClient", return_value=ctx404):
        await store.recent_directions("food")
    assert store._disabled_reason
    with patch("httpx.AsyncClient", return_value=ctx) as ac:
        assert await store.record_plan(plan={"direction": "x"}, category="food") is None
        ac.assert_not_called()


@pytest.mark.asyncio
async def test_mark_outcome_patches_by_website(monkeypatch):
    monkeypatch.setenv("DESIGN_PLAN_STORE_ENABLED", "true")
    monkeypatch.setenv("SUPABASE_URL", "https://x.supabase.co")
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "k")
    ctx, client = _client([])
    with patch("httpx.AsyncClient", return_value=ctx):
        await store.mark_outcome("site-1", "published")
        await store.mark_outcome("site-1", "bogus")
    assert client.patch.await_count == 1
    assert client.patch.call_args.kwargs["params"] == {"website_id": "eq.site-1"}
    assert client.patch.call_args.kwargs["json"]["outcome"] == "published"


# ---- stats -------------------------------------------------------------------

def _rows():
    rows = []
    for _ in range(6):
        rows.append({"direction": "warung_cerah", "category": "food", "outcome": "published", "critique_avg": 8.0, "plan_source": "ai"})
    for i in range(6):
        rows.append({"direction": "kopi_moden", "category": "food", "outcome": "regenerated" if i < 5 else "published", "critique_avg": 6.5, "plan_source": "fallback"})
    rows.append({"direction": "salon_lembut", "category": "salon", "outcome": "edited", "critique_avg": None})
    rows.append({"direction": "salon_lembut", "category": "salon", "outcome": "generated"})
    return rows


def test_aggregate_flags_lowest_publish_rate_with_enough_samples():
    stats = aggregate(_rows())
    d = stats["directions"]
    assert d["warung_cerah"]["publish_rate"] == 100.0 and d["kopi_moden"]["publish_rate"] < 20
    assert d["kopi_moden"]["regen_rate"] > 80 and d["kopi_moden"]["fallback"] == 6
    assert d["salon_lembut"]["publish_rate"] == 50.0 and d["salon_lembut"]["critique_avg"] is None
    assert stats["flagged"] == ["kopi_moden"]  # salon_lembut has < MIN_SAMPLE sites
    assert MIN_SAMPLE == 5 and FLAG_GAP_PCT == 15.0


def test_render_markdown_lists_flagged_and_table():
    md = render_markdown(aggregate(_rows()), generated_at=datetime(2026, 9, 13, tzinfo=timezone.utc))
    assert md.startswith("# Direction stats")
    assert "## Flagged (lowest publish rate)" in md and "`kopi_moden`" in md
    assert "| `warung_cerah` |" in md and "food 6" in md
    empty = render_markdown(aggregate([]))
    assert "No direction is flagged yet" in empty and "_no data yet_" in empty


@pytest.mark.asyncio
async def test_run_design_stats_writes_the_report(tmp_path):
    with patch("app.services.design_plan_store.fetch_all", new=AsyncMock(return_value=_rows())):
        result = await run_design_stats(tmp_path / "direction-stats.md")
    assert result["success"] and result["steps"]["design_stats"]["flagged"] == ["kopi_moden"]
    assert (tmp_path / "direction-stats.md").read_text().startswith("# Direction stats")
