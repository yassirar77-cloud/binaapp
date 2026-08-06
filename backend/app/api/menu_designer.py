from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4, A5, letter
from reportlab.lib.colors import Color, HexColor
from reportlab.lib.utils import simpleSplit
import io
import httpx
import uuid
from app.core.config import settings

router = APIRouter()

class MenuItem(BaseModel):
    name: str
    price: str
    description: str = ""
    category: str = ""
    photo_url: str = ""

class MenuTheme(BaseModel):
    id: str = "modern"
    paper: str = "#FFFFFF"
    ink: str = "#0B0B15"
    accent: str = "#4F3DFF"

class MenuRequest(BaseModel):
    business_name: str
    subtitle: str = ""
    items: list[MenuItem]
    size: str = "A4"
    style: str = "modern"
    theme: MenuTheme = MenuTheme()


def _hex(value: str, fallback: str) -> Color:
    try:
        return HexColor(value)
    except Exception:
        return HexColor(fallback)


def _blend(fg: Color, bg: Color, alpha: float) -> Color:
    """Approximate CSS opacity by blending fg into the paper colour."""
    return Color(
        fg.red * alpha + bg.red * (1 - alpha),
        fg.green * alpha + bg.green * (1 - alpha),
        fg.blue * alpha + bg.blue * (1 - alpha),
    )


def _grouped_items(items: list[MenuItem]) -> list[tuple[str, list[MenuItem]]]:
    """Group items by category, preserving first-seen category order."""
    groups: dict[str, list[MenuItem]] = {}
    for item in items:
        groups.setdefault(item.category.strip(), []).append(item)
    return list(groups.items())


def render_menu_pdf(request: MenuRequest) -> bytes:
    """Render the menu PDF, mirroring the frontend live preview layout."""
    buffer = io.BytesIO()

    if request.size == "A4":
        page_size = A4
    elif request.size == "A5":
        page_size = A5
    elif request.size == "Letter":
        page_size = letter
    else:  # banner
        page_size = (36*72, 24*72)

    c = canvas.Canvas(buffer, pagesize=page_size)
    width, height = page_size

    paper = _hex(request.theme.paper, "#FFFFFF")
    ink = _hex(request.theme.ink, "#0B0B15")
    accent = _hex(request.theme.accent, "#4F3DFF")
    ink_soft = _blend(ink, paper, 0.65)
    leader = _blend(ink, paper, 0.25)

    # Scale typography with the page so the layout matches the preview on
    # every size (A5 shrinks, banner grows).
    scale = width / A4[0]
    margin = width * 0.08
    content_width = width - 2 * margin

    def paint_page() -> float:
        c.setFillColor(paper)
        c.rect(0, 0, width, height, stroke=0, fill=1)
        return height - height * 0.07

    def draw_footer():
        c.setFont("Helvetica", 9 * scale)
        c.setFillColor(ink_soft)
        c.drawCentredString(width / 2, 24 * scale, "Dibina dengan binaapp.")

    def next_page() -> float:
        draw_footer()
        c.showPage()
        return paint_page()

    y = paint_page()

    # Header — centred business name in ink, like the live preview
    title_size = 28 * scale
    c.setFont("Helvetica-Bold", title_size)
    c.setFillColor(ink)
    y -= title_size
    c.drawCentredString(width / 2, y, request.business_name)

    # Subtitle — uppercase accent line
    if request.subtitle.strip():
        sub_size = 11 * scale
        y -= sub_size + 8 * scale
        c.setFont("Helvetica-Bold", sub_size)
        c.setFillColor(accent)
        c.drawCentredString(width / 2, y, request.subtitle.strip().upper())

    # Short centred accent divider
    y -= 16 * scale
    c.setFillColor(accent)
    c.rect(width / 2 - 28 * scale, y, 56 * scale, 2 * scale, stroke=0, fill=1)
    y -= 26 * scale

    item_size = 14 * scale
    desc_size = 10 * scale
    cat_size = 11 * scale
    bottom_limit = 60 * scale

    for cat_label, cat_items in _grouped_items(request.items):
        if cat_label:
            if y - cat_size < bottom_limit:
                y = next_page()
            c.setFont("Helvetica-Bold", cat_size)
            c.setFillColor(accent)
            c.drawString(margin, y - cat_size, cat_label.upper())
            y -= cat_size + 10 * scale

        for item in cat_items:
            if y - item_size < bottom_limit:
                y = next_page()
            y -= item_size

            name = item.name
            price = f"RM{item.price}"

            c.setFont("Helvetica-Bold", item_size)
            c.setFillColor(ink)
            c.drawString(margin, y, name)

            c.setFillColor(accent)
            c.drawRightString(width - margin, y, price)

            # Dotted leader between name and price
            name_end = margin + c.stringWidth(name, "Helvetica-Bold", item_size)
            price_start = width - margin - c.stringWidth(price, "Helvetica-Bold", item_size)
            if price_start - name_end > 12 * scale:
                c.setStrokeColor(leader)
                c.setLineWidth(1)
                c.setDash(1, 3)
                c.line(name_end + 6 * scale, y + 1, price_start - 6 * scale, y + 1)
                c.setDash()

            y -= 10 * scale

        # Descriptions collected under the category, italic and softened
        described = [i for i in cat_items if i.description.strip()]
        if described:
            y -= 2 * scale
            c.setFont("Helvetica-Oblique", desc_size)
            c.setFillColor(ink_soft)
            for item in described:
                lines = simpleSplit(
                    f"{item.name}: {item.description.strip()}",
                    "Helvetica-Oblique", desc_size, content_width,
                )
                for line in lines:
                    if y - desc_size < bottom_limit:
                        y = next_page()
                        c.setFont("Helvetica-Oblique", desc_size)
                        c.setFillColor(ink_soft)
                    y -= desc_size + 2 * scale
                    c.drawString(margin, y, line)

        y -= 18 * scale

    draw_footer()
    c.save()

    buffer.seek(0)
    pdf_data = buffer.getvalue()
    buffer.close()
    return pdf_data


@router.post("/generate-menu")
async def generate_menu(request: MenuRequest):
    try:
        pdf_data = render_menu_pdf(request)

        # Upload to Supabase using REST API
        filename = f"menu_{uuid.uuid4()}.pdf"

        url = f"{settings.SUPABASE_URL}/storage/v1/object/menus/{filename}"

        headers = {
            "apikey": settings.SUPABASE_SERVICE_ROLE_KEY,
            "Authorization": f"Bearer {settings.SUPABASE_SERVICE_ROLE_KEY}",
            "Content-Type": "application/pdf"
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                url,
                headers=headers,
                content=pdf_data,
                timeout=30.0
            )

        if response.status_code in [200, 201]:
            pdf_url = f"{settings.SUPABASE_URL}/storage/v1/object/public/menus/{filename}"
            return {
                "success": True,
                "pdf_url": pdf_url
            }
        else:
            raise HTTPException(
                status_code=500,
                detail=f"Upload failed: {response.text}"
            )

    except HTTPException:
        raise
    except Exception as e:
        print(f"Menu generation error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )
