"""
Simple Projects Endpoint
Manage user projects (list, get, update, delete)
"""

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field
from typing import List, Optional
from loguru import logger
from datetime import datetime

from app.services.storage_service import storage_service
from app.services.supabase_client import supabase_service

router = APIRouter()


class ProjectResponse(BaseModel):
    """Project response"""
    id: str
    name: str
    subdomain: str
    url: str
    created_at: str
    published_at: Optional[str] = None


class ProjectDetailResponse(BaseModel):
    """Detailed project response with HTML code"""
    id: str
    name: str
    subdomain: str
    url: str
    html_code: str
    created_at: str
    published_at: Optional[str] = None


class UpdateProjectRequest(BaseModel):
    """Update project request"""
    name: Optional[str] = Field(None, min_length=2, max_length=100)
    html_code: Optional[str] = None


class DeleteResponse(BaseModel):
    """Delete response"""
    success: bool = True
    message: str = "Project deleted successfully"


@router.get("/{user_id}", response_model=List[ProjectResponse])
async def list_projects(user_id: str):
    """
    List all projects for a user

    Returns list of projects with basic information
    """
    try:
        logger.info(f"Listing projects for user: {user_id}")

        # Get projects from database
        websites = await supabase_service.get_user_websites(user_id)

        # Convert to response format
        projects = []
        for website in websites:
            projects.append(ProjectResponse(
                id=website["id"],
                name=website.get("business_name", "Untitled Project"),
                subdomain=website["subdomain"],
                url=website.get("public_url", ""),
                created_at=website.get("created_at", datetime.utcnow().isoformat()),
                published_at=website.get("published_at")
            ))

        logger.info(f"Found {len(projects)} projects for user {user_id}")
        return projects

    except Exception as e:
        logger.error(f"Error listing projects: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list projects: {str(e)}"
        )


@router.get("/{user_id}/{project_id}", response_model=ProjectDetailResponse)
async def get_project(user_id: str, project_id: str):
    """
    Get specific project details including HTML code

    Returns full project information with HTML content
    """
    try:
        logger.info(f"Getting project: {project_id} for user: {user_id}")

        # Get project from database
        website = await supabase_service.get_website(project_id)

        if not website:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Project not found"
            )

        # Verify ownership
        if website["user_id"] != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to access this project"
            )

        # Get HTML content from storage if not in database
        html_content = website.get("html_content", "")
        if not html_content:
            logger.info("HTML not in database, fetching from storage...")
            html_content = await storage_service.get_website_content(
                user_id=user_id,
                subdomain=website["subdomain"]
            ) or ""

        return ProjectDetailResponse(
            id=website["id"],
            name=website.get("business_name", "Untitled Project"),
            subdomain=website["subdomain"],
            url=website.get("public_url", ""),
            html_code=html_content,
            created_at=website.get("created_at", datetime.utcnow().isoformat()),
            published_at=website.get("published_at")
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting project: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get project: {str(e)}"
        )


@router.put("/{user_id}/{project_id}")
async def update_project(
    user_id: str,
    project_id: str,
    request: UpdateProjectRequest
):
    """
    Update project (name, html_code)

    If HTML code is updated, it will be re-uploaded to Supabase Storage
    """
    try:
        logger.info(f"Updating project: {project_id} for user: {user_id}")

        # Get project from database
        website = await supabase_service.get_website(project_id)

        if not website:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Project not found"
            )

        # Verify ownership
        if website["user_id"] != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to update this project"
            )

        # Prepare update data
        update_data = {
            "updated_at": datetime.utcnow().isoformat()
        }

        if request.name:
            update_data["business_name"] = request.name

        if request.html_code:
            update_data["html_content"] = request.html_code

            # Re-upload to storage
            try:
                public_url = await storage_service.upload_website(
                    user_id=user_id,
                    subdomain=website["subdomain"],
                    html_content=request.html_code
                )
                update_data["public_url"] = public_url
                logger.info(f"Website re-uploaded to storage: {public_url}")
            except Exception as e:
                logger.error(f"Failed to re-upload website: {e}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Failed to update website files: {str(e)}"
                )

        # Update database
        await supabase_service.update_website(project_id, update_data)

        logger.info(f"Project updated successfully: {project_id}")

        return {
            "success": True,
            "url": update_data.get("public_url", website.get("public_url")),
            "message": "Project updated successfully"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating project: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update project: {str(e)}"
        )


@router.delete("/{user_id}/{project_id}", response_model=DeleteResponse)
async def delete_project(user_id: str, project_id: str):
    """
    Delete project from database and Supabase Storage

    Removes both the database record and the HTML files
    """
    try:
        logger.info(f"Deleting project: {project_id} for user: {user_id}")

        # Get project from database
        website = await supabase_service.get_website(project_id)

        if not website:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Project not found"
            )

        # Verify ownership
        if website["user_id"] != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to delete this project"
            )

        # Delete from storage
        try:
            await storage_service.delete_website(
                user_id=user_id,
                subdomain=website["subdomain"]
            )
            logger.info(f"Deleted website files from storage: {website['subdomain']}")
        except Exception as e:
            logger.error(f"Failed to delete from storage: {e}")
            # Continue even if storage deletion fails

        # Delete from database
        success = await supabase_service.delete_website(project_id)

        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to delete project from database"
            )

        logger.info(f"Project deleted successfully: {project_id}")

        return DeleteResponse(
            success=True,
            message="Project deleted successfully"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting project: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete project: {str(e)}"
        )
