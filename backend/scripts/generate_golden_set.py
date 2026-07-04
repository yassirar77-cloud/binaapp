"""Generate the golden comparison set: OLD vs NEW pipeline over golden prompts.

For each golden prompt this runs the selected pipeline(s) and writes:
    docs/previews/golden/{pipeline}/{prompt_id}.html
    docs/previews/golden/{pipeline}/{prompt_id}.meta.json

meta.json records WHICH MODEL produced the output (read from env at run
time — the live model is pinned in Render env vars, so always trust env,
never hardcode), timings, truncation diagnostics, and the M0 lint report.

Usage (from backend/, with DEEPSEEK_API_KEY etc. exported):
    python scripts/generate_golden_set.py                       # both pipelines, all prompts
    python scripts/generate_golden_set.py --pipeline old        # legacy only
    python scripts/generate_golden_set.py --pipeline new        # recipe pipeline only
    python scripts/generate_golden_set.py --prompts mamak_neon_bm,cafe_minimal_manglish
    python scripts/generate_golden_set.py --images ai           # spend Stability credits (default: none)

Then screenshot + build the review gallery:
    python scripts/screenshot_golden.py
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

_script_dir = os.path.dirname(os.path.abspath(__file__))
_backend_dir = os.path.dirname(_script_dir)
sys.path.insert(0, _backend_dir)

from scripts.golden_prompts import GOLDEN_PROMPTS, PROMPTS_BY_ID, GoldenPrompt  # noqa: E402

DEFAULT_OUT = Path(_backend_dir).parent / "docs" / "previews" / "golden"


def resolve_models() -> dict:
    """The exact model IDs the pipelines will use — read from env like
    ai_service does, so the meta.json always names the pinned live model."""
    return {
        "deepseek_model": os.getenv("DEEPSEEK_MODEL", "deepseek-chat"),
        "deepseek_model_pro": os.getenv("DEEPSEEK_MODEL_PRO", "deepseek-reasoner"),
        "qwen_html_model": os.getenv("QWEN_HTML_MODEL", "qwen-plus-latest"),
        "deepseek_base_url": os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1"),
    }


def build_request(prompt: GoldenPrompt):
    from app.models.schemas import WebsiteGenerationRequest, Language

    return WebsiteGenerationRequest(
        description=prompt.description,
        business_name=prompt.business_name,
        business_type="restaurant",
        language=Language.MALAY if prompt.language == "ms" else Language.ENGLISH,
        subdomain="golden-preview",
        include_whatsapp=prompt.features.get("whatsapp", True),
        whatsapp_number=prompt.whatsapp_number,
        include_maps=False,
        color_mode=prompt.color_mode,
    )


async def run_old(prompt: GoldenPrompt, image_choice: str) -> dict:
    from app.services.ai_service import AIService

    service = AIService()
    request = build_request(prompt)
    t0 = time.time()
    response = await service.generate_website(request, image_choice=image_choice)
    return {
        "html": response.html_content,
        "duration_s": round(time.time() - t0, 1),
        "was_truncated": response.was_truncated,
        "truncation_retries": response.truncation_retries,
        "needs_manual_review": response.needs_manual_review,
        "step_timings": response.step_timings,
    }


async def run_new(prompt: GoldenPrompt, image_choice: str) -> dict:
    try:
        from app.services import recipe_pipeline
    except ImportError as exc:  # M0 shipped before M1 — degrade politely
        raise SystemExit(
            f"recipe pipeline not available ({exc}). Build M1 first or use --pipeline old."
        )

    request = build_request(prompt)
    t0 = time.time()
    response = await recipe_pipeline.generate(request, image_choice=image_choice)
    return {
        "html": response.html_content,
        "duration_s": round(time.time() - t0, 1),
        "was_truncated": response.was_truncated,
        "truncation_retries": response.truncation_retries,
        "needs_manual_review": response.needs_manual_review,
        "step_timings": response.step_timings,
    }


async def generate_one(prompt: GoldenPrompt, pipeline: str, image_choice: str, out_dir: Path) -> bool:
    from app.utils.output_lint import lint_html

    models = resolve_models()
    print(f"\n=== {prompt.id} [{pipeline}] ===")
    print(f"    models: deepseek={models['deepseek_model']} "
          f"pro={models['deepseek_model_pro']} qwen={models['qwen_html_model']}")

    runner = run_old if pipeline == "old" else run_new
    try:
        result = await runner(prompt, image_choice)
    except Exception as exc:
        print(f"    FAILED: {exc}")
        (out_dir / pipeline).mkdir(parents=True, exist_ok=True)
        (out_dir / pipeline / f"{prompt.id}.meta.json").write_text(json.dumps({
            "prompt_id": prompt.id,
            "pipeline": pipeline,
            "models": models,
            "error": str(exc),
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }, indent=2))
        return False

    lint = lint_html(result["html"], language=prompt.language)
    meta = {
        "prompt_id": prompt.id,
        "scenario": prompt.scenario,
        "language": prompt.language,
        "pipeline": pipeline,
        "models": models,
        "image_choice": image_choice,
        "duration_s": result["duration_s"],
        "was_truncated": result["was_truncated"],
        "truncation_retries": result["truncation_retries"],
        "needs_manual_review": result["needs_manual_review"],
        "step_timings": result["step_timings"],
        "lint": lint.as_dict(),
        "html_bytes": len(result["html"].encode("utf-8")),
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }

    target = out_dir / pipeline
    target.mkdir(parents=True, exist_ok=True)
    (target / f"{prompt.id}.html").write_text(result["html"], encoding="utf-8")
    (target / f"{prompt.id}.meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")

    status = "OK" if lint.ok else f"LINT ISSUES: {lint.issues}"
    print(f"    {result['duration_s']}s, {meta['html_bytes'] // 1024} KB — {status}")
    return lint.ok


async def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pipeline", choices=["old", "new", "both"], default="both")
    parser.add_argument("--prompts", default="all",
                        help="comma-separated prompt ids, or 'all'")
    parser.add_argument("--images", choices=["none", "ai"], default="none",
                        help="'ai' spends Stability credits; default 'none'")
    parser.add_argument("--out", default=str(DEFAULT_OUT))
    args = parser.parse_args()

    if not os.getenv("DEEPSEEK_API_KEY"):
        print("WARNING: DEEPSEEK_API_KEY not set — both pipelines need it.")

    if args.prompts == "all":
        prompts = GOLDEN_PROMPTS
    else:
        missing = [p for p in args.prompts.split(",") if p not in PROMPTS_BY_ID]
        if missing:
            print(f"Unknown prompt ids: {missing}. Known: {sorted(PROMPTS_BY_ID)}")
            return 2
        prompts = [PROMPTS_BY_ID[p] for p in args.prompts.split(",")]

    pipelines = ["old", "new"] if args.pipeline == "both" else [args.pipeline]
    out_dir = Path(args.out)

    print(f"Golden set: {len(prompts)} prompts × {pipelines} → {out_dir}")
    all_ok = True
    for prompt in prompts:
        for pipeline in pipelines:
            ok = await generate_one(prompt, pipeline, args.images, out_dir)
            all_ok = all_ok and ok

    print("\nDone. Next: python scripts/screenshot_golden.py")
    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
