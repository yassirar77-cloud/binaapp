"""
Weekly direction stats (§9) — the learning loop's report.

Reads every design_plans row (migration 057), aggregates per direction:
how many sites it produced, how many were published / edited /
regenerated, the average critique score, and flags the directions with the
lowest publish rate so the library can be tuned on evidence. The report
is written to docs/design/direction-stats.md (checked into the repo by
whoever runs the job, or read straight off the Render disk).

Run: ``python cron_runner.py design-stats`` (Render cron, weekly). The
aggregation itself (``aggregate`` / ``render_markdown``) is pure so it is
unit-tested without a database.
"""

from __future__ import annotations

import asyncio
import logging
import os
import time
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

logger = logging.getLogger(__name__)

#: A direction needs this many finished sites before its publish rate is
#: taken seriously — below it, the flag would be noise.
MIN_SAMPLE = 5
#: Directions whose publish rate sits this far below the library average
#: (in absolute percentage points) are flagged.
FLAG_GAP_PCT = 15.0

DEFAULT_REPORT_PATH = Path(__file__).resolve().parents[3] / "docs" / "design" / "direction-stats.md"


def aggregate(rows: Iterable[Dict[str, Any]]) -> Dict[str, Any]:
    """rows → {directions: {key: {...}}, overall: {...}, flagged: [keys]}."""
    per: Dict[str, Dict[str, Any]] = defaultdict(lambda: {
        "sites": 0, "published": 0, "edited": 0, "regenerated": 0, "discarded": 0,
        "fallback": 0, "critique_sum": 0.0, "critique_n": 0, "categories": defaultdict(int),
    })
    for row in rows:
        key = str(row.get("direction") or "unknown")
        d = per[key]
        d["sites"] += 1
        outcome = str(row.get("outcome") or "generated")
        if outcome in ("published", "edited", "regenerated", "discarded"):
            d[outcome] += 1
        if str(row.get("plan_source") or "") == "fallback":
            d["fallback"] += 1
        avg = row.get("critique_avg")
        try:
            if avg is not None:
                d["critique_sum"] += float(avg)
                d["critique_n"] += 1
        except (TypeError, ValueError):
            pass
        d["categories"][str(row.get("category") or "general")] += 1

    directions: Dict[str, Dict[str, Any]] = {}
    total_sites = total_published = 0
    for key, d in per.items():
        sites = d["sites"]
        # "edited" is still a kept site — the merchant used the page.
        kept = d["published"] + d["edited"]
        directions[key] = {
            "sites": sites,
            "published": d["published"],
            "edited": d["edited"],
            "regenerated": d["regenerated"],
            "discarded": d["discarded"],
            "fallback": d["fallback"],
            "publish_rate": round(100.0 * kept / sites, 1) if sites else 0.0,
            "regen_rate": round(100.0 * d["regenerated"] / sites, 1) if sites else 0.0,
            "critique_avg": round(d["critique_sum"] / d["critique_n"], 2) if d["critique_n"] else None,
            "categories": dict(sorted(d["categories"].items(), key=lambda kv: -kv[1])),
        }
        total_sites += sites
        total_published += kept
    overall_rate = round(100.0 * total_published / total_sites, 1) if total_sites else 0.0
    flagged = sorted(
        [k for k, v in directions.items() if v["sites"] >= MIN_SAMPLE and v["publish_rate"] <= overall_rate - FLAG_GAP_PCT],
        key=lambda k: directions[k]["publish_rate"],
    )
    return {
        "directions": dict(sorted(directions.items(), key=lambda kv: (-kv[1]["sites"], kv[0]))),
        "overall": {"sites": total_sites, "kept": total_published, "publish_rate": overall_rate},
        "flagged": flagged,
    }


def render_markdown(stats: Dict[str, Any], generated_at: Optional[datetime] = None) -> str:
    generated_at = generated_at or datetime.now(timezone.utc)
    lines = [
        "# Direction stats",
        "",
        f"_Generated {generated_at.strftime('%Y-%m-%d %H:%M UTC')} by `python cron_runner.py design-stats` from the `design_plans` table (migration 057)._",
        "",
        "Every generated site records its design plan, critique score and what the merchant did next. "
        "A direction is **flagged** when it has at least "
        f"{MIN_SAMPLE} sites and its publish rate (published + edited) sits {FLAG_GAP_PCT:.0f} points or more below the library average — "
        "those are the directions to redesign or retire first.",
        "",
        f"**Overall:** {stats['overall']['sites']} sites, {stats['overall']['kept']} kept, publish rate {stats['overall']['publish_rate']}%.",
        "",
    ]
    if stats["flagged"]:
        lines.append("## Flagged (lowest publish rate)")
        lines.append("")
        for key in stats["flagged"]:
            d = stats["directions"][key]
            lines.append(f"- `{key}` — {d['publish_rate']}% kept over {d['sites']} sites (regenerated {d['regen_rate']}%, critique avg {d['critique_avg']})")
        lines.append("")
    else:
        lines.append("## Flagged")
        lines.append("")
        lines.append("_No direction is flagged yet (not enough sites, or every direction is within range)._")
        lines.append("")
    lines.append("## All directions")
    lines.append("")
    lines.append("| Direction | Sites | Published | Edited | Regenerated | Publish rate | Regen rate | Critique avg | Fallback plans | Categories |")
    lines.append("|---|---:|---:|---:|---:|---:|---:|---:|---:|---|")
    for key, d in stats["directions"].items():
        cats = ", ".join(f"{c} {n}" for c, n in d["categories"].items())
        flag = " ⚠️" if key in stats["flagged"] else ""
        lines.append(
            f"| `{key}`{flag} | {d['sites']} | {d['published']} | {d['edited']} | {d['regenerated']} | {d['publish_rate']}% | {d['regen_rate']}% | "
            f"{d['critique_avg'] if d['critique_avg'] is not None else '—'} | {d['fallback']} | {cats} |"
        )
    if not stats["directions"]:
        lines.append("| _no data yet_ | | | | | | | | | |")
    lines.append("")
    return "\n".join(lines)


async def run_design_stats(report_path: Optional[Path] = None) -> Dict[str, Any]:
    started = time.time()
    path = Path(report_path or os.getenv("DESIGN_STATS_REPORT_PATH") or DEFAULT_REPORT_PATH)
    try:
        from app.services import design_plan_store

        rows = await design_plan_store.fetch_all()
        stats = aggregate(rows)
        markdown = render_markdown(stats)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(markdown, encoding="utf-8")
        logger.info(f"📊 Direction stats written to {path} ({len(rows)} rows, {len(stats['flagged'])} flagged)")
        return {
            "success": True,
            "duration_seconds": round(time.time() - started, 2),
            "steps": {"design_stats": {"rows": len(rows), "directions": len(stats["directions"]), "flagged": stats["flagged"], "report": str(path)}},
        }
    except Exception as err:
        logger.exception("Direction stats failed")
        return {"success": False, "error": str(err), "duration_seconds": round(time.time() - started, 2), "steps": {}}


def run_design_stats_sync(report_path: Optional[Path] = None) -> Dict[str, Any]:
    return asyncio.run(run_design_stats(report_path))


if __name__ == "__main__":
    print(run_design_stats_sync())
