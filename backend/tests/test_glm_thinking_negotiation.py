"""
Tests for the GLM `thinking` contract negotiation in _call_glm.

Regression context — production had USE_GLM_FOR_HTML=on and glm-5.3 configured,
yet DeepSeek generated every page. The reason was a hard 400, half a second
into every GLM call:

    11:10:32.213  🟣 Calling GLM (Z.ai) API (glm-5.3)... (prompt length: 37967)
    11:10:32.729  🟣 GLM ❌ Status 400: {"error":{"code":"1210","message":
                  "This model always engages in thinking and cannot be
                   disabled; please use low, high, or max"}}

_call_glm hardcoded `"thinking": {"type": "disabled"}` and, unlike
_call_deepseek, had no retry on 400. So GLM never produced a single page — it
failed instantly and every generation silently fell through to the DeepSeek
path, where it burned ~374s and truncated.

Covers the ladder (low → disabled → omitted), that unrelated 400s are NOT
retried, and that the PHOTO_SLOT binding now runs on the plan-gate path.

All HTTP calls are mocked — no live API usage.
"""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock

import app.services.ai_service as ai_service_module
from app.services.ai_service import AIService


HTML = "<!DOCTYPE html><html><body><h1>Warung</h1></body></html>"

# The exact rejection glm-5.3 returns for thinking=disabled.
THINKING_400 = (
    '{"error":{"code":"1210","message":"This model always engages in thinking '
    'and cannot be disabled; please use low, high, or max"}}'
)


def _resp(status_code=200, content=HTML, text="", finish_reason="stop"):
    r = MagicMock()
    r.status_code = status_code
    r.text = text
    r.json.return_value = {
        "choices": [{"message": {"content": content}, "finish_reason": finish_reason}],
        "usage": {"completion_tokens": 900},
    }
    return r


def _patch_client(*responses):
    mock_post = AsyncMock(side_effect=list(responses))
    mock_client = MagicMock()
    mock_client.post = mock_post
    ctx = MagicMock()
    ctx.__aenter__ = AsyncMock(return_value=mock_client)
    ctx.__aexit__ = AsyncMock(return_value=False)
    return patch.object(ai_service_module.httpx, "AsyncClient", return_value=ctx), mock_post


@pytest.fixture
def svc():
    s = AIService()
    s.zai_api_key = "test-key"
    return s


def _thinking_of(call):
    return call.kwargs["json"].get("thinking", "ABSENT")


@pytest.mark.asyncio
async def test_first_attempt_uses_a_reasoning_level_not_disabled(svc):
    """glm-5.3 requires reasoning on — `disabled` must not be the opening bid."""
    patcher, post = _patch_client(_resp())
    with patcher:
        out = await svc._call_glm("prompt")
    assert out == HTML
    assert post.await_count == 1
    assert _thinking_of(post.await_args_list[0]) == {"type": "low"}


@pytest.mark.asyncio
async def test_thinking_400_retries_down_the_ladder(svc):
    """The production failure: first rung rejected, call must not die there."""
    patcher, post = _patch_client(
        _resp(status_code=400, text=THINKING_400),
        _resp(),
    )
    with patcher:
        out = await svc._call_glm("prompt")
    assert out == HTML, "a thinking-400 must fall to the next rung, not fail the call"
    assert post.await_count == 2
    assert _thinking_of(post.await_args_list[1]) == {"type": "disabled"}


@pytest.mark.asyncio
async def test_ladder_finally_drops_the_field_entirely(svc):
    """An unknown future contract degrades to the provider default."""
    patcher, post = _patch_client(
        _resp(status_code=400, text=THINKING_400),
        _resp(status_code=400, text=THINKING_400),
        _resp(),
    )
    with patcher:
        out = await svc._call_glm("prompt")
    assert out == HTML
    assert post.await_count == 3
    assert _thinking_of(post.await_args_list[2]) == "ABSENT"


@pytest.mark.asyncio
async def test_unrelated_400_is_not_retried(svc):
    """Only thinking-400s walk the ladder — a bad request should surface at once."""
    patcher, post = _patch_client(
        _resp(status_code=400, text='{"error":{"message":"model not found"}}'),
    )
    with patcher:
        out = await svc._call_glm("prompt")
    assert out is None
    assert post.await_count == 1, "unrelated 400 must not burn the whole ladder"


@pytest.mark.asyncio
async def test_thinking_type_is_env_overridable(svc):
    """Operators can raise the reasoning level without a deploy."""
    ladder = ({"type": "high"}, {"type": "disabled"}, None)
    patcher, post = _patch_client(_resp())
    with patch.object(AIService, "_GLM_THINKING_LADDER", ladder), patcher:
        await svc._call_glm("prompt")
    assert _thinking_of(post.await_args_list[0]) == {"type": "high"}


@pytest.mark.asyncio
async def test_every_rung_rejected_returns_none_for_deepseek_fallback(svc):
    patcher, post = _patch_client(
        _resp(status_code=400, text=THINKING_400),
        _resp(status_code=400, text=THINKING_400),
        _resp(status_code=400, text=THINKING_400),
    )
    with patcher:
        out = await svc._call_glm("prompt")
    assert out is None
    assert post.await_count == 3


# ── PHOTO_SLOT binding on the plan-gate path ─────────────────────────────────

def test_photo_slot_binding_runs_for_the_plan_gate_path_too():
    """The binding must be reachable when the plan gate ran, not only after
    the premium loop.

    GLM emits src="PHOTO_SLOT_N" tokens that _replace_photo_slots() binds to
    the merchant's real image URLs. That call used to sit inside the
    `elif html_raw:` premium-loop branch, so a GLM run that went through the
    plan gate (plan is not None — the normal case) never bound its slots: every
    <img> shipped with a literal src="PHOTO_SLOT_1" and the merchant's own
    photos never reached the page. _html_model had the same hole, so plan-gated
    GLM runs were also misattributed in the validation telemetry.

    Checked on the AST: the binding must NOT live inside the if/elif that
    chooses between the two review paths — it has to be a sibling statement
    that both paths fall through to.
    """
    import ast

    # Parse the module file: generate_website embeds prompt literals at column
    # zero, so inspect.getsource + dedent can't be re-parsed on its own.
    with open(ai_service_module.__file__) as fh:
        tree = ast.parse(fh.read())

    def calls(node, name):
        return any(
            isinstance(n, ast.Attribute) and n.attr == name
            for n in ast.walk(node)
        )

    # The if/elif that routes between the two GLM review paths: plan gate in
    # the body, premium loop in the elif.
    routers = [
        n for n in ast.walk(tree)
        if isinstance(n, ast.If)
        and any(calls(b, "_run_plan_gate") for b in n.body)
        and any(calls(b, "_run_premium_design_loop") for b in n.orelse)
    ]
    assert len(routers) == 1, f"expected exactly one GLM review router, found {len(routers)}"
    router = routers[0]

    assert not calls(router, "_replace_photo_slots"), (
        "PHOTO_SLOT binding is trapped inside the review-path branch, so a "
        "plan-gated GLM run ships unbound slots"
    )
    assert calls(tree, "_replace_photo_slots"), (
        "PHOTO_SLOT binding vanished from the GLM path entirely"
    )
