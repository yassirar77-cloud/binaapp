"""POST /api/menu/read-image — read a menu board photo into item rows.

Called by the create page's "Baca menu dari gambar" so the merchant can
review the rows before generating. Returns {"success", "is_menu", "items",
"available"}; ``available=false`` when no vision model is configured.
"""

from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from app.services.menu_ocr import read_menu_from_image

router = APIRouter()


class ReadMenuImageRequest(BaseModel):
    image_url: str = Field(..., min_length=8, max_length=1000)


@router.post("/menu/read-image")
async def read_menu_image(body: ReadMenuImageRequest):
    from app.services.ai_service import ai_service

    url = body.image_url.strip()
    if not url.lower().startswith(("http://", "https://")):
        return JSONResponse(status_code=400, content={"success": False, "error": "image_url must be an http(s) URL"})
    if not (ai_service.qwen_api_key or ai_service.zai_api_key):
        return JSONResponse(status_code=200, content={"success": True, "available": False, "is_menu": False, "items": []})
    result = await read_menu_from_image(url, call_model=ai_service._call_image_check_model)
    return {"success": True, "available": True, "is_menu": result["is_menu"], "items": result["items"]}


class ImageRoleRequest(BaseModel):
    image_url: str = Field(..., min_length=8, max_length=1000)


@router.post("/image/role")
async def image_role(body: ImageRoleRequest):
    """POST /api/image/role — is this upload a poster / menu board?

    The create page asks right after a hero upload: a portrait image, or
    one the vision model reports as text-heavy, is a poster (a menu board,
    a promo flyer) and makes a bad hero. Returns {"success", "poster",
    "portrait", "text_heavy", "width", "height", "text_checked"}; the
    shape probe always runs, the text check only when a vision model is
    configured.
    """
    from app.services import image_roles
    from app.services.ai_service import ai_service

    url = body.image_url.strip()
    if not url.lower().startswith(("http://", "https://")):
        return JSONResponse(status_code=400, content={"success": False, "error": "image_url must be an http(s) URL"})
    shape = await image_roles.probe_shape(url)
    text_checked = False
    if not shape.portrait and (ai_service.qwen_api_key or ai_service.zai_api_key):
        try:
            from app.services import image_vision_check
            verdict = await image_vision_check.check_image(
                url, "a photo for a business website", call_model=ai_service._call_image_check_model,
            )
            text_checked = bool(getattr(verdict, "checked", True))
            shape.text_heavy = bool(verdict.has_text)
        except Exception:
            text_checked = False
    return {
        "success": True, "poster": shape.poster, "portrait": shape.portrait, "text_heavy": shape.text_heavy,
        "width": shape.width, "height": shape.height, "text_checked": text_checked,
    }
