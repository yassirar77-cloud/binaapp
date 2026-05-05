"""
Animation tokens per Style DNA.

Each style DNA gets distinct animation personality: easing curves,
durations, stagger delays, reveal distances, and hover lift amounts.
Used by recipe_builder to inject animation CSS variables and by
html_renderer to emit data-reveal attributes instead of AOS.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class AnimationTokens:
    easing: str
    duration_base_ms: int
    stagger_ms: int
    reveal_distance_px: int
    hover_lift_px: int
    page_entrance_enabled: bool = True


ANIMATION_TOKENS = {
    "teh_tarik_warm": AnimationTokens(
        easing="cubic-bezier(0.22, 1, 0.36, 1)",
        duration_base_ms=700,
        stagger_ms=100,
        reveal_distance_px=30,
        hover_lift_px=2,
    ),
    "pandan_fresh": AnimationTokens(
        easing="cubic-bezier(0.22, 1, 0.36, 1)",
        duration_base_ms=600,
        stagger_ms=90,
        reveal_distance_px=25,
        hover_lift_px=3,
    ),
    "kopi_hitam": AnimationTokens(
        easing="cubic-bezier(0.165, 0.84, 0.44, 1)",
        duration_base_ms=800,
        stagger_ms=130,
        reveal_distance_px=35,
        hover_lift_px=2,
    ),
    "sambal_berani": AnimationTokens(
        easing="cubic-bezier(0.34, 1.56, 0.64, 1)",
        duration_base_ms=450,
        stagger_ms=70,
        reveal_distance_px=20,
        hover_lift_px=3,
    ),
    "sutera_putih": AnimationTokens(
        easing="cubic-bezier(0.4, 0, 0.2, 1)",
        duration_base_ms=750,
        stagger_ms=110,
        reveal_distance_px=30,
        hover_lift_px=1,
    ),
    "lampu_neon": AnimationTokens(
        easing="cubic-bezier(0.34, 1.56, 0.64, 1)",
        duration_base_ms=500,
        stagger_ms=80,
        reveal_distance_px=25,
        hover_lift_px=4,
    ),
    "warisan_emas": AnimationTokens(
        easing="cubic-bezier(0.25, 0.46, 0.45, 0.94)",
        duration_base_ms=800,
        stagger_ms=120,
        reveal_distance_px=35,
        hover_lift_px=2,
    ),
    "ombak_biru": AnimationTokens(
        easing="cubic-bezier(0.22, 1, 0.36, 1)",
        duration_base_ms=700,
        stagger_ms=100,
        reveal_distance_px=30,
        hover_lift_px=3,
    ),
    "pasar_malam_neon": AnimationTokens(
        easing="cubic-bezier(0.34, 1.56, 0.64, 1)",
        duration_base_ms=400,
        stagger_ms=60,
        reveal_distance_px=20,
        hover_lift_px=4,
    ),
    "kampung_serene": AnimationTokens(
        easing="cubic-bezier(0.4, 0, 0.2, 1)",
        duration_base_ms=900,
        stagger_ms=150,
        reveal_distance_px=40,
        hover_lift_px=1,
    ),
    "kopitiam_nostalgia": AnimationTokens(
        easing="cubic-bezier(0.25, 0.46, 0.45, 0.94)",
        duration_base_ms=800,
        stagger_ms=120,
        reveal_distance_px=35,
        hover_lift_px=2,
    ),
    "streetfood_bold": AnimationTokens(
        easing="cubic-bezier(0.68, -0.55, 0.265, 1.55)",
        duration_base_ms=350,
        stagger_ms=50,
        reveal_distance_px=15,
        hover_lift_px=3,
    ),
    "fine_dining_obsidian": AnimationTokens(
        easing="cubic-bezier(0.165, 0.84, 0.44, 1)",
        duration_base_ms=1000,
        stagger_ms=200,
        reveal_distance_px=50,
        hover_lift_px=2,
    ),
}


def get_animation_tokens(style_dna_key: str) -> AnimationTokens:
    """Look up animation tokens by style DNA key. Returns teh_tarik_warm as default."""
    return ANIMATION_TOKENS.get(style_dna_key, ANIMATION_TOKENS["teh_tarik_warm"])
