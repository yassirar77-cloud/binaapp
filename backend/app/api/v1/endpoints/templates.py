"""
Templates Endpoints
Provides pre-made templates for quick website generation
"""

from fastapi import APIRouter, HTTPException, status
from typing import List
from loguru import logger

from app.models.schemas import TemplateResponse, TemplateCategory

router = APIRouter()


# Sample templates (in production, these would come from database)
TEMPLATES = [
    {
        "id": "template-restaurant-1",
        "name": "Restoran Nasi Lemak",
        "category": TemplateCategory.RESTAURANT,
        "description": "Template untuk restoran Melayu dengan menu, galeri, dan WhatsApp ordering",
        "thumbnail_url": "/templates/thumbnails/restaurant-1.jpg",
        "preview_url": "/templates/previews/restaurant-1.html"
    },
    {
        "id": "template-retail-1",
        "name": "Kedai Runcit",
        "category": TemplateCategory.RETAIL,
        "description": "Template untuk kedai runcit dengan senarai produk dan shopping cart",
        "thumbnail_url": "/templates/thumbnails/retail-1.jpg",
        "preview_url": "/templates/previews/retail-1.html"
    },
    {
        "id": "template-services-1",
        "name": "Servis Pembaikan",
        "category": TemplateCategory.SERVICES,
        "description": "Template untuk perniagaan servis dengan borang tempahan",
        "thumbnail_url": "/templates/thumbnails/services-1.jpg",
        "preview_url": "/templates/previews/services-1.html"
    },
    {
        "id": "template-landing-1",
        "name": "Landing Page Promosi",
        "category": TemplateCategory.LANDING,
        "description": "Landing page untuk kempen promosi dengan call-to-action",
        "thumbnail_url": "/templates/thumbnails/landing-1.jpg",
        "preview_url": "/templates/previews/landing-1.html"
    },
    {
        "id": "template-portfolio-1",
        "name": "Portfolio Kreatif",
        "category": TemplateCategory.PORTFOLIO,
        "description": "Portfolio untuk pekerja bebas dan kreatif",
        "thumbnail_url": "/templates/thumbnails/portfolio-1.jpg",
        "preview_url": "/templates/previews/portfolio-1.html"
    }
]


@router.get("/", response_model=List[TemplateResponse])
async def list_templates(category: TemplateCategory = None):
    """
    Get all available templates, optionally filtered by category
    """
    try:
        templates = TEMPLATES

        if category:
            templates = [t for t in templates if t["category"] == category]

        return [
            TemplateResponse(**template)
            for template in templates
        ]

    except Exception as e:
        logger.error(f"Error listing templates: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve templates"
        )


@router.get("/{template_id}", response_model=TemplateResponse)
async def get_template(template_id: str):
    """
    Get a specific template by ID
    """
    try:
        template = next((t for t in TEMPLATES if t["id"] == template_id), None)

        if not template:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Template not found"
            )

        return TemplateResponse(**template)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting template: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve template"
        )


@router.get("/categories/list", response_model=List[dict])
async def list_categories():
    """
    Get all template categories
    """
    return [
        {
            "value": TemplateCategory.RESTAURANT,
            "label": "Restoran & F&B",
            "description": "Template untuk restoran, kafe, dan perniagaan makanan"
        },
        {
            "value": TemplateCategory.RETAIL,
            "label": "Kedai Runcit & E-Dagang",
            "description": "Template untuk kedai dan jualan online"
        },
        {
            "value": TemplateCategory.SERVICES,
            "label": "Perkhidmatan",
            "description": "Template untuk perniagaan berasaskan servis"
        },
        {
            "value": TemplateCategory.LANDING,
            "label": "Landing Page",
            "description": "Halaman promosi dan kempen marketing"
        },
        {
            "value": TemplateCategory.PORTFOLIO,
            "label": "Portfolio",
            "description": "Portfolio peribadi dan profesional"
        }
    ]
