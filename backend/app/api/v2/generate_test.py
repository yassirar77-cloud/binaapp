"""
V2 Test Endpoint — POST /api/v2/generate-test

Accepts a DesignBrief JSON, runs it through recipe_builder + html_renderer,
and returns the assembled HTML. No AI involved — this is for validating the
assembler pipeline end-to-end.

This endpoint is temporary and will be removed once Stage 1 AI is wired up.
"""

from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import ValidationError

from app.schemas.recipe import DesignBrief
from app.services.recipe_builder import build_recipe
from app.services.html_renderer import render_html

router = APIRouter(prefix="/api/v2", tags=["V2 Generation"])


@router.post("/generate-test")
async def generate_test(brief_data: dict):
    """
    Accepts a raw Design Brief JSON, validates it, builds a Page Recipe,
    and returns assembled HTML.

    Returns JSON with:
      - html: the assembled HTML string
      - recipe: the resolved PageRecipe (for debugging)
      - meta: page metadata
    """
    # 1. Validate the Design Brief
    try:
        brief = DesignBrief(**brief_data)
    except ValidationError as e:
        raise HTTPException(
            status_code=422,
            detail={
                "error": "Invalid Design Brief",
                "validation_errors": e.errors(),
            },
        )

    # 2. Build the Page Recipe (deterministic, no AI)
    try:
        recipe = build_recipe(brief)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={"error": f"Recipe build failed: {str(e)}"},
        )

    # 3. Render to HTML
    try:
        html = render_html(recipe)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={"error": f"HTML render failed: {str(e)}"},
        )

    return JSONResponse({
        "success": True,
        "html": html,
        "html_size_bytes": len(html.encode("utf-8")),
        "sections_count": len(recipe.sections),
        "components_used": [s.component for s in recipe.sections],
        "style_dna": recipe.theme.style_dna.value,
        "meta": {
            "title": recipe.meta.title,
            "description": recipe.meta.description,
        },
    })


@router.post("/generate-test/preview")
async def generate_test_preview(brief_data: dict):
    """
    Same as /generate-test but returns the HTML directly as text/html,
    so you can open it in a browser to preview.
    """
    try:
        brief = DesignBrief(**brief_data)
    except ValidationError as e:
        raise HTTPException(status_code=422, detail={"error": str(e)})

    recipe = build_recipe(brief)
    html = render_html(recipe)

    return HTMLResponse(content=html)
