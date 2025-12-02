"""
Supabase Client Service
Handles all interactions with Supabase
"""

from supabase import create_client, Client
from typing import Dict, List, Optional, Any
from loguru import logger

from app.core.config import settings


class SupabaseService:
    """Service for Supabase operations"""

    def __init__(self):
        self.client: Client = create_client(
            settings.SUPABASE_URL,
            settings.SUPABASE_SERVICE_ROLE_KEY
        )
        logger.info("Supabase client initialized")

    # User operations
    async def create_user(self, email: str, password: str, full_name: Optional[str] = None) -> Dict:
        """Create a new user"""
        try:
            response = self.client.auth.sign_up({
                "email": email,
                "password": password,
                "options": {
                    "data": {
                        "full_name": full_name
                    }
                }
            })
            return response
        except Exception as e:
            logger.error(f"Error creating user: {e}")
            raise

    async def sign_in(self, email: str, password: str) -> Dict:
        """Sign in user"""
        try:
            response = self.client.auth.sign_in_with_password({
                "email": email,
                "password": password
            })
            return response
        except Exception as e:
            logger.error(f"Error signing in: {e}")
            raise

    async def get_user(self, user_id: str) -> Optional[Dict]:
        """Get user by ID"""
        try:
            response = self.client.auth.admin.get_user_by_id(user_id)
            return response
        except Exception as e:
            logger.error(f"Error getting user: {e}")
            return None

    # Website operations
    async def create_website(self, website_data: Dict) -> Dict:
        """Create a new website record"""
        try:
            response = self.client.table("websites").insert(website_data).execute()
            return response.data[0] if response.data else None
        except Exception as e:
            logger.error(f"Error creating website: {e}")
            raise

    async def get_website(self, website_id: str) -> Optional[Dict]:
        """Get website by ID"""
        try:
            response = self.client.table("websites").select("*").eq("id", website_id).execute()
            return response.data[0] if response.data else None
        except Exception as e:
            logger.error(f"Error getting website: {e}")
            return None

    async def get_user_websites(self, user_id: str) -> List[Dict]:
        """Get all websites for a user"""
        try:
            response = self.client.table("websites").select("*").eq("user_id", user_id).order("created_at", desc=True).execute()
            return response.data
        except Exception as e:
            logger.error(f"Error getting user websites: {e}")
            return []

    async def update_website(self, website_id: str, update_data: Dict) -> Optional[Dict]:
        """Update website"""
        try:
            response = self.client.table("websites").update(update_data).eq("id", website_id).execute()
            return response.data[0] if response.data else None
        except Exception as e:
            logger.error(f"Error updating website: {e}")
            raise

    async def delete_website(self, website_id: str) -> bool:
        """Delete website"""
        try:
            self.client.table("websites").delete().eq("id", website_id).execute()
            return True
        except Exception as e:
            logger.error(f"Error deleting website: {e}")
            return False

    async def check_subdomain_available(self, subdomain: str) -> bool:
        """Check if subdomain is available"""
        try:
            response = self.client.table("websites").select("id").eq("subdomain", subdomain).execute()
            return len(response.data) == 0
        except Exception as e:
            logger.error(f"Error checking subdomain: {e}")
            return False

    # Subscription operations
    async def get_user_subscription(self, user_id: str) -> Optional[Dict]:
        """Get user subscription"""
        try:
            response = self.client.table("subscriptions").select("*").eq("user_id", user_id).execute()
            return response.data[0] if response.data else None
        except Exception as e:
            logger.error(f"Error getting subscription: {e}")
            return None

    async def update_subscription(self, user_id: str, subscription_data: Dict) -> Optional[Dict]:
        """Update or create user subscription"""
        try:
            response = self.client.table("subscriptions").upsert({
                "user_id": user_id,
                **subscription_data
            }).execute()
            return response.data[0] if response.data else None
        except Exception as e:
            logger.error(f"Error updating subscription: {e}")
            raise

    # Analytics operations
    async def record_view(self, website_id: str) -> None:
        """Record a website view"""
        try:
            self.client.rpc("increment_views", {"website_id": website_id}).execute()
        except Exception as e:
            logger.error(f"Error recording view: {e}")

    async def get_analytics(self, website_id: str) -> Optional[Dict]:
        """Get website analytics"""
        try:
            response = self.client.table("analytics").select("*").eq("website_id", website_id).execute()
            return response.data[0] if response.data else None
        except Exception as e:
            logger.error(f"Error getting analytics: {e}")
            return None


# Create singleton instance
supabase_service = SupabaseService()
