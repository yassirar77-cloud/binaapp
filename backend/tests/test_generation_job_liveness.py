"""Liveness of a running generation job, as the status poll sees it.

Job 44294844 (21 Sep): the page gave up at its fixed 10-minute cap while
the backend was still working — progress had sat at 75% for three minutes
because the polish passes and validation report nothing — and the backend
completed the job one minute later. Nobody saw the site.

The page now watches the job row instead of the clock
(frontend/src/lib/generationPoll.ts). For that to work the row has to
keep moving while the task is alive:

- run_generation_task runs a heartbeat that touches updated_at on a
  `processing` row and stops with the task;
- generate_website reports progress into the long steps (each finished
  image, the polish passes, validation) instead of only at their ends.

Also covers AI_QWEN_REFINE_ENABLED, the switch for the copy-polish pass
that had timed out on every run for a week.
"""
import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest

import app.main as main_module
import app.services.ai_service as ai_service_module
from app.models.schemas import Language, MenuItemInput, WebsiteGenerationRequest
from app.services.ai_service import AIService


# ---- heartbeat ---------------------------------------------------------------

@pytest.mark.asyncio
async def test_heartbeat_touches_only_a_processing_row(monkeypatch):
    supabase = MagicMock()
    monkeypatch.setattr(main_module, "supabase", supabase)
    monkeypatch.setattr(main_module, "JOB_HEARTBEAT_SECONDS", 0.01)

    task = asyncio.create_task(main_module._job_heartbeat("job-1"))
    await asyncio.sleep(0.08)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task

    update = supabase.table.return_value.update
    assert update.call_count >= 3
    payload = update.call_args.args[0]
    assert set(payload) == {"updated_at"}  # never status, progress or html
    chain = update.return_value.eq
    assert chain.call_args_list[0].args == ("job_id", "job-1")
    assert chain.return_value.eq.call_args.args == ("status", "processing")


@pytest.mark.asyncio
async def test_heartbeat_survives_a_failed_write(monkeypatch):
    supabase = MagicMock()
    supabase.table.return_value.update.return_value.eq.return_value.eq.return_value.execute.side_effect = RuntimeError("db down")
    monkeypatch.setattr(main_module, "supabase", supabase)
    monkeypatch.setattr(main_module, "JOB_HEARTBEAT_SECONDS", 0.01)

    task = asyncio.create_task(main_module._job_heartbeat("job-1"))
    await asyncio.sleep(0.05)
    assert not task.done()  # still beating after the failures
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert supabase.table.return_value.update.call_count >= 2


@pytest.mark.asyncio
async def test_run_generation_task_stops_the_heartbeat_when_it_ends(monkeypatch):
    cancelled = asyncio.Event()

    async def fake_heartbeat(job_id):
        try:
            await asyncio.sleep(3600)
        except asyncio.CancelledError:
            cancelled.set()
            raise

    monkeypatch.setattr(main_module, "_job_heartbeat", fake_heartbeat)
    monkeypatch.setattr(main_module, "supabase", MagicMock())
    # The first awaited step of the multi-style path fails: the heartbeat has
    # started beating by then, and the task's failure path must stop it.
    async def _no_variants(*a, **k):
        await asyncio.sleep(0)  # a real suspension, so the heartbeat task gets to start
        return []

    monkeypatch.setattr(main_module.ai_service, "generate_plan_variants", _no_variants)

    await main_module.run_generation_task(
        "job-1", "Kedai makan Pak Mat", business_name="Kedai Pak Mat", multi_style=True,
    )
    await asyncio.sleep(0)
    assert cancelled.is_set()
    failed = main_module.supabase.table.return_value.update.call_args.args[0]
    assert failed["status"] == "failed"


# ---- progress inside the long steps -----------------------------------------

@pytest.fixture
def service(monkeypatch):
    monkeypatch.setenv("ZAI_API_KEY", "test-zai-key")
    monkeypatch.setenv("STABILITY_API_KEY", "test-stability-key")
    return AIService()


@pytest.mark.asyncio
async def test_autofill_reports_each_finished_image(service):
    request = WebsiteGenerationRequest(
        description="Dapur Western Kak Mira — chicken chop dan lamb chop",
        language=Language.MALAY, business_name="Dapur Western Kak Mira",
        business_type="food", subdomain="kakmira",
        menu_items=[MenuItemInput(name="Chicken Chop", price="18"), MenuItemInput(name="Lamb Chop", price="28")],
    )

    async def _fake_generate(prompt, food=True, zai_phase=None, doodle=False):
        return f"https://res.cloudinary.com/{abs(hash(prompt))}.png"

    service._generate_image = AsyncMock(side_effect=_fake_generate)
    reports = []

    async def _progress(done, total):
        reports.append((done, total))

    count = await service._autofill_missing_images(request, {}, None, progress_callback=_progress)

    assert count == 3  # hero + 2 items
    assert reports == [(1, 3), (2, 3), (3, 3)]


@pytest.mark.asyncio
async def test_autofill_progress_callback_errors_do_not_fail_the_step(service):
    request = WebsiteGenerationRequest(
        description="Dapur Western Kak Mira", language=Language.MALAY,
        business_name="Dapur Western Kak Mira", business_type="food", subdomain="kakmira",
        menu_items=[MenuItemInput(name="Chicken Chop", price="18")],
    )
    service._generate_image = AsyncMock(return_value="https://res.cloudinary.com/x.png")
    boom = AsyncMock(side_effect=RuntimeError("callback broke"))
    assert await service._autofill_missing_images(request, {}, None, progress_callback=boom) == 2
    assert boom.await_count == 2


PAGE = """<!DOCTYPE html><html lang="ms"><head><title>Dobi</title></head><body>
<section id="home"><h1>Dobi Layan Diri Seksyen 18</h1><p>Buka 24 jam. Mesin 10kg dan 20kg.</p><a href="https://wa.me/60198765432">WhatsApp</a></section>
<section id="servis"><h2>Servis</h2><ul><li>Basuh 10kg — RM6.00</li><li>Basuh 20kg — RM12.00</li></ul></section>
<section id="lokasi"><h2>Lokasi</h2><p>L7/1, Jalan 18/2, Seksyen 18, Shah Alam</p></section>
<footer><p>Dobi Layan Diri Seksyen 18</p></footer>
</body></html>"""


def _pipeline(monkeypatch):
    monkeypatch.setattr(ai_service_module, "USE_GLM_FOR_HTML", False)
    monkeypatch.setattr(ai_service_module, "AI_QWEN_CSS_REFINE_ENABLED", False)
    monkeypatch.setenv("DESIGN_CRITIQUE_ENABLED", "false")
    svc = AIService()
    svc.deepseek_api_key = "k"
    svc._call_plan_model = AsyncMock(return_value=None)
    svc._call_deepseek = AsyncMock(return_value=PAGE)
    svc._call_qwen = AsyncMock(return_value=None)
    svc._improve_with_qwen = AsyncMock(side_effect=lambda h, d: h)
    svc._generate_ai_food_images = AsyncMock(side_effect=lambda h, **k: (h, 0))
    svc._autofill_missing_images = AsyncMock(return_value=0)
    req = WebsiteGenerationRequest(
        description="Dobi Layan Diri Seksyen 18 — dobi layan diri 24 jam di Seksyen 18, Shah Alam. Mesin basuh 10kg dan 20kg.",
        language=Language.MALAY, business_name="Dobi Layan Diri Seksyen 18", business_type="services", subdomain="bebe",
        whatsapp_number="0198765432", include_maps=False, location_address="L7/1, Jalan 18/2, Seksyen 18, Shah Alam",
        color_mode="light", is_24h=True, opening_hours="Buka 24 jam",
        menu_items=[MenuItemInput(name="Basuh 10kg", price="6"), MenuItemInput(name="Basuh 20kg", price="12")],
    )
    return svc, req


@pytest.mark.asyncio
async def test_progress_is_reported_into_the_polish_and_validation_steps(monkeypatch):
    monkeypatch.setattr(ai_service_module, "AI_QWEN_REFINE_ENABLED", True)
    svc, req = _pipeline(monkeypatch)
    seen = []

    async def _progress(pct, msg):
        seen.append(pct)

    await svc.generate_website(req, image_choice="none", progress_callback=_progress)

    assert 75 in seen and 78 in seen and 85 in seen and 90 in seen
    assert seen.index(75) < seen.index(78) < seen.index(85) < seen.index(90)
    svc._improve_with_qwen.assert_awaited_once()


@pytest.mark.asyncio
async def test_qwen_refine_flag_off_skips_the_pass_and_says_so(monkeypatch):
    monkeypatch.setattr(ai_service_module, "AI_QWEN_REFINE_ENABLED", False)
    svc, req = _pipeline(monkeypatch)
    seen = []

    async def _progress(pct, msg):
        seen.append(pct)

    result = await svc.generate_website(req, image_choice="none", progress_callback=_progress)

    svc._improve_with_qwen.assert_not_awaited()
    assert result.step_outcomes["qwen_refine"] == "skipped (disabled)"
    assert "qwen_refine" not in (result.step_timings or {})
    assert 78 not in seen and 85 in seen


def test_qwen_refine_flag_defaults_on():
    # The flag is new; an environment that has never heard of it keeps the
    # behaviour it had (the pass runs). Only an explicit "false" turns it off.
    assert ai_service_module.AI_QWEN_REFINE_ENABLED is True
