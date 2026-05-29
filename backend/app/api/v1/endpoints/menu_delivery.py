"""
Menu and Delivery Management API Endpoints
"""

from fastapi import APIRouter, HTTPException, Depends, status
from typing import List, Optional
from pydantic import BaseModel
from loguru import logger
from supabase import Client

from app.models.schemas import (
    MenuCategoryCreate, MenuCategoryUpdate, MenuCategoryResponse,
    MenuItemCreate, MenuItemUpdate, MenuItemResponse,
    DeliveryZoneCreate, DeliveryZoneUpdate, DeliveryZoneResponse
)
from app.core.supabase import get_supabase_client
from app.core.security import get_current_user
from app.services.ai_service import ai_service
from app.services.subscription_service import subscription_service

router = APIRouter()


# Shared over-quota message for AI image generation. Surfaced to the UI so it
# can nudge the user to upload their own photo or upgrade their plan.
AI_IMAGE_QUOTA_MESSAGE = (
    "Had imej AI anda telah tercapai. Anda boleh muat naik foto sendiri atau "
    "naik taraf pelan untuk menjana lebih banyak imej AI."
)


# ============================================================
# IMAGE GENERATION ENDPOINTS
# ============================================================

class GenerateFoodImageRequest(BaseModel):
    """Request to generate AI image for food item"""
    food_name: str
    description: Optional[str] = None


class GenerateFoodImageResponse(BaseModel):
    """Response with generated image URL.

    When the user is over their AI-image quota, no image is generated:
    image_url is null and ai_image_skipped is True with an explanatory message.
    """
    image_url: Optional[str] = None
    food_name: str
    ai_image_skipped: bool = False
    ai_image_message: Optional[str] = None


@router.post("/generate-food-image", response_model=GenerateFoodImageResponse)
async def generate_food_image(
    request: GenerateFoodImageRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Generate AI image for a food item using Stability AI.
    The image is uploaded to Cloudinary and the URL is returned.

    Example:
    - Input: "Nasi Kandar Special" → Generates realistic nasi kandar image
    - Input: "Ayam Goreng Berempah" → Generates Malaysian fried chicken image
    """
    try:
        logger.info(f"🎨 User {current_user['email']} requesting image for: {request.food_name}")

        # Enforce the owner's per-plan AI-image quota (same as the website
        # generator and create_menu_item). Over quota → graceful skip, not 500.
        image_check = await subscription_service.check_limit(
            current_user["id"], "generate_ai_image"
        )
        if not image_check.get("allowed"):
            logger.info(
                f"🚫 AI image limit reached for user {current_user['id']} — "
                f"skipping image for '{request.food_name}'"
            )
            return GenerateFoodImageResponse(
                image_url=None,
                food_name=request.food_name,
                ai_image_skipped=True,
                ai_image_message=AI_IMAGE_QUOTA_MESSAGE,
            )

        # Generate AI image
        image_url = await ai_service.generate_food_image(request.food_name)

        if not image_url:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to generate image. Please try again or contact support."
            )

        # Only count usage once an image was actually produced.
        try:
            await subscription_service.increment_usage(
                current_user["id"], "generate_ai_image"
            )
            logger.info(f"📊 Incremented ai_images_used for user {current_user['id']}")
        except Exception as usage_err:
            logger.warning(f"⚠️ AI image usage tracking failed: {usage_err}")

        return GenerateFoodImageResponse(
            image_url=image_url,
            food_name=request.food_name
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating food image: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error generating image: {str(e)}"
        )


# ============================================================
# MENU CATEGORIES ENDPOINTS
# ============================================================

@router.post("/websites/{website_id}/menu-categories", response_model=MenuCategoryResponse, status_code=status.HTTP_201_CREATED)
async def create_menu_category(
    website_id: str,
    category: MenuCategoryCreate,
    current_user: dict = Depends(get_current_user),
    supabase: Client = Depends(get_supabase_client)
):
    """Create a new menu category"""
    try:
        # Verify ownership
        website_check = supabase.table("websites").select("user_id").eq("id", website_id).execute()
        if not website_check.data or website_check.data[0]["user_id"] != current_user["id"]:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to modify this website")

        # Create category
        category.website_id = website_id
        result = supabase.table("menu_categories").insert(category.dict()).execute()

        if not result.data:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to create category")

        return result.data[0]
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating menu category: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/websites/{website_id}/menu-categories", response_model=List[MenuCategoryResponse])
async def get_menu_categories(
    website_id: str,
    supabase: Client = Depends(get_supabase_client)
):
    """Get all menu categories for a website (public endpoint)"""
    try:
        result = supabase.table("menu_categories")\
            .select("*")\
            .eq("website_id", website_id)\
            .order("sort_order")\
            .execute()

        return result.data
    except Exception as e:
        logger.error(f"Error fetching menu categories: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.put("/websites/{website_id}/menu-categories/{category_id}", response_model=MenuCategoryResponse)
async def update_menu_category(
    website_id: str,
    category_id: str,
    category_update: MenuCategoryUpdate,
    current_user: dict = Depends(get_current_user),
    supabase: Client = Depends(get_supabase_client)
):
    """Update a menu category"""
    try:
        # Verify ownership
        website_check = supabase.table("websites").select("user_id").eq("id", website_id).execute()
        if not website_check.data or website_check.data[0]["user_id"] != current_user["id"]:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")

        # Update category
        update_data = category_update.dict(exclude_unset=True)
        if not update_data:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No fields to update")

        result = supabase.table("menu_categories")\
            .update(update_data)\
            .eq("id", category_id)\
            .eq("website_id", website_id)\
            .execute()

        if not result.data:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found")

        return result.data[0]
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating menu category: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.delete("/websites/{website_id}/menu-categories/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_menu_category(
    website_id: str,
    category_id: str,
    current_user: dict = Depends(get_current_user),
    supabase: Client = Depends(get_supabase_client)
):
    """Delete a menu category"""
    try:
        # Verify ownership
        website_check = supabase.table("websites").select("user_id").eq("id", website_id).execute()
        if not website_check.data or website_check.data[0]["user_id"] != current_user["id"]:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")

        # Delete category
        result = supabase.table("menu_categories")\
            .delete()\
            .eq("id", category_id)\
            .eq("website_id", website_id)\
            .execute()

        if not result.data:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found")

        return None
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting menu category: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


# ============================================================
# MENU ITEMS ENDPOINTS
# ============================================================

class CreateMenuItemResponse(MenuItemResponse):
    """Menu item response, plus feedback when AI image generation was skipped
    because the owner reached their plan's AI-image quota. The item is always
    created regardless; these fields just tell the UI what happened."""
    ai_image_skipped: bool = False
    ai_image_message: Optional[str] = None


@router.post("/websites/{website_id}/menu-items", response_model=CreateMenuItemResponse, status_code=status.HTTP_201_CREATED)
async def create_menu_item(
    website_id: str,
    item: MenuItemCreate,
    auto_generate_image: bool = True,
    current_user: dict = Depends(get_current_user),
    supabase: Client = Depends(get_supabase_client)
):
    """
    Create a new menu item

    If auto_generate_image=True (default) and no image_url is provided,
    the system will automatically generate an AI image using Stability AI.
    AI image generation is subject to the owner's per-plan AI-image quota
    (same limit the website generator enforces). When the quota is exhausted
    the item is still created, just without an AI image.
    """
    try:
        # Verify ownership
        website_check = supabase.table("websites").select("user_id").eq("id", website_id).execute()
        if not website_check.data or website_check.data[0]["user_id"] != current_user["id"]:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")

        # Auto-generate image if not provided — but only within the owner's
        # per-plan AI-image quota (same enforcement as the website generator).
        ai_image_skipped = False
        ai_image_message: Optional[str] = None
        if auto_generate_image and not item.image_url:
            image_check = await subscription_service.check_limit(
                current_user["id"], "generate_ai_image"
            )
            if image_check.get("allowed"):
                logger.info(f"🎨 Auto-generating image for menu item: {item.name}")
                try:
                    generated_url = await ai_service.generate_food_image(item.name)
                    if generated_url:
                        item.image_url = generated_url
                        logger.info(f"✅ Generated image: {generated_url[:60]}...")
                        # Only count usage once an image was actually produced,
                        # so a failed generation doesn't burn the user's quota.
                        try:
                            await subscription_service.increment_usage(
                                current_user["id"], "generate_ai_image"
                            )
                            logger.info(f"📊 Incremented ai_images_used for user {current_user['id']}")
                        except Exception as usage_err:
                            logger.warning(f"⚠️ AI image usage tracking failed: {usage_err}")
                    else:
                        logger.warning("⚠️ Image generation failed, creating without image")
                except Exception as e:
                    logger.error(f"❌ Image generation error: {e}, creating without image")
            else:
                # Over quota: create the item without an image and tell the user.
                ai_image_skipped = True
                ai_image_message = AI_IMAGE_QUOTA_MESSAGE
                logger.info(
                    f"🚫 AI image limit reached for user {current_user['id']} — "
                    f"creating '{item.name}' without an AI image"
                )

        # Create item
        item.website_id = website_id
        result = supabase.table("menu_items").insert(item.dict()).execute()

        if not result.data:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to create item")

        return {
            **result.data[0],
            "ai_image_skipped": ai_image_skipped,
            "ai_image_message": ai_image_message,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating menu item: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/websites/{website_id}/menu-items", response_model=List[MenuItemResponse])
async def get_menu_items(
    website_id: str,
    category_id: Optional[str] = None,
    available_only: bool = False,
    supabase: Client = Depends(get_supabase_client)
):
    """Get all menu items for a website with optional filtering"""
    try:
        query = supabase.table("menu_items").select("*").eq("website_id", website_id)

        if category_id:
            query = query.eq("category_id", category_id)

        if available_only:
            query = query.eq("is_available", True)

        result = query.order("sort_order").execute()
        return result.data
    except Exception as e:
        logger.error(f"Error fetching menu items: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.put("/websites/{website_id}/menu-items/{item_id}", response_model=MenuItemResponse)
async def update_menu_item(
    website_id: str,
    item_id: str,
    item_update: MenuItemUpdate,
    current_user: dict = Depends(get_current_user),
    supabase: Client = Depends(get_supabase_client)
):
    """Update a menu item"""
    try:
        # Verify ownership
        website_check = supabase.table("websites").select("user_id").eq("id", website_id).execute()
        if not website_check.data or website_check.data[0]["user_id"] != current_user["id"]:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")

        # Update item
        update_data = item_update.dict(exclude_unset=True)
        if not update_data:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No fields to update")

        result = supabase.table("menu_items")\
            .update(update_data)\
            .eq("id", item_id)\
            .eq("website_id", website_id)\
            .execute()

        if not result.data:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")

        return result.data[0]
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating menu item: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.patch("/websites/{website_id}/menu-items/{item_id}/availability", response_model=MenuItemResponse)
async def toggle_menu_item_availability(
    website_id: str,
    item_id: str,
    is_available: bool,
    current_user: dict = Depends(get_current_user),
    supabase: Client = Depends(get_supabase_client)
):
    """Toggle menu item availability"""
    try:
        # Verify ownership
        website_check = supabase.table("websites").select("user_id").eq("id", website_id).execute()
        if not website_check.data or website_check.data[0]["user_id"] != current_user["id"]:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")

        # Update availability
        result = supabase.table("menu_items")\
            .update({"is_available": is_available})\
            .eq("id", item_id)\
            .eq("website_id", website_id)\
            .execute()

        if not result.data:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")

        return result.data[0]
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error toggling availability: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.delete("/websites/{website_id}/menu-items/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_menu_item(
    website_id: str,
    item_id: str,
    current_user: dict = Depends(get_current_user),
    supabase: Client = Depends(get_supabase_client)
):
    """Delete a menu item"""
    try:
        # Verify ownership
        website_check = supabase.table("websites").select("user_id").eq("id", website_id).execute()
        if not website_check.data or website_check.data[0]["user_id"] != current_user["id"]:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")

        # Delete item
        result = supabase.table("menu_items")\
            .delete()\
            .eq("id", item_id)\
            .eq("website_id", website_id)\
            .execute()

        if not result.data:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")

        return None
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting menu item: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


# ============================================================
# DELIVERY ZONES ENDPOINTS
# ============================================================

@router.post("/websites/{website_id}/delivery-zones", response_model=DeliveryZoneResponse, status_code=status.HTTP_201_CREATED)
async def create_delivery_zone(
    website_id: str,
    zone: DeliveryZoneCreate,
    current_user: dict = Depends(get_current_user),
    supabase: Client = Depends(get_supabase_client)
):
    """Create a new delivery zone"""
    try:
        # Verify ownership
        website_check = supabase.table("websites").select("user_id").eq("id", website_id).execute()
        if not website_check.data or website_check.data[0]["user_id"] != current_user["id"]:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")

        # Create zone
        zone.website_id = website_id
        result = supabase.table("delivery_zones").insert(zone.dict()).execute()

        if not result.data:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to create zone")

        return result.data[0]
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating delivery zone: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/websites/{website_id}/delivery-zones", response_model=List[DeliveryZoneResponse])
async def get_delivery_zones(
    website_id: str,
    active_only: bool = False,
    supabase: Client = Depends(get_supabase_client)
):
    """Get all delivery zones for a website"""
    try:
        query = supabase.table("delivery_zones").select("*").eq("website_id", website_id)

        if active_only:
            query = query.eq("active", True)

        result = query.order("sort_order").execute()
        return result.data
    except Exception as e:
        logger.error(f"Error fetching delivery zones: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.put("/websites/{website_id}/delivery-zones/{zone_id}", response_model=DeliveryZoneResponse)
async def update_delivery_zone(
    website_id: str,
    zone_id: str,
    zone_update: DeliveryZoneUpdate,
    current_user: dict = Depends(get_current_user),
    supabase: Client = Depends(get_supabase_client)
):
    """Update a delivery zone"""
    try:
        # Verify ownership
        website_check = supabase.table("websites").select("user_id").eq("id", website_id).execute()
        if not website_check.data or website_check.data[0]["user_id"] != current_user["id"]:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")

        # Update zone
        update_data = zone_update.dict(exclude_unset=True)
        if not update_data:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No fields to update")

        result = supabase.table("delivery_zones")\
            .update(update_data)\
            .eq("id", zone_id)\
            .eq("website_id", website_id)\
            .execute()

        if not result.data:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Zone not found")

        return result.data[0]
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating delivery zone: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.delete("/websites/{website_id}/delivery-zones/{zone_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_delivery_zone(
    website_id: str,
    zone_id: str,
    current_user: dict = Depends(get_current_user),
    supabase: Client = Depends(get_supabase_client)
):
    """Delete a delivery zone"""
    try:
        # Verify ownership
        website_check = supabase.table("websites").select("user_id").eq("id", website_id).execute()
        if not website_check.data or website_check.data[0]["user_id"] != current_user["id"]:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")

        # Delete zone
        result = supabase.table("delivery_zones")\
            .delete()\
            .eq("id", zone_id)\
            .eq("website_id", website_id)\
            .execute()

        if not result.data:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Zone not found")

        return None
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting delivery zone: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.patch("/websites/{website_id}/delivery-zones/reorder", response_model=List[DeliveryZoneResponse])
async def reorder_delivery_zones(
    website_id: str,
    zone_ids: List[str],
    current_user: dict = Depends(get_current_user),
    supabase: Client = Depends(get_supabase_client)
):
    """Reorder delivery zones"""
    try:
        # Verify ownership
        website_check = supabase.table("websites").select("user_id").eq("id", website_id).execute()
        if not website_check.data or website_check.data[0]["user_id"] != current_user["id"]:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")

        # Update sort order for each zone
        updated_zones = []
        for index, zone_id in enumerate(zone_ids):
            result = supabase.table("delivery_zones")\
                .update({"sort_order": index})\
                .eq("id", zone_id)\
                .eq("website_id", website_id)\
                .execute()

            if result.data:
                updated_zones.extend(result.data)

        return updated_zones
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error reordering delivery zones: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
