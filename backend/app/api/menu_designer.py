from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4, A5, letter
import io
import httpx
import uuid
from app.core.config import settings

router = APIRouter()


class MenuItem(BaseModel):
    name: str
    price: str
    description: str = ""
    photo_url: str = ""
    cat: str = ""  # Category id (e.g. "makanan-berat"); empty for uncategorised


class MenuRequest(BaseModel):
    business_name: str
    items: list[MenuItem]
    size: str = "A4"
    style: str = "modern"  # Theme id: classic|warm|modern|forest|ocean|rose
    subtitle: str = ""


def _hex(h: str) -> tuple[float, float, float]:
    h = h.lstrip("#")
    return (int(h[0:2], 16) / 255, int(h[2:4], 16) / 255, int(h[4:6], 16) / 255)


# Mirrors the THEMES array in frontend/src/app/menu-designer/page.tsx.
# muted = ink at 0.55 opacity (lighter body text); rule = ink at 0.2 (dividers).
# Reportlab built-ins: Times-* (serif) and Helvetica (sans).
THEMES: dict[str, dict] = {
    "classic": {"paper": "#FAF7F0", "ink": "#2B2A29", "accent": "#B5894E", "serif": True},
    "warm":    {"paper": "#F5E9D6", "ink": "#5B3A1E", "accent": "#D96B2A", "serif": True},
    "modern":  {"paper": "#FFFFFF", "ink": "#0B0B15", "accent": "#4F3DFF", "serif": False},
    "forest":  {"paper": "#F4F1E8", "ink": "#1F3D2B", "accent": "#2E7D4F", "serif": True},
    "ocean":   {"paper": "#F2F7FB", "ink": "#0A2540", "accent": "#1196EA", "serif": False},
    "rose":    {"paper": "#FBF1F3", "ink": "#4A1F2E", "accent": "#C2185B", "serif": True},
}

# Mirrors the CATEGORIES array in frontend/src/app/menu-designer/page.tsx
CATEGORY_ORDER = ["makanan-berat", "minuman", "roti-snack", "pencuci-mulut"]
CATEGORY_LABELS = {
    "makanan-berat": "Makanan Berat",
    "minuman": "Minuman",
    "roti-snack": "Roti & Snack",
    "pencuci-mulut": "Pencuci Mulut",
}


def _fmt_price(p: str) -> str:
    """Always render as RM with 2 decimals; fall back to raw if not numeric."""
    try:
        return f"RM{float(str(p).replace(',', '.').strip()):.2f}"
    except (ValueError, TypeError):
        return f"RM{p}"


def _font_pair(serif: bool) -> tuple[str, str, str]:
    """Return (regular, bold, italic) PDF font names."""
    if serif:
        return ("Times-Roman", "Times-Bold", "Times-Italic")
    return ("Helvetica", "Helvetica-Bold", "Helvetica-Oblique")


def _mix(rgb: tuple[float, float, float], alpha: float, bg: tuple[float, float, float]) -> tuple[float, float, float]:
    """Pre-multiply ink onto paper so we can fake transparency in vector PDFs."""
    return (
        rgb[0] * alpha + bg[0] * (1 - alpha),
        rgb[1] * alpha + bg[1] * (1 - alpha),
        rgb[2] * alpha + bg[2] * (1 - alpha),
    )


def _draw_theme_frame(c, width, height, theme_id: str, ink, accent, paper):
    """Per-theme decorative edges. Print-safe — stays >18pt inside trim."""
    m = 24  # outer margin in points (~0.33")
    if theme_id == "classic":
        # Double gold rule frame
        c.setStrokeColorRGB(*accent)
        c.setLineWidth(1.4)
        c.rect(m, m, width - 2 * m, height - 2 * m, stroke=1, fill=0)
        c.setLineWidth(0.5)
        c.rect(m + 5, m + 5, width - 2 * m - 10, height - 2 * m - 10, stroke=1, fill=0)
    elif theme_id == "warm":
        # Thick warm rule top + bottom, small accent dots at corners
        c.setStrokeColorRGB(*accent)
        c.setLineWidth(2.5)
        c.line(m, height - m, width - m, height - m)
        c.line(m, m, width - m, m)
        c.setFillColorRGB(*accent)
        for cx, cy in [(m, height - m), (width - m, height - m), (m, m), (width - m, m)]:
            c.circle(cx, cy, 3.5, stroke=0, fill=1)
    elif theme_id == "modern":
        # Geometric L-shaped corner brackets, no frame
        c.setStrokeColorRGB(*accent)
        c.setLineWidth(2)
        arm = 26
        # top-left
        c.line(m, height - m, m + arm, height - m)
        c.line(m, height - m, m, height - m - arm)
        # top-right
        c.line(width - m, height - m, width - m - arm, height - m)
        c.line(width - m, height - m, width - m, height - m - arm)
        # bottom-left
        c.line(m, m, m + arm, m)
        c.line(m, m, m, m + arm)
        # bottom-right
        c.line(width - m, m, width - m - arm, m)
        c.line(width - m, m, width - m, m + arm)
    elif theme_id == "forest":
        # Thin green border + small triangular leaf motif top-center
        c.setStrokeColorRGB(*accent)
        c.setLineWidth(0.8)
        c.rect(m, m, width - 2 * m, height - 2 * m, stroke=1, fill=0)
        # leaf trio
        cx = width / 2
        cy = height - m - 14
        c.setFillColorRGB(*accent)
        for dx in (-12, 0, 12):
            p = c.beginPath()
            p.moveTo(cx + dx, cy + 7)
            p.lineTo(cx + dx - 5, cy - 5)
            p.lineTo(cx + dx + 5, cy - 5)
            p.close()
            c.drawPath(p, stroke=0, fill=1)
    elif theme_id == "ocean":
        # Two horizontal accent rules at top and bottom, no full frame
        c.setStrokeColorRGB(*accent)
        c.setLineWidth(3)
        c.line(m, height - m, width - m, height - m)
        c.setLineWidth(1)
        c.line(m, height - m - 5, width - m, height - m - 5)
        c.setLineWidth(3)
        c.line(m, m, width - m, m)
        c.setLineWidth(1)
        c.line(m, m + 5, width - m, m + 5)
    elif theme_id == "rose":
        # Double rose rule frame + small offset diamond corners
        c.setStrokeColorRGB(*accent)
        c.setLineWidth(0.8)
        c.rect(m, m, width - 2 * m, height - 2 * m, stroke=1, fill=0)
        c.setLineWidth(0.4)
        c.rect(m + 6, m + 6, width - 2 * m - 12, height - 2 * m - 12, stroke=1, fill=0)
        c.setFillColorRGB(*accent)
        for cx, cy in [(m, height - m), (width - m, height - m), (m, m), (width - m, m)]:
            c.saveState()
            c.translate(cx, cy)
            c.rotate(45)
            c.rect(-3, -3, 6, 6, stroke=0, fill=1)
            c.restoreState()


def _group_items(items: list[MenuItem]) -> list[tuple[str, list[MenuItem]]]:
    """Group items by category in CATEGORY_ORDER; trailing untagged items as ('', [...]).
    If NO item has a cat, returns a single ('', items) group (flat render, old behaviour)."""
    has_any = any(it.cat for it in items)
    if not has_any:
        return [("", items)]
    groups: list[tuple[str, list[MenuItem]]] = []
    by_cat: dict[str, list[MenuItem]] = {}
    untagged: list[MenuItem] = []
    for it in items:
        if it.cat in CATEGORY_LABELS:
            by_cat.setdefault(it.cat, []).append(it)
        else:
            untagged.append(it)
    for cat_id in CATEGORY_ORDER:
        if by_cat.get(cat_id):
            groups.append((cat_id, by_cat[cat_id]))
    if untagged:
        groups.append(("", untagged))
    return groups


@router.post("/generate-menu")
async def generate_menu(request: MenuRequest):
    try:
        buffer = io.BytesIO()

        if request.size == "A4":
            page_size = A4
        elif request.size == "A5":
            page_size = A5
        elif request.size == "Letter":
            page_size = letter
        else:  # banner
            page_size = (36 * 72, 24 * 72)

        c = canvas.Canvas(buffer, pagesize=page_size)
        width, height = page_size

        theme_id = request.style if request.style in THEMES else "modern"
        theme = THEMES[theme_id]
        paper = _hex(theme["paper"])
        ink = _hex(theme["ink"])
        accent = _hex(theme["accent"])
        muted = _mix(ink, 0.55, paper)
        rule = _mix(ink, 0.20, paper)
        font_regular, font_bold, font_italic = _font_pair(theme["serif"])

        def paint_page_chrome():
            # Paper background
            c.setFillColorRGB(*paper)
            c.rect(0, 0, width, height, stroke=0, fill=1)
            _draw_theme_frame(c, width, height, theme_id, ink, accent, paper)

        paint_page_chrome()

        # Header: business name
        c.setFillColorRGB(*ink)
        c.setFont(font_bold, 30)
        c.drawCentredString(width / 2, height - 72, request.business_name)

        # Optional subtitle in accent (uppercase tracked)
        if request.subtitle:
            c.setFillColorRGB(*accent)
            c.setFont(font_regular, 10)
            c.drawCentredString(width / 2, height - 90, request.subtitle.upper())

        # Header accent rule
        c.setStrokeColorRGB(*accent)
        c.setLineWidth(1.5)
        rule_y = height - 102
        c.line(width / 2 - 26, rule_y, width / 2 + 26, rule_y)

        # Content area
        y = height - 130
        inner_left = 64
        inner_right = width - 64
        bottom_limit = 80  # don't draw past this — start a new page

        def ensure_space(needed: float):
            nonlocal y
            if y - needed < bottom_limit:
                c.showPage()
                paint_page_chrome()
                y = height - 80

        groups = _group_items(request.items)

        for cat_id, group_items in groups:
            label = CATEGORY_LABELS.get(cat_id, "")
            if label:
                ensure_space(36)
                c.setFillColorRGB(*accent)
                c.setFont(font_bold, 11)
                c.drawString(inner_left, y, label.upper())
                # short accent underline under the category label
                c.setStrokeColorRGB(*accent)
                c.setLineWidth(0.8)
                c.line(inner_left, y - 4, inner_left + 30, y - 4)
                y -= 22

            for item in group_items:
                ensure_space(50 if item.description else 36)

                # Name (ink, bold)
                c.setFillColorRGB(*ink)
                c.setFont(font_bold, 14)
                c.drawString(inner_left, y, item.name)

                # Price (accent, bold, right-aligned)
                c.setFillColorRGB(*accent)
                c.setFont(font_bold, 14)
                c.drawRightString(inner_right, y, _fmt_price(item.price))

                # Description
                if item.description:
                    c.setFillColorRGB(*muted)
                    c.setFont(font_italic, 10)
                    c.drawString(inner_left, y - 14, item.description)
                    y -= 30
                else:
                    y -= 22

                # Separator
                c.setStrokeColorRGB(*rule)
                c.setLineWidth(0.5)
                c.line(inner_left, y, inner_right, y)
                y -= 12

            y -= 8  # gap between groups

        # Footer
        c.setFillColorRGB(*muted)
        c.setFont(font_regular, 9)
        c.drawCentredString(width / 2, 36, "Dibina dengan binaapp.")

        c.save()
        buffer.seek(0)
        pdf_data = buffer.getvalue()
        buffer.close()

        filename = f"menu_{uuid.uuid4()}.pdf"
        url = f"{settings.SUPABASE_URL}/storage/v1/object/menus/{filename}"
        headers = {
            "apikey": settings.SUPABASE_SERVICE_ROLE_KEY,
            "Authorization": f"Bearer {settings.SUPABASE_SERVICE_ROLE_KEY}",
            "Content-Type": "application/pdf",
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(url, headers=headers, content=pdf_data, timeout=30.0)

        if response.status_code in [200, 201]:
            pdf_url = f"{settings.SUPABASE_URL}/storage/v1/object/public/menus/{filename}"
            return {"success": True, "pdf_url": pdf_url}
        else:
            raise HTTPException(status_code=500, detail=f"Upload failed: {response.text}")

    except Exception as e:
        print(f"Menu generation error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
