"""
Widget Catalogue — single source of truth for every widget that the
post-generation injection layer can stitch onto an AI-generated site.

Both the AI prompt builder (`ai_service._build_strict_prompt`) and the
injection layer (`templates.TemplateService.*`) consume this. The prompt
builder uses the entries to tell the model which widgets will be injected
and where, so the model can leave room for them (designated slot div +
no clashing fixed elements + complementary palette). The injection layer
honours the same slot ids when the model emitted them, and falls back to
the legacy floating/fixed positioning when it didn't.

Backward compatibility:
- Every widget has a `legacy_position` describing the original floating/
  fixed style. If the AI did not emit the slot, the injection layer keeps
  using the legacy placement, so existing generated sites still work.
- Adding a new widget only requires appending to `WIDGETS`. Both the
  prompt and the injectors will pick it up the next generation.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional


# Slot id prefix — kept identical to what the prompt instructs the AI to
# emit. Changing this is a breaking change.
SLOT_PREFIX = "binaapp-"


@dataclass(frozen=True)
class WidgetSpec:
    """Metadata describing one injectable widget."""

    id: str
    """Stable identifier (used in the slot div id and logging)."""

    name: str
    """Human-readable name for prompt / docs / debugging."""

    default_position: str
    """Slug describing where the widget naturally lives: floating-br,
    floating-bl, top-right, section-after-hero, footer, hero-cta."""

    default_colors: Dict[str, str]
    """Hex codes the widget paints itself in by default. Theme extraction
    can override `primary` with the site's primary accent."""

    recommended_placement: str
    """Short instruction the AI sees in the context block — describes the
    *semantic* location the AI should leave free."""

    prompt_description: str
    """One-line summary of what the widget does, included in the prompt's
    widget catalogue block."""

    legacy_position: str
    """How the injection layer positions the widget if the AI did not
    emit a designated slot div (CSS hint, used in fallback)."""

    slot_id: str = ""
    """Computed: the `id` attribute the AI is told to emit. Filled in by
    `__post_init__` so callers don't have to remember the prefix."""

    aliases: List[str] = field(default_factory=list)
    """Alternative ids the injection layer should also look for, so the
    AI can still match when it emits a near-miss."""

    def __post_init__(self):
        # `frozen=True` blocks plain assignment; this is the documented
        # workaround for derived fields on frozen dataclasses.
        object.__setattr__(self, "slot_id", f"{SLOT_PREFIX}{self.id}-slot")


WIDGETS: Dict[str, WidgetSpec] = {
    "whatsapp": WidgetSpec(
        id="whatsapp",
        name="WhatsApp Floating Button",
        default_position="floating-br",
        default_colors={"primary": "#25D366", "text": "#ffffff"},
        recommended_placement=(
            "Floating action button in the bottom-right corner. Leave a "
            "~80px clear zone there (no overlapping CTAs, no fixed footers "
            "occupying that area)."
        ),
        prompt_description=(
            "Green WhatsApp floating button (60px circle) that opens a "
            "pre-filled wa.me chat. Always present when WhatsApp is enabled."
        ),
        legacy_position="position:fixed;bottom:20px;right:20px",
    ),
    "chat": WidgetSpec(
        id="chat",
        name="Customer Chat Widget",
        default_position="floating-bl",
        default_colors={"primary": "#3b82f6", "text": "#ffffff"},
        recommended_placement=(
            "Floating bubble in the bottom-left corner. Hero CTAs and "
            "fixed nav must not overlap this zone."
        ),
        prompt_description=(
            "In-page chat widget for customer↔owner messaging. Loads via "
            "external script; renders a floating bubble + side panel."
        ),
        legacy_position="position:fixed;bottom:20px;left:20px",
        aliases=["binaapp-chat"],
    ),
    "delivery": WidgetSpec(
        id="delivery",
        name="Delivery / Ordering Widget",
        default_position="floating-br-above-whatsapp",
        default_colors={"primary": "#ea580c", "text": "#ffffff"},
        recommended_placement=(
            "Stacked above the WhatsApp button on the bottom-right. The "
            "hero CTA should complement an ordering flow (e.g. 'Lihat "
            "Menu' or 'Pesan Sekarang') and link to #menu so the widget's "
            "cart can pick items from a real menu section."
        ),
        prompt_description=(
            "BinaApp delivery widget — opens a full ordering sheet with "
            "cart, zones, and checkout. Only injected when ecommerce is on."
        ),
        legacy_position="position:fixed;bottom:90px;right:20px",
        aliases=["binaapp-pesanan", "binaapp-pesanan-slot", "binaapp-delivery-slot"],
    ),
    "pesanan": WidgetSpec(
        id="pesanan",
        name="Inline Pesanan / Menu Slot",
        default_position="section-after-menu",
        default_colors={"primary": "#ea580c", "text": "#ffffff"},
        recommended_placement=(
            "A full-width section immediately after the menu/products "
            "section. The injection layer will replace this slot's "
            "contents with the live ordering UI."
        ),
        prompt_description=(
            "Inline ordering section anchor — gives the AI a place to "
            "reserve real-estate between menu and contact for the "
            "ordering flow."
        ),
        legacy_position="appended-before-body-close",
    ),
    "maps": WidgetSpec(
        id="maps",
        name="Google Maps Embed",
        default_position="section-before-footer",
        default_colors={"primary": "#1f2937", "text": "#ffffff"},
        recommended_placement=(
            "A 'Lokasi Kami' section embedded before the footer. Leave a "
            "16:9 area for an iframe; do not duplicate the address line "
            "since the widget already shows it."
        ),
        prompt_description=(
            "Google Maps iframe embed showing the business address. Lives "
            "inline in a section, not as a floating button."
        ),
        legacy_position="appended-before-body-close",
    ),
    "contact": WidgetSpec(
        id="contact",
        name="Contact Form",
        default_position="section-before-footer",
        default_colors={"primary": "#3b82f6", "text": "#ffffff"},
        recommended_placement=(
            "A simple 'Hubungi Kami' / 'Contact Us' form section. Place "
            "right before the footer. Do not also write your own contact "
            "form — the widget provides one."
        ),
        prompt_description=(
            "Inline contact form (name, email, message) that emails the "
            "owner. Rendered as a section."
        ),
        legacy_position="appended-before-body-close",
    ),
    "qr": WidgetSpec(
        id="qr",
        name="QR Code Block",
        default_position="footer",
        default_colors={"primary": "#000000", "text": "#ffffff"},
        recommended_placement=(
            "Inside or right above the footer. A small block (≤200px "
            "wide) labelled with the site URL."
        ),
        prompt_description=(
            "QR code image generated from the published URL — used to "
            "share the site offline."
        ),
        legacy_position="appended-before-body-close",
    ),
}


def get_widget(widget_id: str) -> Optional[WidgetSpec]:
    """Look up a widget by id, returning None if unknown."""
    return WIDGETS.get(widget_id)


def widgets_for_request(
    *,
    include_whatsapp: bool,
    include_maps: bool,
    include_ecommerce: bool,
    include_contact: bool = True,
    include_chat: bool = True,
) -> List[WidgetSpec]:
    """Compute the ordered list of widgets that will be injected for the
    given generation request. Order matters: the prompt block lists
    widgets in this order so the AI gets the most prominent ones first.
    """
    selected: List[WidgetSpec] = []
    # Delivery (ordering) is the most layout-disruptive; surface it first.
    if include_ecommerce:
        selected.append(WIDGETS["delivery"])
        selected.append(WIDGETS["pesanan"])
    if include_whatsapp:
        selected.append(WIDGETS["whatsapp"])
    if include_chat:
        selected.append(WIDGETS["chat"])
    if include_maps:
        selected.append(WIDGETS["maps"])
    if include_contact:
        selected.append(WIDGETS["contact"])
    return selected


def build_prompt_context_block(
    widgets: List[WidgetSpec],
    *,
    primary_color: Optional[str] = None,
) -> str:
    """Render the widget-awareness context block that gets prepended to
    the AI prompt.

    The block tells the AI:
    1. Which widgets are about to be stitched in (so don't duplicate them).
    2. Where they will live (so leave the area free).
    3. Optional designated slot div ids the AI can emit to control
       placement explicitly.
    """
    if not widgets:
        return ""

    primary_hint = (
        f"\nSITE PRIMARY COLOUR (use this in tailwind config + hero gradients): "
        f"{primary_color}"
        if primary_color
        else ""
    )

    rows: List[str] = []
    for w in widgets:
        rows.append(
            f"- {w.name} (id={w.slot_id})\n"
            f"    purpose: {w.prompt_description}\n"
            f"    placement: {w.recommended_placement}\n"
            f"    default colour: {w.default_colors.get('primary')}"
        )
    rows_block = "\n".join(rows)

    return f"""
===== INJECTED WIDGETS — DESIGN AROUND THESE =====
After you finish, the platform will inject the following widgets onto the
page. Your design MUST accommodate them — do NOT recreate them, do NOT
clash with their colours, do NOT cover their positions with your own
fixed elements.{primary_hint}

WIDGETS BEING INJECTED:
{rows_block}

RULES:
1. Do NOT add your own floating WhatsApp / chat / delivery buttons —
   they will be injected. (You may add a regular inline "Order Now" CTA
   that scrolls to #menu; that's fine.)
2. For inline widgets (maps, contact form, qr, pesanan), you MAY emit an
   empty placeholder div with the listed id, e.g.
       <div id="binaapp-pesanan-slot"></div>
   placed at the correct semantic location. The injection layer will
   replace the inner contents with the live widget. If you don't emit a
   slot div, the widget is appended at the end of the body (legacy
   behaviour, still works, but layout is less controlled).
3. Keep the bottom-right ~80px clear of your own fixed elements (no fixed
   "back to top" arrows, no announcement bars there).
4. Pick a palette that does not clash with the floating widgets'
   defaults (WhatsApp green #25D366, chat blue #3b82f6). If your primary
   is also a saturated green, shift toward teal or warm tones for the
   hero so the WhatsApp button stays legible.
==================================================
"""
