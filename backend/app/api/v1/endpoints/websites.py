"""
Website Endpoints
Handles website generation, management, and publishing
"""

from fastapi import APIRouter, HTTPException, status, Depends, BackgroundTasks
from typing import List
from loguru import logger
from datetime import datetime
import uuid

from app.models.schemas import (
    WebsiteGenerationRequest,
    WebsiteResponse,
    WebsiteListResponse,
    PublishRequest,
    PublishResponse,
    WebsiteStatus
)
from app.services.supabase_client import supabase_service
from app.core.security import get_current_user
from app.services.ai_service import ai_service
from app.services.storage_service import storage_service
from app.services.templates import TemplateService
from app.core.config import settings

router = APIRouter()


@router.post("/generate", response_model=WebsiteResponse, status_code=status.HTTP_201_CREATED)
async def generate_website(
    request: WebsiteGenerationRequest,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user)
):
    """
    Generate a new website using AI
    """
    try:
        user_id = current_user.get("sub")

        # Check subdomain availability
        subdomain_available = await supabase_service.check_subdomain_available(request.subdomain)
        if not subdomain_available:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Subdomain already taken"
            )

        # Check if storage also has this subdomain
        storage_exists = await storage_service.check_subdomain_exists(request.subdomain)
        if storage_exists:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Subdomain already exists in storage"
            )

        # Create website record
        website_id = str(uuid.uuid4())
        website_data = {
            "id": website_id,
            "user_id": user_id,
            "business_name": request.business_name,
            "business_type": request.business_type,
            "subdomain": request.subdomain,
            "status": WebsiteStatus.GENERATING,
            "language": request.language,
            "include_whatsapp": request.include_whatsapp,
            "whatsapp_number": request.whatsapp_number,
            "include_maps": request.include_maps,
            "location_address": request.location_address,
            "include_ecommerce": request.include_ecommerce,
            "contact_email": request.contact_email,
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat()
        }

        website = await supabase_service.create_website(website_data)

        # Generate website in background
        background_tasks.add_task(
            generate_website_content,
            website_id,
            request
        )

        logger.info(f"Website generation started: {website_id}")

        return WebsiteResponse(
            id=website["id"],
            user_id=website["user_id"],
            business_name=website["business_name"],
            subdomain=website["subdomain"],
            full_url=f"https://{request.subdomain}{settings.SUBDOMAIN_SUFFIX}",
            status=WebsiteStatus.GENERATING,
            created_at=datetime.fromisoformat(website["created_at"]),
            updated_at=datetime.fromisoformat(website["updated_at"]),
            published_at=None,
            html_content=None,
            preview_url=None
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating website: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate website"
        )


async def generate_website_content(website_id: str, request: WebsiteGenerationRequest):
    """
    Background task to generate website content using AI
    """
    import asyncio

    try:
        logger.info(f"🚀 Starting website generation for {website_id}")
        logger.info(f"   Business: {request.business_name}")
        logger.info(f"   Language: {request.language}")
        logger.info(f"   Include E-commerce: {request.include_ecommerce}")

        # Step 1: Generate HTML using AI with timeout (3 minutes max)
        logger.info(f"⏱️  Step 1/4: Calling AI generation service (max 180s timeout)...")
        try:
            ai_response = await asyncio.wait_for(
                ai_service.generate_website(request),
                timeout=180.0  # 3 minutes timeout for entire AI generation
            )
            logger.info(f"✅ Step 1/4: AI generation completed - {len(ai_response.html_content)} chars generated")
        except asyncio.TimeoutError:
            error_msg = "AI generation timed out after 180 seconds. Please try again with a shorter description or fewer features."
            logger.error(f"❌ {error_msg}")
            raise Exception(error_msg)

        html_content = ai_response.html_content
        integrations = ai_response.integrations_included

        # Step 2: Inject delivery widget if needed
        logger.info(f"⏱️  Step 2/4: Processing delivery widget...")
        if request.include_ecommerce:
            logger.info(f"🛒 Delivery mode enabled - injecting delivery widget for website {website_id}")

            # Initialize template service
            template_service = TemplateService()

            # Inject delivery widget with website_id
            html_content = template_service.inject_delivery_widget(
                html=html_content,
                website_id=website_id,
                whatsapp_number=request.whatsapp_number or "+60123456789",
                primary_color="#ea580c",  # Default orange color
                business_type=request.business_type,
                description=request.description,
                language=request.language.value if hasattr(request, 'language') and request.language else "ms"
            )

            # Update integrations list to include delivery
            integrations = ["BinaApp Delivery", "WhatsApp Contact", "Mobile Responsive", "Cloudinary Images"]
            logger.info(f"✅ Step 2/4: Delivery widget injected successfully")
        else:
            logger.info(f"⏭️  Step 2/4: Delivery widget skipped (not enabled)")

        # Step 3: Inject chat widget
        logger.info(f"⏱️  Step 3/4: Injecting chat widget...")
        template_service = TemplateService()
        html_content = template_service.inject_chat_widget(
            html=html_content,
            website_id=website_id,
            api_url="https://binaapp-backend.onrender.com"
        )
        logger.info(f"✅ Step 3/4: Chat widget injected successfully")

        # Step 4: Update database
        logger.info(f"⏱️  Step 4/4: Updating database...")
        update_data = {
            "html_content": html_content,
            "status": WebsiteStatus.DRAFT,
            "meta_title": ai_response.meta_title,
            "meta_description": ai_response.meta_description,
            "sections": ai_response.sections,
            "integrations": integrations,
            "updated_at": datetime.utcnow().isoformat()
        }

        await supabase_service.update_website(website_id, update_data)

        logger.info(f"✅ Step 4/4: Database updated successfully")
        logger.info(f"🎉 Website generation completed successfully: {website_id}")

    except asyncio.TimeoutError:
        error_msg = "Generation timed out - please try again"
        logger.error(f"❌ Timeout error for website {website_id}: {error_msg}")

        # Mark website as failed
        await supabase_service.update_website(website_id, {
            "status": WebsiteStatus.FAILED,
            "error_message": error_msg,
            "updated_at": datetime.utcnow().isoformat()
        })

    except Exception as e:
        logger.error(f"❌ Error in background generation for {website_id}: {str(e)}", exc_info=True)

        # Mark website as failed
        await supabase_service.update_website(website_id, {
            "status": WebsiteStatus.FAILED,
            "error_message": str(e),
            "updated_at": datetime.utcnow().isoformat()
        })


@router.get("/", response_model=List[WebsiteListResponse])
async def list_websites(current_user: dict = Depends(get_current_user)):
    """
    Get all websites for the current user
    """
    try:
        user_id = current_user.get("sub")
        websites = await supabase_service.get_user_websites(user_id)

        if not websites:
            return []

        result = []
        for w in websites:
            try:
                # Handle potential null/missing values
                website_status = w.get("status", "draft")
                # Ensure status is valid enum value
                if website_status not in ["draft", "generating", "published", "failed"]:
                    website_status = "draft"

                result.append(WebsiteListResponse(
                    id=w["id"],
                    business_name=w.get("business_name") or "Untitled",
                    subdomain=w.get("subdomain"),
                    full_url=f"https://{w['subdomain']}{settings.SUBDOMAIN_SUFFIX}" if w.get("subdomain") else None,
                    status=website_status,
                    created_at=datetime.fromisoformat(w["created_at"]) if w.get("created_at") else datetime.utcnow(),
                    published_at=datetime.fromisoformat(w["published_at"]) if w.get("published_at") else None
                ))
            except Exception as item_error:
                logger.warning(f"Skipping website {w.get('id')}: {item_error}")
                continue

        return result

    except Exception as e:
        logger.error(f"Error listing websites: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve websites"
        )


@router.get("/{website_id}", response_model=WebsiteResponse)
async def get_website(
    website_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Get a specific website by ID
    """
    try:
        website = await supabase_service.get_website(website_id)

        if not website:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Website not found"
            )

        # Check ownership
        if website["user_id"] != current_user.get("sub"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to access this website"
            )

        return WebsiteResponse(
            id=website["id"],
            user_id=website["user_id"],
            business_name=website["business_name"],
            subdomain=website["subdomain"],
            full_url=f"https://{website['subdomain']}{settings.SUBDOMAIN_SUFFIX}",
            status=website["status"],
            created_at=datetime.fromisoformat(website["created_at"]),
            updated_at=datetime.fromisoformat(website["updated_at"]),
            published_at=datetime.fromisoformat(website["published_at"]) if website.get("published_at") else None,
            html_content=website.get("html_content"),
            preview_url=website.get("preview_url")
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting website: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve website"
        )


@router.post("/{website_id}/publish", response_model=PublishResponse)
async def publish_website(
    website_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Publish website to subdomain
    """
    try:
        website = await supabase_service.get_website(website_id)

        if not website:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Website not found"
            )

        # Check ownership
        if website["user_id"] != current_user.get("sub"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to publish this website"
            )

        # Check if website is ready to publish
        if website["status"] != WebsiteStatus.DRAFT:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Website is not ready to publish"
            )

        if not website.get("html_content"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Website has no content to publish"
            )

        # Publish to Supabase Storage
        try:
            public_url = await storage_service.publish_website(
                subdomain=website["subdomain"],
                html_content=website["html_content"],
                website_id=website_id,
                user_id=current_user.get("sub")
            )
        except Exception as storage_error:
            logger.error(f"Storage upload failed for {website_id}: {storage_error}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to upload website to storage"
            )

        # Update website status in database
        published_at = datetime.utcnow()
        try:
            update_success = await supabase_service.update_website(website_id, {
                "status": WebsiteStatus.PUBLISHED,
                "published_at": published_at.isoformat(),
                "public_url": public_url,
                "updated_at": published_at.isoformat()
            })

            if not update_success:
                raise Exception("Database update returned failure")

        except Exception as db_error:
            # ROLLBACK: If database update fails, try to delete from storage
            logger.error(f"Database update failed for {website_id}: {db_error}")
            logger.warning(f"Attempting storage rollback for {website_id}...")
            try:
                await storage_service.delete_website(
                    user_id=current_user.get("sub"),
                    subdomain=website["subdomain"]
                )
                logger.info(f"Storage rollback successful for {website_id}")
            except Exception as rollback_error:
                logger.error(f"Storage rollback failed for {website_id}: {rollback_error}")
                # Note: This leaves orphaned storage, but sync script can clean up

            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update website status after publishing"
            )

        logger.info(f"Website published: {website_id} -> {public_url}")

        full_url = f"https://{website['subdomain']}{settings.SUBDOMAIN_SUFFIX}"

        return PublishResponse(
            success=True,
            url=full_url,
            message="Website published successfully",
            published_at=published_at
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error publishing website: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to publish website"
        )


@router.post("/{website_id}/fix-widget")
async def fix_website_widget(
    website_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Fix existing website HTML to add data-website-id to delivery widget script tag
    This is a maintenance endpoint to update websites created before the fix
    """
    try:
        import re

        # SECURITY: Extract user_id from authenticated token
        user_id = current_user.get("sub") or current_user.get("id")
        if not user_id:
            raise HTTPException(status_code=401, detail="User ID not found in token")

        logger.info(f"User {user_id} fixing widget for website: {website_id}")

        # Get website
        website = await supabase_service.get_website(website_id)

        if not website:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Website not found"
            )

        # SECURITY: Verify user owns this website
        if website.get('user_id') != user_id:
            logger.warning(f"User {user_id} attempted to modify unauthorized website: {website_id}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: You don't own this website"
            )

        html_content = website.get('html_content', '')

        if not html_content:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Website has no HTML content"
            )

        logger.info(f"Original HTML length: {len(html_content)}")

        # Check if already has data-website-id
        if 'data-website-id' in html_content:
            logger.info("Already has data-website-id")
            return {
                "success": True,
                "message": "Website already has data-website-id",
                "website_id": website_id,
                "subdomain": website.get('subdomain'),
                "changed": False
            }

        # Pattern to match old script tag (with or without init script)
        old_pattern = r'<script\s+src="[^"]*delivery-widget\.js"[^>]*>\s*</script>\s*(?:<script>.*?BinaAppDelivery\.init\(.*?\).*?</script>)?'

        # Check if pattern exists
        if not re.search(old_pattern, html_content, re.DOTALL):
            logger.warning("No delivery widget script tag found")
            return {
                "success": False,
                "message": "No delivery widget script tag found in HTML",
                "website_id": website_id,
                "subdomain": website.get('subdomain'),
                "changed": False
            }

        # New script tag with data-website-id
        new_script = f'''<script
  src="https://binaapp-backend.onrender.com/widgets/delivery-widget.js"
  data-website-id="{website_id}"
  data-api-url="https://binaapp-backend.onrender.com"
  data-primary-color="#ea580c"
  data-language="ms"
></script>
<div id="binaapp-widget"></div>'''

        # Replace old script with new script
        new_html = re.sub(old_pattern, new_script, html_content, flags=re.DOTALL)

        if new_html == html_content:
            logger.warning("Pattern didn't match, trying simpler pattern")
            # Try simpler pattern
            simple_pattern = r'<script\s+src="[^"]*delivery-widget\.js"[^>]*>\s*</script>'
            new_html = re.sub(simple_pattern, new_script, html_content)

        if new_html == html_content:
            return {
                "success": False,
                "message": "Could not find or replace script tag",
                "website_id": website_id,
                "subdomain": website.get('subdomain'),
                "changed": False
            }

        logger.info(f"New HTML length: {len(new_html)}")
        logger.info("Updating database...")

        # Update website
        await supabase_service.update_website(website_id, {
            "html_content": new_html,
            "updated_at": datetime.utcnow().isoformat()
        })

        logger.info(f"✅ Successfully fixed website: {website['subdomain']}")

        return {
            "success": True,
            "message": f"Website HTML updated successfully",
            "website_id": website_id,
            "subdomain": website.get('subdomain'),
            "changed": True,
            "url": f"https://{website.get('subdomain')}.binaapp.my"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fixing website widget: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fix website: {str(e)}"
        )


@router.post("/fix-all-widgets")
async def fix_all_website_widgets():
    """
    Fix ALL websites to add data-website-id to delivery widget script tags
    This is a maintenance endpoint to batch update all websites
    """
    try:
        logger.info("Fixing widgets for all websites...")

        # Get all websites
        websites = await supabase_service.supabase.table('websites')\
            .select('id, subdomain, html_content')\
            .execute()

        if not websites.data:
            return {
                "success": True,
                "message": "No websites found",
                "fixed": 0,
                "skipped": 0,
                "failed": 0
            }

        results = {
            "fixed": [],
            "skipped": [],
            "failed": []
        }

        for website in websites.data:
            website_id = website['id']
            subdomain = website.get('subdomain', 'unknown')

            try:
                # Call the fix endpoint for each website
                result = await fix_website_widget(website_id)

                if result['changed']:
                    results['fixed'].append(subdomain)
                else:
                    results['skipped'].append(subdomain)

            except Exception as e:
                logger.error(f"Failed to fix {subdomain}: {e}")
                results['failed'].append(subdomain)

        logger.info(f"✅ Batch fix complete: {len(results['fixed'])} fixed, {len(results['skipped'])} skipped, {len(results['failed'])} failed")

        return {
            "success": True,
            "message": "Batch fix completed",
            "fixed": len(results['fixed']),
            "skipped": len(results['skipped']),
            "failed": len(results['failed']),
            "details": results
        }

    except Exception as e:
        logger.error(f"Error in batch fix: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Batch fix failed: {str(e)}"
        )


@router.get("/{website_id}/health")
async def check_website_health(website_id: str):
    """
    Check if website has all required components including delivery widget
    This is a diagnostic endpoint to verify website health
    """
    try:
        logger.info(f"Health check for website: {website_id}")

        # Get website HTML
        website = await supabase_service.get_website(website_id)

        if not website:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Website not found"
            )

        html = website.get('html_content', '')

        # Check for required components
        checks = {
            'has_html_content': len(html) > 100,
            'has_delivery_button': 'binaapp.my/delivery' in html or 'delivery-widget.js' in html,
            'has_website_id_in_delivery': f'/delivery/{website_id}' in html or f'data-website-id="{website_id}"' in html,
            'has_body_tag': '</body>' in html,
            'has_head_tag': '</head>' in html,
        }

        all_passed = all(checks.values())

        return {
            "website_id": website_id,
            "subdomain": website.get('subdomain'),
            "healthy": all_passed,
            "checks": checks,
            "issues": [k for k, v in checks.items() if not v],
            "html_length": len(html)
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error checking website health: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Health check failed: {str(e)}"
        )


@router.post("/{website_id}/repair-delivery")
async def repair_website_delivery(website_id: str):
    """
    COMPREHENSIVE REPAIR: Add delivery button if COMPLETELY MISSING
    This fixes websites that never had the delivery widget injected
    """
    try:
        from app.services.business_types import detect_business_type, get_delivery_button_label

        logger.info(f"🔧 Repairing delivery widget for website: {website_id}")

        # Get website
        website = await supabase_service.get_website(website_id)

        if not website:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Website not found"
            )

        html_content = website.get('html_content', '')
        business_name = website.get('business_name', '')
        subdomain = website.get('subdomain', '')

        if not html_content:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Website has no HTML content"
            )

        # Check if delivery button already exists
        if 'binaapp.my/delivery' in html_content or 'delivery-widget.js' in html_content:
            # Check if it has the correct website_id
            if f'/delivery/{website_id}' in html_content:
                logger.info(f"✅ Website {subdomain} already has correct delivery button")
                return {
                    "success": True,
                    "message": "Website already has delivery button with correct ID",
                    "website_id": website_id,
                    "subdomain": subdomain,
                    "changed": False
                }

        logger.info(f"❌ Delivery button missing or has wrong ID - INJECTING...")

        # Detect business type and get appropriate button label
        business_type = detect_business_type(business_name)
        button_label = get_delivery_button_label(business_type, "ms")

        # Delivery button HTML
        delivery_button = f'''
<!-- BinaApp Delivery Button - CRITICAL: DO NOT REMOVE! -->
<a href="https://binaapp.my/delivery/{website_id}"
   target="_blank"
   id="binaapp-delivery-btn"
   style="position:fixed;bottom:24px;left:24px;background:linear-gradient(135deg,#f97316,#ea580c);color:white;padding:16px 24px;border-radius:50px;font-weight:600;z-index:9999;text-decoration:none;box-shadow:0 4px 20px rgba(234,88,12,0.4);font-family:sans-serif;display:flex;align-items:center;gap:8px;transition:transform 0.2s,box-shadow 0.2s;"
   onmouseover="this.style.transform='translateY(-2px)';this.style.boxShadow='0 6px 25px rgba(234,88,12,0.5)';"
   onmouseout="this.style.transform='translateY(0)';this.style.boxShadow='0 4px 20px rgba(234,88,12,0.4)';">
    🛵 {button_label}
</a>
'''

        # Inject before </body>
        if "</body>" in html_content:
            new_html = html_content.replace("</body>", delivery_button + "\n</body>")
        else:
            new_html = html_content + delivery_button

        # Update database
        await supabase_service.update_website(website_id, {
            "html_content": new_html,
            "updated_at": datetime.utcnow().isoformat()
        })

        logger.info(f"✅ Successfully repaired website: {subdomain}")

        return {
            "success": True,
            "message": f"Delivery button added successfully",
            "website_id": website_id,
            "subdomain": subdomain,
            "changed": True,
            "url": f"https://{subdomain}.binaapp.my"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error repairing website: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to repair website: {str(e)}"
        )


@router.post("/repair-all-delivery")
async def repair_all_websites_delivery():
    """
    BATCH REPAIR: Add delivery button to ALL websites that are missing it
    This is a one-time fix for all existing websites
    """
    try:
        from app.services.business_types import detect_business_type, get_delivery_button_label

        logger.info("🔧 Starting batch repair for ALL websites...")

        # Get all websites
        websites = await supabase_service.supabase.table('websites')\
            .select('id, subdomain, business_name, html_content')\
            .execute()

        if not websites.data:
            return {
                "success": True,
                "message": "No websites found",
                "fixed": 0,
                "skipped": 0,
                "failed": 0
            }

        results = {
            "fixed": [],
            "skipped": [],
            "failed": []
        }

        for website in websites.data:
            website_id = website['id']
            subdomain = website.get('subdomain', 'unknown')
            business_name = website.get('business_name', '')
            html_content = website.get('html_content', '')

            try:
                if not html_content:
                    results['failed'].append(f"{subdomain}: No HTML content")
                    continue

                # Check if delivery button already exists with correct ID
                if f'/delivery/{website_id}' in html_content:
                    results['skipped'].append(subdomain)
                    logger.info(f"✅ {subdomain}: Already has correct delivery button")
                    continue

                logger.info(f"❌ {subdomain}: Missing delivery button - FIXING...")

                # Detect business type and get button label
                business_type = detect_business_type(business_name)
                button_label = get_delivery_button_label(business_type, "ms")

                # Delivery button HTML
                delivery_button = f'''
<!-- BinaApp Delivery Button - CRITICAL: DO NOT REMOVE! -->
<a href="https://binaapp.my/delivery/{website_id}"
   target="_blank"
   id="binaapp-delivery-btn"
   style="position:fixed;bottom:24px;left:24px;background:linear-gradient(135deg,#f97316,#ea580c);color:white;padding:16px 24px;border-radius:50px;font-weight:600;z-index:9999;text-decoration:none;box-shadow:0 4px 20px rgba(234,88,12,0.4);font-family:sans-serif;display:flex;align-items:center;gap:8px;transition:transform 0.2s,box-shadow 0.2s;"
   onmouseover="this.style.transform='translateY(-2px)';this.style.boxShadow='0 6px 25px rgba(234,88,12,0.5)';"
   onmouseout="this.style.transform='translateY(0)';this.style.boxShadow='0 4px 20px rgba(234,88,12,0.4)';">
    🛵 {button_label}
</a>
'''

                # Inject before </body>
                if "</body>" in html_content:
                    new_html = html_content.replace("</body>", delivery_button + "\n</body>")
                else:
                    new_html = html_content + delivery_button

                # Update database
                await supabase_service.update_website(website_id, {
                    "html_content": new_html,
                    "updated_at": datetime.utcnow().isoformat()
                })

                results['fixed'].append(subdomain)
                logger.info(f"✅ {subdomain}: FIXED!")

            except Exception as e:
                logger.error(f"Failed to fix {subdomain}: {e}")
                results['failed'].append(f"{subdomain}: {str(e)}")

        logger.info(f"✅ Batch repair complete: {len(results['fixed'])} fixed, {len(results['skipped'])} skipped, {len(results['failed'])} failed")

        return {
            "success": True,
            "message": "Batch repair completed",
            "fixed": len(results['fixed']),
            "skipped": len(results['skipped']),
            "failed": len(results['failed']),
            "details": results
        }

    except Exception as e:
        logger.error(f"Error in batch repair: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Batch repair failed: {str(e)}"
        )


@router.get("/by-domain/{domain}")
async def get_website_by_domain(domain: str):
    """
    Get website by domain name (subdomain or custom domain)
    This endpoint is public to allow widget initialization
    """
    try:
        # Remove port if present
        domain = domain.split(':')[0].strip().lower()

        # Remove .binaapp.my suffix if present
        domain = domain.replace('.binaapp.my', '')

        logger.info(f"Looking up website by domain: {domain}")

        # Try subdomain first
        result = await supabase_service.supabase.table('websites')\
            .select('id, business_name, subdomain, custom_domain, status')\
            .eq('subdomain', domain)\
            .maybeSingle()\
            .execute()

        # If not found, try custom domain
        if not result.data:
            result = await supabase_service.supabase.table('websites')\
                .select('id, business_name, subdomain, custom_domain, status')\
                .eq('custom_domain', f"{domain}.binaapp.my")\
                .maybeSingle()\
                .execute()

        # Still not found, try with .binaapp.my appended
        if not result.data:
            result = await supabase_service.supabase.table('websites')\
                .select('id, business_name, subdomain, custom_domain, status')\
                .eq('subdomain', domain)\
                .or_(f'custom_domain.eq.{domain}')\
                .maybeSingle()\
                .execute()

        if not result.data:
            logger.warning(f"Website not found for domain: {domain}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Website not found for domain: {domain}"
            )

        logger.info(f"Found website: {result.data.get('id')} for domain: {domain}")
        return result.data

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error finding website by domain {domain}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to lookup website: {str(e)}"
        )


@router.post("/admin/sync-storage-db")
async def sync_storage_and_database():
    """
    Admin endpoint to sync websites between Storage and Database.

    This identifies orphaned websites (in Storage but not in DB) and creates
    missing database records. This fixes foreign key constraint errors when
    customers try to place orders on websites that exist in storage but
    not in the database.

    Returns:
        Summary of sync operation including orphaned websites found and fixed.
    """
    try:
        logger.info("🔄 Starting Storage-Database sync...")

        # Get Supabase client
        from app.core.supabase import get_supabase_client
        supabase = get_supabase_client()

        # Step 1: Get all websites from database
        db_result = supabase.table("websites").select("id, subdomain").execute()
        db_websites = {w["subdomain"]: w for w in (db_result.data or []) if w.get("subdomain")}
        logger.info(f"Found {len(db_websites)} websites in database")

        # Step 2: Get all folders from storage
        bucket_name = settings.STORAGE_BUCKET_NAME if hasattr(settings, 'STORAGE_BUCKET_NAME') else "websites"

        try:
            storage_list = supabase.storage.from_(bucket_name).list()
            storage_folders = [item["name"] for item in (storage_list or []) if item.get("name") and item.get("id")]
        except Exception as storage_err:
            logger.warning(f"Could not list storage: {storage_err}")
            storage_folders = []

        logger.info(f"Found {len(storage_folders)} folders in storage")

        # Step 3: Find orphaned websites
        orphaned = []
        for folder in storage_folders:
            # Skip if it looks like a UUID (user_id folder)
            if len(folder) == 36 and folder.count("-") == 4:
                continue
            if folder not in db_websites:
                orphaned.append(folder)

        logger.info(f"Found {len(orphaned)} orphaned websites")

        # Step 4: Create missing records
        fixed = []
        failed = []

        for subdomain in orphaned:
            try:
                # Try to get website_id from storage HTML
                website_id = None
                try:
                    public_url = supabase.storage.from_(bucket_name).get_public_url(f"{subdomain}/index.html")
                    import httpx
                    import re
                    async with httpx.AsyncClient() as client:
                        response = await client.get(public_url, timeout=10.0)
                        if response.status_code == 200:
                            html = response.text
                            # Look for data-website-id
                            match = re.search(r'data-website-id=["\']([a-f0-9-]{36})["\']', html, re.IGNORECASE)
                            if match:
                                website_id = match.group(1)
                except Exception as html_err:
                    logger.debug(f"Could not extract website_id from HTML: {html_err}")

                # Generate ID if not found
                if not website_id:
                    website_id = str(uuid.uuid4())

                # Create the record
                website_data = {
                    "id": website_id,
                    "subdomain": subdomain,
                    "business_name": subdomain.replace("-", " ").replace("_", " ").title(),
                    "status": "published",
                    "include_ecommerce": True,
                    "created_at": datetime.utcnow().isoformat(),
                    "updated_at": datetime.utcnow().isoformat()
                }

                supabase.table("websites").insert(website_data).execute()
                fixed.append({"subdomain": subdomain, "id": website_id})
                logger.info(f"✅ Created missing record: {subdomain} -> {website_id}")

            except Exception as create_err:
                failed.append({"subdomain": subdomain, "error": str(create_err)})
                logger.error(f"❌ Failed to create {subdomain}: {create_err}")

        result = {
            "success": True,
            "storage_count": len(storage_folders),
            "database_count": len(db_websites),
            "orphaned_count": len(orphaned),
            "fixed_count": len(fixed),
            "failed_count": len(failed),
            "fixed": fixed,
            "failed": failed
        }

        logger.info(f"✅ Sync complete: {len(fixed)} fixed, {len(failed)} failed")
        return result

    except Exception as e:
        logger.error(f"❌ Sync failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Sync failed: {str(e)}"
        )


@router.get("/admin/check-website/{website_id_or_subdomain}")
async def check_website_status(website_id_or_subdomain: str):
    """
    Check if a website exists in both database and storage.

    This diagnostic endpoint helps identify mismatches between
    storage and database records.

    Args:
        website_id_or_subdomain: Either a UUID or subdomain to check
    """
    try:
        import re
        from app.core.supabase import get_supabase_client
        supabase = get_supabase_client()

        uuid_pattern = re.compile(
            r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$',
            re.IGNORECASE
        )

        # Determine if input is UUID or subdomain
        is_uuid = uuid_pattern.match(website_id_or_subdomain)

        result = {
            "input": website_id_or_subdomain,
            "is_uuid": is_uuid is not None,
            "database_record": None,
            "storage_exists": False,
            "issues": []
        }

        # Check database
        if is_uuid:
            db_result = supabase.table("websites")\
                .select("id, subdomain, business_name, status, user_id")\
                .eq("id", website_id_or_subdomain)\
                .execute()
        else:
            db_result = supabase.table("websites")\
                .select("id, subdomain, business_name, status, user_id")\
                .eq("subdomain", website_id_or_subdomain)\
                .execute()

        if db_result.data:
            result["database_record"] = db_result.data[0]
            subdomain = db_result.data[0].get("subdomain")
        else:
            result["issues"].append("NOT_IN_DATABASE")
            subdomain = website_id_or_subdomain if not is_uuid else None

        # Check storage (if we have a subdomain)
        if subdomain:
            bucket_name = settings.STORAGE_BUCKET_NAME if hasattr(settings, 'STORAGE_BUCKET_NAME') else "websites"
            try:
                storage_list = supabase.storage.from_(bucket_name).list(subdomain)
                if storage_list and len(storage_list) > 0:
                    result["storage_exists"] = True
                    result["storage_files"] = [f["name"] for f in storage_list[:10]]
            except Exception as storage_err:
                logger.debug(f"Storage check error: {storage_err}")

        # Analyze issues
        if result["database_record"] and not result["storage_exists"]:
            result["issues"].append("IN_DATABASE_BUT_NOT_STORAGE")
        elif result["storage_exists"] and not result["database_record"]:
            result["issues"].append("IN_STORAGE_BUT_NOT_DATABASE")

        result["healthy"] = len(result["issues"]) == 0

        return result

    except Exception as e:
        logger.error(f"Check website error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Check failed: {str(e)}"
        )


@router.delete("/{website_id}")
async def delete_website(
    website_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Delete a website and all related data
    """
    try:
        logger.info(f"Delete request for website: {website_id}")

        website = await supabase_service.get_website(website_id)

        if not website:
            logger.warning(f"Website not found: {website_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Website not found"
            )

        # Check ownership
        if website["user_id"] != current_user.get("sub"):
            logger.warning(f"Unauthorized delete attempt by {current_user.get('sub')} for website {website_id}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to delete this website"
            )

        # Delete from storage if published
        if website["status"] == WebsiteStatus.PUBLISHED:
            logger.info(f"Deleting published website from storage: {website['subdomain']}")
            try:
                await storage_service.delete_website(
                    user_id=current_user.get("sub"),
                    subdomain=website["subdomain"]
                )
                logger.info(f"✅ Storage deleted for: {website['subdomain']}")
            except Exception as storage_error:
                logger.error(f"Storage delete error (continuing anyway): {storage_error}")

        # Delete from database (CASCADE will handle related tables)
        logger.info(f"Deleting website from database: {website_id}")
        delete_result = await supabase_service.delete_website(website_id)

        if not delete_result.get("success"):
            logger.error(f"Database delete failed: {delete_result.get('message')}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=delete_result.get("message", "Failed to delete website from database")
            )

        logger.info(f"✅ Website deleted successfully: {website_id} ({website.get('subdomain')})")

        return {
            "success": True,
            "message": "Website deleted successfully",
            "website_id": website_id,
            "subdomain": website.get("subdomain")
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error deleting website {website_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete website: {str(e)}"
        )
