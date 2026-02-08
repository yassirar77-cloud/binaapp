"""
Template Gallery Endpoints
Provides the design template gallery for website generation.
This is separate from the existing templates.py which handles
pre-made website templates and categories.
"""

from fastapi import APIRouter
from typing import Optional

from app.services.template_gallery import (
    get_all_templates,
    get_templates_for_business,
    get_template,
)

router = APIRouter()


@router.get("/gallery")
async def list_gallery_templates():
    """Get all available design templates for the gallery."""
    return {"templates": get_all_templates()}


@router.get("/gallery/recommended/{business_type}")
async def recommended_gallery_templates(business_type: str):
    """Get recommended design templates for a business type."""
    return {"templates": get_templates_for_business(business_type)}


@router.get("/gallery/{template_id}")
async def get_gallery_template(template_id: str):
    """Get a specific design template by ID."""
    template = get_template(template_id)
    if not template:
        return {"error": "Template not found"}
    return {
        "id": template["id"],
        "name": template["name"],
        "name_ms": template["name_ms"],
        "description": template["description"],
        "description_ms": template["description_ms"],
        "preview_image": template["preview_image"],
        "category": template["category"],
        "best_for": template["best_for"],
        "color_mode": template["color_mode"],
        "colors": template["colors"],
        "fonts": template["fonts"],
    }
