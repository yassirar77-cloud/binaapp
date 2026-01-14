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
from app.services.ai_service import ai_service
from app.services.storage_service import storage_service
from app.services.templates import TemplateService
from app.core.security import get_current_user
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
    try:
        # Generate HTML using AI
        ai_response = await ai_service.generate_website(request)

        html_content = ai_response.html_content
        integrations = ai_response.integrations_included

        # CRITICAL: Inject delivery widget if ecommerce/delivery is enabled
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
            logger.info(f"✅ Delivery widget injected successfully for website {website_id}")

        # ALWAYS inject chat widget for customer-owner communication
        # This allows customers to ask questions before ordering
        template_service = TemplateService()
        html_content = template_service.inject_chat_widget(
            html=html_content,
            website_id=website_id,
            api_url="https://binaapp-backend.onrender.com"
        )
        logger.info(f"✅ Chat widget injected for website {website_id}")

        # Update website with generated content
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

        logger.info(f"Website content generated successfully: {website_id}")

    except Exception as e:
        logger.error(f"Error in background generation: {e}")

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

        return [
            WebsiteListResponse(
                id=w["id"],
                business_name=w["business_name"],
                subdomain=w["subdomain"],
                full_url=f"https://{w['subdomain']}{settings.SUBDOMAIN_SUFFIX}",
                status=w["status"],
                created_at=datetime.fromisoformat(w["created_at"]),
                published_at=datetime.fromisoformat(w["published_at"]) if w.get("published_at") else None
            )
            for w in websites
        ]

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
        public_url = await storage_service.publish_website(
            subdomain=website["subdomain"],
            html_content=website["html_content"],
            website_id=website_id,
            user_id=current_user.get("sub")
        )

        # Update website status
        published_at = datetime.utcnow()
        await supabase_service.update_website(website_id, {
            "status": WebsiteStatus.PUBLISHED,
            "published_at": published_at.isoformat(),
            "public_url": public_url,
            "updated_at": published_at.isoformat()
        })

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
async def fix_website_widget(website_id: str):
    """
    Fix existing website HTML to add data-website-id to delivery widget script tag
    This is a maintenance endpoint to update websites created before the fix
    """
    try:
        import re

        logger.info(f"Fixing widget for website: {website_id}")

        # Get website
        website = await supabase_service.get_website(website_id)

        if not website:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Website not found"
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
