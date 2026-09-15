"""
Post-generation vision check (Round 2, §A2/§A3).

Every AI-generated image is shown to the Qwen vision model with a yes/no
rubric: rendered text? food? a person's face? matches the category? A
failed check regenerates once with a stricter prompt; a second failure
drops the image (the section renders a typographic tile instead). Text
baked into images ("10 kg", the shop name) is caught the same way — labels
are HTML, never pixels.

Pure apart from the injected model call; ``ai_service`` owns the key.
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)

_JSON_SHAPE = '{"has_text": true|false, "has_food": true|false, "has_face": true|false, "matches_category": true|false, "reason": "one short sentence"}'


@dataclass
class VisionVerdict:
    has_text: Optional[bool] = None
    has_food: Optional[bool] = None
    has_face: Optional[bool] = None
    matches_category: Optional[bool] = None
    reason: str = ""
    checked: bool = True  # False when no model answered (the image passes by default)

    def failures(self, *, food_allowed: bool) -> List[str]:
        out: List[str] = []
        if self.has_text:
            out.append("rendered text in the image")
        if self.has_face:
            out.append("a person's face in the image")
        if self.has_food and not food_allowed:
            out.append("food in a non-F&B image")
        if self.matches_category is False:
            out.append("does not match the category")
        return out

    def passes(self, *, food_allowed: bool) -> bool:
        return not self.failures(food_allowed=food_allowed)

    def as_dict(self) -> Dict[str, Any]:
        return {
            "has_text": self.has_text, "has_food": self.has_food, "has_face": self.has_face,
            "matches_category": self.matches_category, "reason": self.reason, "checked": self.checked,
        }


def build_messages(image_url: str, category_label: str) -> List[Dict[str, Any]]:
    system = (
        "You are a strict image QA reviewer for a small-business website builder. Answer each question "
        "about the image with true or false. Be strict: any readable letters, digits, words or a logo "
        "count as text; any human face (even small or partial) counts as a face; any prepared dish, "
        "snack, drink or ingredients count as food. Respond with ONLY a JSON object in this shape:\n" + _JSON_SHAPE
    )
    text = (
        f"Category the image must match: {category_label}.\n"
        "Questions: has_text — does the image contain rendered text, letters, numbers or a logo? "
        "has_food — does it contain food or drink? has_face — does it show a person's face? "
        "matches_category — is the subject clearly the category above?"
    )
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": [
            {"type": "image_url", "image_url": {"url": image_url}},
            {"type": "text", "text": text},
        ]},
    ]


def _to_bool(value: Any) -> Optional[bool]:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        v = value.strip().lower()
        if v in ("true", "yes", "ya", "1"):
            return True
        if v in ("false", "no", "tidak", "0"):
            return False
    return None


def parse_verdict(raw: Optional[str]) -> Optional[VisionVerdict]:
    if not raw or not isinstance(raw, str):
        return None
    text = raw.strip()
    fence = re.search(r"```(?:json)?\s*(.*?)```", text, re.DOTALL)
    if fence:
        text = fence.group(1).strip()
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end <= start:
        return None
    try:
        data = json.loads(text[start:end + 1])
    except (json.JSONDecodeError, ValueError):
        try:
            data = json.loads(re.sub(r",\s*([}\]])", r"\1", text[start:end + 1]))
        except (json.JSONDecodeError, ValueError):
            return None
    if not isinstance(data, dict):
        return None
    verdict = VisionVerdict(
        has_text=_to_bool(data.get("has_text")),
        has_food=_to_bool(data.get("has_food")),
        has_face=_to_bool(data.get("has_face")),
        matches_category=_to_bool(data.get("matches_category")),
        reason=re.sub(r"\s+", " ", str(data.get("reason") or "")).strip()[:200],
    )
    if all(v is None for v in (verdict.has_text, verdict.has_food, verdict.has_face, verdict.matches_category)):
        return None
    return verdict


async def check_image(
    image_url: str,
    category_label: str,
    *,
    call_model: Callable[[List[Dict[str, Any]]], Awaitable[Optional[str]]],
) -> VisionVerdict:
    """Run the rubric. A model failure never blocks an image: the verdict
    comes back ``checked=False`` and passes."""
    try:
        raw = await call_model(build_messages(image_url, category_label))
    except Exception as err:
        logger.warning(f"👁️ Vision check call failed: {err}")
        raw = None
    verdict = parse_verdict(raw)
    if verdict is None:
        return VisionVerdict(checked=False, reason="no verdict from the vision model")
    return verdict
