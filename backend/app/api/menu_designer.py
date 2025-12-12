from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4, A5
from reportlab.lib.utils import ImageReader
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

class MenuRequest(BaseModel):
    business_name: str
    items: list[MenuItem]
    size: str = "A4"
    style: str = "modern"

@router.post("/generate-menu")
async def generate_menu(request: MenuRequest):
    try:
        # Create PDF buffer
        buffer = io.BytesIO()
        
        # Set page size
        if request.size == "A4":
            page_size = A4
        elif request.size == "A5":
            page_size = A5
        else:  # banner
            page_size = (36*72, 24*72)
        
        # Create canvas
        c = canvas.Canvas(buffer, pagesize=page_size)
        width, height = page_size
        
        # Draw header
        c.setFont("Helvetica-Bold", 32)
        c.drawCentredString(width/2, height-60, request.business_name)
        
        # Draw decorative line
        c.setStrokeColorRGB(0.4, 0.49, 0.91)
        c.setLineWidth(3)
        c.line(50, height-80, width-50, height-80)
        
        # Draw menu items
        y_position = height - 130
        for item in request.items:
            # Item name
            c.setFont("Helvetica-Bold", 18)
            c.drawString(70, y_position, item.name)
            
            # Price
            c.setFont("Helvetica-Bold", 18)
            c.setFillColorRGB(0.9, 0.22, 0.27)
            c.drawRightString(width-70, y_position, f"RM{item.price}")
            
            # Description
            if item.description:
                c.setFont("Helvetica", 12)
                c.setFillColorRGB(0.4, 0.4, 0.4)
                c.drawString(70, y_position-20, item.description)
            
            # Separator line
            c.setStrokeColorRGB(0.9, 0.9, 0.9)
            c.setLineWidth(1)
            c.line(50, y_position-40, width-50, y_position-40)
            
            y_position -= 80
            
            # New page if needed
            if y_position < 100:
                c.showPage()
                y_position = height - 50
        
        # Footer
        c.setFont("Helvetica", 10)
        c.setFillColorRGB(0.6, 0.6, 0.6)
        c.drawCentredString(width/2, 30, "Menu created with BinaApp")
        
        c.save()
        
        # Get PDF data
        buffer.seek(0)
        pdf_data = buffer.getvalue()
        buffer.close()
        
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
            
    except Exception as e:
        print(f"Menu generation error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )