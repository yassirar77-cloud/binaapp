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

        # SECURITY: Use service role key for admin operations (bypasses RLS)
        # This should ONLY be used for:
        # - Customer-facing operations (widgets, order creation)
        # - Admin operations
        # - Migrations
        self.service_headers = {
            "apikey": self.service_key,
            "Authorization": f"Bearer {self.service_key}",
            "Content-Type": "application/json"
        }

        # For backwards compatibility, default headers use service key
        # TODO: Gradually migrate to use get_user_headers() for business operations
        self.headers = self.service_headers

    def get_user_headers(self, user_token: str) -> Dict[str, str]:
        """
        Get headers for authenticated user operations (respects RLS).

        Use this for business owner operations where RLS should be enforced.

        Args:
            user_token: JWT token from authenticated user

        Returns:
            Headers with anon key and user's JWT token
        """
        return {
            "apikey": self.anon_key,  # Use anon key, not service key
            "Authorization": f"Bearer {user_token}",  # User's JWT
            "Content-Type": "application/json"
        }
    
    async def upload_file(self, bucket: str, path: str, file_data: bytes, content_type: str = "application/octet-stream") -> Optional[str]:
        """
        Upload file to Supabase Storage with proper Content-Type for HTML rendering.

        SECURITY NOTE: Uses service role key because storage operations need admin access.
        """
        try:
            url = f"{self.url}/storage/v1/object/{bucket}/{path}"

            # Critical headers for Supabase Storage to serve HTML correctly
            # Content-Type MUST be set to text/html for browsers to render (not download)
            # SECURITY: Explicitly use service_key for storage operations
            upload_headers = {
                "apikey": self.service_key,
                "Authorization": f"Bearer {self.service_key}",
                "Content-Type": content_type,
                "x-upsert": "true",
                "Cache-Control": "public, max-age=3600",
                # Additional headers to ensure proper MIME type storage
                "content-type": content_type,  # lowercase variant for compatibility
            }

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    url,
                    headers=upload_headers,
                    content=file_data,
                    timeout=30.0
                )

            if response.status_code in [200, 201]:
                # Return public URL with .html extension for proper serving
                public_url = f"{self.url}/storage/v1/object/public/{bucket}/{path}"
                print(f"✅ File uploaded with Content-Type: {content_type}")
                return public_url
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
    
    async def create_user(self, email: str, password: str, full_name: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Create a new user using Supabase Admin API.

        CRITICAL: Uses /auth/v1/admin/users endpoint with SERVICE_ROLE_KEY
        This bypasses RLS and is required for user creation.
        """
        try:
            # CRITICAL: Use admin endpoint, NOT /auth/v1/signup
            # /auth/v1/signup fails with "Database error saving new user" due to RLS
            url = f"{self.url}/auth/v1/admin/users"

            payload = {
                "email": email,
                "password": password,
                "email_confirm": True,  # Auto-confirm email for now
                "user_metadata": {}
            }

            # Add user metadata if full_name is provided
            if full_name:
                payload["user_metadata"]["full_name"] = full_name

            # MUST use service_headers with SERVICE_ROLE_KEY for admin operations
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    url,
                    headers=self.service_headers,
                    json=payload
                )

            if response.status_code in [200, 201]:
                data = response.json()
                user_id = data.get("id")
                print(f"✅ Created auth user: {user_id}")
                # Wrap response to provide consistent interface
                return {"user": data, "raw": data}
            else:
                error_text = response.text
                print(f"❌ Create user failed: {response.status_code} - {error_text}")
                return None
        except Exception as e:
            print(f"❌ Create user error: {str(e)}")
            return None

    async def create_user_profile(self, user_id: str, email: str, full_name: Optional[str] = None, role: str = "customer") -> Optional[Dict[str, Any]]:
        """
        Create a user profile in the public.profiles table.

        This is called after creating the auth user to ensure the profile exists.
        Uses SERVICE ROLE headers to bypass RLS.

        NOTE: The table is 'profiles' not 'users' per DATABASE_SCHEMA.sql
        """
        try:
            url = f"{self.url}/rest/v1/profiles"

            # Profile data matching the 'profiles' table schema
            # Columns: id, full_name, business_name, avatar_url, phone, created_at, updated_at
            profile_data = {
                "id": user_id,
                "full_name": full_name
            }

            # MUST use service_headers to bypass RLS
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    url,
                    headers={**self.service_headers, "Prefer": "return=representation"},
                    json=profile_data
                )

            if response.status_code in [200, 201]:
                result = response.json()
                print(f"✅ Created user profile: {user_id}")
                return result[0] if isinstance(result, list) else result
            else:
                error_text = response.text
                print(f"❌ Failed to create user profile: {response.status_code} - {error_text}")
                return None
        except Exception as e:
            print(f"❌ Create user profile error: {str(e)}")
            return None

    async def delete_auth_user(self, user_id: str) -> bool:
        """
        Delete a user from Supabase Auth (rollback operation).

        Used when profile creation fails after auth user was created.
        """
        try:
            url = f"{self.url}/auth/v1/admin/users/{user_id}"

            async with httpx.AsyncClient() as client:
                response = await client.delete(
                    url,
                    headers=self.service_headers
                )

            if response.status_code in [200, 204]:
                print(f"✅ Deleted auth user (rollback): {user_id}")
                return True
            else:
                print(f"❌ Failed to delete auth user: {response.status_code} - {response.text}")
                return False
        except Exception as e:
            print(f"❌ Delete auth user error: {str(e)}")
            return False
    
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
                data = response.json()
                # Supabase returns: { user: {...}, access_token: ..., ... }
                # Wrap to provide consistent interface
                return {"user": data.get("user"), "session": data, "raw": data}
            else:
                error_text = response.text
                print(f"❌ Sign in failed: {response.status_code} - {error_text}")
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

    async def delete_from_table(self, table: str, column: str, value: str) -> Dict[str, Any]:
        """Delete records from a table by column value"""
        try:
            url = f"{self.url}/rest/v1/{table}"
            params = {column: f"eq.{value}"}

            async with httpx.AsyncClient() as client:
                response = await client.delete(
                    url,
                    headers=self.headers,
                    params=params
                )

            if response.status_code in [200, 204]:
                print(f"✅ Deleted from {table} where {column}={value}")
                return {"success": True, "deleted": table}
            else:
                print(f"⚠️ Delete from {table} returned {response.status_code}: {response.text}")
                # Don't fail - some tables may not have matching records
                return {"success": True, "deleted": table, "note": "No matching records"}
        except Exception as e:
            print(f"❌ Delete from {table} error: {str(e)}")
            return {"success": False, "table": table, "error": str(e)}

    async def get_rider_ids_for_website(self, website_id: str) -> list:
        """Get all rider IDs for a website"""
        try:
            url = f"{self.url}/rest/v1/riders"
            params = {"website_id": f"eq.{website_id}", "select": "id"}

            async with httpx.AsyncClient() as client:
                response = await client.get(
                    url,
                    headers=self.headers,
                    params=params
                )

            if response.status_code == 200:
                riders = response.json()
                return [r['id'] for r in riders]
            return []
        except Exception as e:
            print(f"❌ Get rider IDs error: {str(e)}")
            return []

    async def get_conversation_ids_for_website(self, website_id: str) -> list:
        """Get all conversation IDs for a website"""
        try:
            url = f"{self.url}/rest/v1/chat_conversations"
            params = {"website_id": f"eq.{website_id}", "select": "id"}

            async with httpx.AsyncClient() as client:
                response = await client.get(
                    url,
                    headers=self.headers,
                    params=params
                )

            if response.status_code == 200:
                conversations = response.json()
                return [c['id'] for c in conversations]
            return []
        except Exception as e:
            print(f"❌ Get conversation IDs error: {str(e)}")
            return []

    async def delete_by_ids(self, table: str, column: str, ids: list) -> Dict[str, Any]:
        """Delete records by a list of IDs"""
        if not ids:
            return {"success": True, "deleted": 0}

        try:
            url = f"{self.url}/rest/v1/{table}"
            # Use the 'in' operator for multiple IDs
            ids_str = ",".join([f'"{id}"' for id in ids])
            params = {column: f"in.({ids_str})"}

            async with httpx.AsyncClient() as client:
                response = await client.delete(
                    url,
                    headers=self.headers,
                    params=params
                )

            if response.status_code in [200, 204]:
                print(f"✅ Deleted {len(ids)} records from {table}")
                return {"success": True, "deleted": len(ids)}
            else:
                print(f"⚠️ Delete by IDs from {table} returned {response.status_code}")
                return {"success": True, "deleted": 0}
        except Exception as e:
            print(f"❌ Delete by IDs from {table} error: {str(e)}")
            return {"success": False, "error": str(e)}

    async def delete_website_cascade(self, website_id: str) -> Dict[str, Any]:
        """
        Delete a website and ALL related data in the correct order
        IMPORTANT: Delete children before parent to avoid foreign key errors
        """
        try:
            deleted_tables = []

            print(f"[Delete Cascade] Starting deletion for website: {website_id}")

            # STEP 1: Get IDs we need for nested deletions
            rider_ids = await self.get_rider_ids_for_website(website_id)
            conversation_ids = await self.get_conversation_ids_for_website(website_id)

            print(f"[Delete Cascade] Found {len(rider_ids)} riders, {len(conversation_ids)} conversations")

            # STEP 2: Delete chat messages (child of chat_conversations)
            if conversation_ids:
                result = await self.delete_by_ids("chat_messages", "conversation_id", conversation_ids)
                deleted_tables.append(f"chat_messages ({result.get('deleted', 0)} records)")
            print(f"[Delete Cascade] Deleted chat messages")

            # STEP 3: Delete chat conversations
            await self.delete_from_table("chat_conversations", "website_id", website_id)
            deleted_tables.append("chat_conversations")
            print(f"[Delete Cascade] Deleted chat conversations")

            # STEP 4: Delete rider locations (child of riders)
            if rider_ids:
                result = await self.delete_by_ids("rider_locations", "rider_id", rider_ids)
                deleted_tables.append(f"rider_locations ({result.get('deleted', 0)} records)")
            print(f"[Delete Cascade] Deleted rider locations")

            # STEP 5: Delete order items (child of delivery_orders)
            # First get order IDs
            order_ids = await self.get_order_ids_for_website(website_id)
            if order_ids:
                result = await self.delete_by_ids("order_items", "order_id", order_ids)
                deleted_tables.append(f"order_items ({result.get('deleted', 0)} records)")
            print(f"[Delete Cascade] Deleted order items")

            # STEP 6: Delete delivery orders
            await self.delete_from_table("delivery_orders", "website_id", website_id)
            deleted_tables.append("delivery_orders")
            print(f"[Delete Cascade] Deleted delivery orders")

            # STEP 7: Delete menu items
            await self.delete_from_table("menu_items", "website_id", website_id)
            deleted_tables.append("menu_items")
            print(f"[Delete Cascade] Deleted menu items")

            # STEP 8: Delete menu categories
            await self.delete_from_table("menu_categories", "website_id", website_id)
            deleted_tables.append("menu_categories")
            print(f"[Delete Cascade] Deleted menu categories")

            # STEP 9: Delete delivery zones
            await self.delete_from_table("delivery_zones", "website_id", website_id)
            deleted_tables.append("delivery_zones")
            print(f"[Delete Cascade] Deleted delivery zones")

            # STEP 10: Delete delivery settings
            await self.delete_from_table("delivery_settings", "website_id", website_id)
            deleted_tables.append("delivery_settings")
            print(f"[Delete Cascade] Deleted delivery settings")

            # STEP 11: Delete riders
            await self.delete_from_table("riders", "website_id", website_id)
            deleted_tables.append("riders")
            print(f"[Delete Cascade] Deleted riders")

            # STEP 12: Delete generation jobs
            await self.delete_from_table("generation_jobs", "website_id", website_id)
            deleted_tables.append("generation_jobs")
            print(f"[Delete Cascade] Deleted generation jobs")

            # STEP 13: FINALLY delete the website itself
            url = f"{self.url}/rest/v1/websites"
            params = {"id": f"eq.{website_id}"}

            async with httpx.AsyncClient() as client:
                response = await client.delete(
                    url,
                    headers=self.headers,
                    params=params
                )

            if response.status_code in [200, 204]:
                print(f"✅ [Delete Cascade] Website deleted successfully: {website_id}")
                return {
                    "success": True,
                    "message": "Website and all related data deleted successfully",
                    "deleted_tables": deleted_tables
                }
            else:
                error_detail = response.text
                print(f"❌ [Delete Cascade] Website delete failed: {response.status_code} - {error_detail}")
                return {
                    "success": False,
                    "message": f"Failed to delete website: {error_detail}",
                    "status_code": response.status_code,
                    "deleted_tables": deleted_tables
                }

        except Exception as e:
            print(f"❌ [Delete Cascade] Exception: {str(e)}")
            import traceback
            traceback.print_exc()
            return {"success": False, "message": f"Exception: {str(e)}"}

    async def get_order_ids_for_website(self, website_id: str) -> list:
        """Get all order IDs for a website"""
        try:
            url = f"{self.url}/rest/v1/delivery_orders"
            params = {"website_id": f"eq.{website_id}", "select": "id"}

            async with httpx.AsyncClient() as client:
                response = await client.get(
                    url,
                    headers=self.headers,
                    params=params
                )

            if response.status_code == 200:
                orders = response.json()
                return [o['id'] for o in orders]
            return []
        except Exception as e:
            print(f"❌ Get order IDs error: {str(e)}")
            return []

    async def delete_website(self, website_id: str) -> Dict[str, Any]:
        """Delete a website record and all related data (CASCADE)"""
        # Use the new cascade delete method
        return await self.delete_website_cascade(website_id)

    async def get_user_subscription(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user's subscription details"""
        try:
            url = f"{self.url}/rest/v1/subscriptions"
            params = {"user_id": f"eq.{user_id}"}

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
            print(f"❌ Get subscription error: {str(e)}")
            return None

    async def update_user_subscription(self, user_id: str, data: Dict[str, Any]) -> bool:
        """Update user's subscription. Uses service_headers to bypass RLS."""
        try:
            # First check if subscription exists
            existing = await self.get_user_subscription(user_id)

            url = f"{self.url}/rest/v1/subscriptions"

            if existing:
                # Update existing subscription
                params = {"user_id": f"eq.{user_id}"}

                async with httpx.AsyncClient() as client:
                    response = await client.patch(
                        url,
                        headers={**self.service_headers, "Prefer": "return=minimal"},
                        params=params,
                        json=data
                    )

                success = response.status_code in [200, 204]
                if success:
                    print(f"✅ Updated subscription for user: {user_id}")
                else:
                    print(f"❌ Failed to update subscription: {response.status_code} - {response.text}")
                return success
            else:
                # Create new subscription using service_headers to bypass RLS
                data["user_id"] = user_id
                async with httpx.AsyncClient() as client:
                    response = await client.post(
                        url,
                        headers={**self.service_headers, "Prefer": "return=representation"},
                        json=data
                    )

                success = response.status_code in [200, 201]
                if success:
                    print(f"✅ Created subscription for user: {user_id}")
                else:
                    print(f"❌ Failed to create subscription: {response.status_code} - {response.text}")
                return success

        except Exception as e:
            print(f"❌ Update subscription error: {str(e)}")
            return False

    async def update_subscription(self, user_id: str, data: Dict[str, Any]) -> bool:
        """Alias for update_user_subscription"""
        return await self.update_user_subscription(user_id, data)

    async def update_payment_status(self, payment_id: str, status: str) -> bool:
        """Update payment status"""
        try:
            url = f"{self.url}/rest/v1/payments"
            params = {"id": f"eq.{payment_id}"}

            async with httpx.AsyncClient() as client:
                response = await client.patch(
                    url,
                    headers={**self.headers, "Prefer": "return=minimal"},
                    params=params,
                    json={"status": status}
                )

            return response.status_code in [200, 204]
        except Exception as e:
            print(f"❌ Update payment status error: {str(e)}")
            return False

    async def get_user(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user from Supabase Auth by ID"""
        try:
            url = f"{self.url}/auth/v1/admin/users/{user_id}"

            async with httpx.AsyncClient() as client:
                response = await client.get(
                    url,
                    headers=self.headers
                )

            if response.status_code == 200:
                data = response.json()
                # Return as a simple object-like dict with common accessors
                return type('User', (), {
                    'id': data.get('id'),
                    'email': data.get('email'),
                    'user_metadata': data.get('user_metadata', {}),
                    'raw': data
                })()
            return None
        except Exception as e:
            print(f"❌ Get user error: {str(e)}")
            return None

    async def get_user_by_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user by ID (UUID string) from users table"""
        try:
            url = f"{self.url}/rest/v1/users"
            params = {"id": f"eq.{user_id}", "select": "*"}

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
            print(f"❌ Get user by ID error: {str(e)}")
            return None


    async def list_storage_folders(self, bucket: str) -> list:
        """
        List all top-level folders in a storage bucket.
        This is used to find websites in storage that may be missing from the database.

        Returns a list of folder names (subdomains).
        """
        try:
            url = f"{self.url}/storage/v1/object/list/{bucket}"

            # Use service headers to bypass RLS
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    url,
                    headers=self.service_headers,
                    json={
                        "prefix": "",
                        "limit": 1000,
                        "offset": 0,
                        "sortBy": {"column": "name", "order": "asc"}
                    },
                    timeout=30.0
                )

            if response.status_code == 200:
                items = response.json()
                # Filter to only get folders (items with no dot extension that look like subdomains)
                # Folders in Supabase storage are represented by their name
                folders = []
                for item in items:
                    name = item.get("name", "")
                    # Skip if it's a file (has extension) or empty
                    if name and "." not in name:
                        folders.append(name)
                    # Also check if it's a UUID-like folder (for user_id paths)
                    elif name and len(name) == 36 and name.count("-") == 4:
                        folders.append(name)
                return folders
            else:
                print(f"❌ List storage folders failed: {response.status_code} - {response.text}")
                return []
        except Exception as e:
            print(f"❌ List storage folders error: {str(e)}")
            return []

    async def list_all_websites_from_db(self) -> list:
        """
        Get all websites from the database.
        Returns list of website records with id, subdomain, user_id, business_name, status.
        """
        try:
            url = f"{self.url}/rest/v1/websites"
            params = {"select": "id,subdomain,user_id,business_name,status,created_at"}

            async with httpx.AsyncClient() as client:
                response = await client.get(
                    url,
                    headers=self.service_headers,
                    params=params
                )

            if response.status_code == 200:
                return response.json()
            else:
                print(f"❌ List all websites failed: {response.status_code}")
                return []
        except Exception as e:
            print(f"❌ List all websites error: {str(e)}")
            return []

    async def get_website_by_subdomain(self, subdomain: str) -> Optional[Dict[str, Any]]:
        """Get a website by its subdomain"""
        try:
            url = f"{self.url}/rest/v1/websites"
            params = {"subdomain": f"eq.{subdomain}", "select": "*"}

            async with httpx.AsyncClient() as client:
                response = await client.get(
                    url,
                    headers=self.service_headers,
                    params=params
                )

            if response.status_code == 200:
                records = response.json()
                return records[0] if records else None
            return None
        except Exception as e:
            print(f"❌ Get website by subdomain error: {str(e)}")
            return None

    async def check_subdomain_available(self, subdomain: str) -> bool:
        """Check if a subdomain is available (not in use)"""
        website = await self.get_website_by_subdomain(subdomain)
        return website is None

    async def create_missing_website_record(
        self,
        subdomain: str,
        user_id: Optional[str] = None,
        business_name: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Create a missing website record for an orphaned storage folder.
        This is used to fix websites that exist in storage but not in the database.

        Args:
            subdomain: The subdomain/folder name
            user_id: The owner's user ID (if known)
            business_name: The business name (if known, otherwise derived from subdomain)
        """
        import uuid
        from datetime import datetime

        try:
            # Generate a new UUID for the website if not extractable from storage
            website_id = str(uuid.uuid4())

            # Use subdomain as business name if not provided
            if not business_name:
                # Convert subdomain to readable format (e.g., "wowo-makan" -> "Wowo Makan")
                business_name = subdomain.replace("-", " ").replace("_", " ").title()

            # If user_id is not known, we'll need to either:
            # 1. Set it to a system/admin user
            # 2. Try to extract from storage metadata
            # For now, we'll create without user_id if not provided (will need manual fix)
            website_data = {
                "id": website_id,
                "subdomain": subdomain,
                "business_name": business_name,
                "status": "published",  # Assume published since it's in storage
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat()
            }

            if user_id:
                website_data["user_id"] = user_id

            url = f"{self.url}/rest/v1/websites"

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    url,
                    headers={**self.service_headers, "Prefer": "return=representation"},
                    json=website_data
                )

            if response.status_code in [200, 201]:
                result = response.json()
                created = result[0] if isinstance(result, list) else result
                print(f"✅ Created missing website record: {subdomain} -> {website_id}")
                return created
            else:
                print(f"❌ Create missing website failed: {response.status_code} - {response.text}")
                return None
        except Exception as e:
            print(f"❌ Create missing website error: {str(e)}")
            return None


# Create singleton instance
supabase_service = SupabaseService()