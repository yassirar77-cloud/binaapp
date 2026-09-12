"""Customer-review policy: real reviews or an empty state. Never an invention.

The generator was writing three named customers with quotes onto every site it
built, for businesses whose owners had supplied no reviews at all. On a real
SME's live page that is a fabricated endorsement — a trust problem for the
merchant and, published as-is, a potential legal one.

The rule this module encodes is deliberately absolute: a review appears on a
page only if the merchant supplied it. With none supplied the testimonials
section renders as an EMPTY STATE — heading, one neutral line, and a CTA
inviting the owner to add real reviews — or is omitted entirely.

Both generation paths import from here so the LLM prompt and the deterministic
renderer say the same thing in the same words.
"""

from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional

#: Empty-state copy by page language. Keep both variants in sync — a Malay
#: page with an English "no reviews yet" line reads as broken.
REVIEWS_EMPTY_STATE_COPY: Dict[str, Dict[str, str]] = {
    "ms": {
        "heading": "Ulasan Pelanggan",
        "body": "Belum ada ulasan lagi. Ulasan sebenar daripada pelanggan anda akan dipaparkan di sini.",
        "cta": "Tambah ulasan anda",
    },
    "en": {
        "heading": "Customer Reviews",
        "body": "No reviews yet. Real reviews from your customers will appear here.",
        "cta": "Add your reviews",
    },
}


def empty_state_copy(language: Optional[str]) -> Dict[str, str]:
    """Empty-state strings for `language`, defaulting to Malay."""
    return REVIEWS_EMPTY_STATE_COPY.get(
        (language or "ms").lower(), REVIEWS_EMPTY_STATE_COPY["ms"]
    )


def normalize_supplied_reviews(raw_reviews: Optional[Iterable[Any]]) -> List[Dict[str, Any]]:
    """Merchant-supplied reviews → plain dicts, or [] when none are usable.

    Tolerant by design (pydantic models, dicts, bare strings), and never
    raises: a review that cannot be read is dropped, and dropping every
    review just means the empty state renders — which is the safe outcome.

    A review needs BOTH a reviewer name and review text to count. A quote with
    no attributable author is exactly the shape of the fabricated testimonials
    this module exists to stop, so it is discarded rather than rendered
    anonymously.
    """
    out: List[Dict[str, Any]] = []
    for raw in (raw_reviews or []):
        try:
            if hasattr(raw, "model_dump"):
                d = raw.model_dump()
            elif hasattr(raw, "dict"):
                d = raw.dict()
            elif isinstance(raw, dict):
                d = raw
            else:
                continue

            name = str(d.get("name") or d.get("author") or "").strip()
            text = str(d.get("text") or d.get("review") or d.get("quote") or "").strip()
            if not name or not text:
                continue

            review: Dict[str, Any] = {"name": name, "text": text}

            rating_raw = d.get("rating")
            if rating_raw not in (None, ""):
                try:
                    rating = int(float(rating_raw))
                except (TypeError, ValueError):
                    rating = 0
                if 1 <= rating <= 5:
                    review["rating"] = rating

            role = str(d.get("role") or "").strip()
            if role:
                review["role"] = role

            out.append(review)
        except Exception:
            continue
    return out
