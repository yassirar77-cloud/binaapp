"""
Supabase Client Service
Handles all Supabase interactions using REST API
"""
import httpx
from typing import Optional, Dict, Any
from app.core.config import settings

class SupabaseService:
    """Supabase service using REST API (no SDK conflicts)"""
    
    def __init__(self):
        self.url = settings.SUPABASE_URL
        self.anon_key = settings.SUPABASE_ANON_KEY
        self.service_key = settings.SUPABASE_SERVICE_ROLE_KEY
        self.headers = {
            "apikey": self.service_key,
            "Authorization": f"Bearer {self.service_key}",
            "Content-Type": "application/json"
        }
    
    async def upload_file(self, bucket: str, path: str, file_data: bytes, content_type: str = "application/octet-stream") -> Optional[str]:
        """Upload file to Supabase Storage with proper Content-Type"""
        try:
            url = f"{self.url}/storage/v1/object/{bucket}/{path}"

            # Use proper headers for Supabase Storage
            # x-upsert: true allows creating or updating files
            upload_headers = {
                "apikey": self.service_key,
                "Authorization": f"Bearer {self.service_key}",
                "Content-Type": content_type,
                "x-upsert": "true",
                "Cache-Control": "public, max-age=3600"
            }

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    url,
                    headers=upload_headers,
                    content=file_data,
                    timeout=30.0
                )

            if response.status_code in [200, 201]:
                # Return public URL
                return f"{self.url}/storage/v1/object/public/{bucket}/{path}"
            else:
                print(f"❌ Upload failed: {response.status_code} - {response.text}")
                return None

        except Exception as e:
            print(f"❌ Upload error: {str(e)}")
            return None
    
    async def get_file_url(self, bucket: str, path: str) -> str:
        """Get public URL for a file"""
        return f"{self.url}/storage/v1/object/public/{bucket}/{path}"
    
    async def delete_file(self, bucket: str, path: str) -> bool:
        """Delete file from storage"""
        try:
            url = f"{self.url}/storage/v1/object/{bucket}/{path}"
            
            async with httpx.AsyncClient() as client:
                response = await client.delete(url, headers=self.headers)
            
            return response.status_code in [200, 204]
        except Exception as e:
            print(f"❌ Delete error: {str(e)}")
            return False
    
    async def create_user(self, email: str, password: str) -> Optional[Dict[str, Any]]:
        """Create a new user"""
        try:
            url = f"{self.url}/auth/v1/signup"
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    url,
                    headers=self.headers,
                    json={"email": email, "password": password}
                )
            
            if response.status_code == 200:
                return response.json()
            return None
        except Exception as e:
            print(f"❌ Create user error: {str(e)}")
            return None
    
    async def sign_in(self, email: str, password: str) -> Optional[Dict[str, Any]]:
        """Sign in a user"""
        try:
            url = f"{self.url}/auth/v1/token?grant_type=password"
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    url,
                    headers=self.headers,
                    json={"email": email, "password": password}
                )
            
            if response.status_code == 200:
                return response.json()
            return None
        except Exception as e:
            print(f"❌ Sign in error: {str(e)}")
            return None
    
    async def insert_record(self, table: str, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Insert a record into a table"""
        try:
            url = f"{self.url}/rest/v1/{table}"
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    url,
                    headers={**self.headers, "Prefer": "return=representation"},
                    json=data
                )
            
            if response.status_code in [200, 201]:
                return response.json()
            return None
        except Exception as e:
            print(f"❌ Insert error: {str(e)}")
            return None
    
    async def select_records(self, table: str, filters: Optional[Dict[str, Any]] = None) -> Optional[list]:
        """Select records from a table"""
        try:
            url = f"{self.url}/rest/v1/{table}"
            params = {}
            
            if filters:
                for key, value in filters.items():
                    params[key] = f"eq.{value}"
            
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    url,
                    headers=self.headers,
                    params=params
                )
            
            if response.status_code == 200:
                return response.json()
            return None
        except Exception as e:
            print(f"❌ Select error: {str(e)}")
            return None
    
    async def get_user_websites(self, user_id: str) -> Optional[list]:
        """Get all websites for a user"""
        try:
            return await self.select_records("websites", {"user_id": user_id})
        except Exception as e:
            print(f"❌ Get user websites error: {str(e)}")
            return []

    async def create_website(self, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Create a new website record"""
        try:
            return await self.insert_record("websites", data)
        except Exception as e:
            print(f"❌ Create website error: {str(e)}")
            return None

    async def get_website(self, website_id: str) -> Optional[Dict[str, Any]]:
        """Get a website by ID"""
        try:
            url = f"{self.url}/rest/v1/websites"
            params = {"id": f"eq.{website_id}"}

            async with httpx.AsyncClient() as client:
                response = await client.get(
                    url,
                    headers=self.headers,
                    params=params
                )

            if response.status_code == 200:
                records = response.json()
                return records[0] if records else None
            return None
        except Exception as e:
            print(f"❌ Get website error: {str(e)}")
            return None

    async def update_website(self, website_id: str, data: Dict[str, Any]) -> bool:
        """Update a website record"""
        try:
            url = f"{self.url}/rest/v1/websites"
            params = {"id": f"eq.{website_id}"}

            async with httpx.AsyncClient() as client:
                response = await client.patch(
                    url,
                    headers={**self.headers, "Prefer": "return=minimal"},
                    params=params,
                    json=data
                )

            return response.status_code in [200, 204]
        except Exception as e:
            print(f"❌ Update website error: {str(e)}")
            return False

    async def delete_website(self, website_id: str) -> bool:
        """Delete a website record"""
        try:
            url = f"{self.url}/rest/v1/websites"
            params = {"id": f"eq.{website_id}"}

            async with httpx.AsyncClient() as client:
                response = await client.delete(
                    url,
                    headers=self.headers,
                    params=params
                )

            return response.status_code in [200, 204]
        except Exception as e:
            print(f"❌ Delete website error: {str(e)}")
            return False


# Create singleton instance
supabase_service = SupabaseService()