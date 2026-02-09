"""
BinaApp AI Website Rebuilder Service
Triggers full rebuild for low-health-score websites using existing generation flow.
Always requires user approval before applying.
"""
import httpx
from datetime import datetime
from typing import Dict, Any, Optional, List
from loguru import logger

from app.core.config import settings


class AIWebsiteRebuilder:
    """Rebuilds websites using existing AI generation flow."""

    def __init__(self):
        self.supabase_url = settings.SUPABASE_URL
        self.headers = {
            "apikey": settings.SUPABASE_SERVICE_ROLE_KEY,
            "Authorization": f"Bearer {settings.SUPABASE_SERVICE_ROLE_KEY}",
            "Content-Type": "application/json"
        }

    async def trigger_rebuild(
        self,
        website_id: str,
        user_id: str,
        trigger_reason: str = "manual"
    ) -> Optional[Dict[str, Any]]:
        """Trigger a website rebuild."""
        try:
            async with httpx.AsyncClient() as client:
                # Get current website
                web_resp = await client.get(
                    f"{self.supabase_url}/rest/v1/websites",
                    headers=self.headers,
                    params={"id": f"eq.{website_id}", "user_id": f"eq.{user_id}", "select": "*"}
                )

                if web_resp.status_code != 200 or not web_resp.json():
                    return {"error": "Laman web tidak dijumpai"}

                website = web_resp.json()[0]

                # Get latest health score
                health_resp = await client.get(
                    f"{self.supabase_url}/rest/v1/website_health_scans",
                    headers=self.headers,
                    params={
                        "website_id": f"eq.{website_id}",
                        "select": "overall_score",
                        "order": "created_at.desc",
                        "limit": "1"
                    }
                )
                old_score = None
                if health_resp.status_code == 200 and health_resp.json():
                    old_score = health_resp.json()[0].get("overall_score")

                # Save old HTML
                old_html = website.get("html_content") or website.get("generated_html") or ""

                # Check for pending rebuild
                pending_resp = await client.get(
                    f"{self.supabase_url}/rest/v1/website_rebuilds",
                    headers=self.headers,
                    params={
                        "website_id": f"eq.{website_id}",
                        "status": "in.(pending,generating,preview_ready)",
                        "select": "id,status"
                    }
                )
                if pending_resp.status_code == 200 and pending_resp.json():
                    return {"error": "Sudah ada proses bina semula yang sedang berjalan"}

                # Create rebuild record
                rebuild_data = {
                    "website_id": website_id,
                    "user_id": user_id,
                    "trigger_reason": trigger_reason,
                    "old_health_score": old_score,
                    "old_html": old_html[:50000] if old_html else None,
                    "status": "generating"
                }

                create_resp = await client.post(
                    f"{self.supabase_url}/rest/v1/website_rebuilds",
                    headers={**self.headers, "Prefer": "return=representation"},
                    json=rebuild_data
                )

                if create_resp.status_code not in [200, 201]:
                    return {"error": "Gagal mencipta rekod bina semula"}

                rebuild = create_resp.json()
                rebuild_record = rebuild[0] if isinstance(rebuild, list) else rebuild
                rebuild_id = rebuild_record["id"]

            # Generate new HTML using existing AI service
            try:
                new_html = await self._generate_new_html(website)

                if new_html:
                    # Generate changes summary
                    changes = self._summarize_changes(old_html, new_html)

                    async with httpx.AsyncClient() as client:
                        await client.patch(
                            f"{self.supabase_url}/rest/v1/website_rebuilds",
                            headers={**self.headers, "Prefer": "return=minimal"},
                            params={"id": f"eq.{rebuild_id}"},
                            json={
                                "new_html": new_html[:50000],
                                "changes_summary": changes,
                                "status": "preview_ready"
                            }
                        )

                    rebuild_record["status"] = "preview_ready"
                    rebuild_record["changes_summary"] = changes
                else:
                    async with httpx.AsyncClient() as client:
                        await client.patch(
                            f"{self.supabase_url}/rest/v1/website_rebuilds",
                            headers={**self.headers, "Prefer": "return=minimal"},
                            params={"id": f"eq.{rebuild_id}"},
                            json={"status": "failed"}
                        )
                    rebuild_record["status"] = "failed"

            except Exception as gen_err:
                logger.error(f"Generation error: {gen_err}")
                async with httpx.AsyncClient() as client:
                    await client.patch(
                        f"{self.supabase_url}/rest/v1/website_rebuilds",
                        headers={**self.headers, "Prefer": "return=minimal"},
                        params={"id": f"eq.{rebuild_id}"},
                        json={"status": "failed"}
                    )
                rebuild_record["status"] = "failed"

            return rebuild_record

        except Exception as e:
            logger.error(f"Error triggering rebuild: {e}")
            return {"error": str(e)}

    async def _generate_new_html(self, website: Dict) -> Optional[str]:
        """Generate new HTML using the existing AI generation flow via DeepSeek."""
        try:
            business_name = website.get("business_name", "Kedai")
            business_type = website.get("business_type", "restaurant")
            description = website.get("description", business_name)

            prompt = f"""Bina semula laman web untuk perniagaan:
Nama: {business_name}
Jenis: {business_type}
Keterangan: {description}

Hasilkan HTML yang lengkap, moden, responsif dan profesional.
Gunakan Tailwind CSS via CDN.
Pastikan ada: header, hero section, menu/perkhidmatan, tentang kami, hubungi kami, footer.
Gunakan Bahasa Melayu.
Pastikan semua imej menggunakan placeholder dari https://placehold.co/.
HTML sahaja, tiada penjelasan lain."""

            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    f"{settings.DEEPSEEK_API_URL}/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {settings.DEEPSEEK_API_KEY}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": settings.DEEPSEEK_MODEL,
                        "messages": [
                            {
                                "role": "system",
                                "content": "You are a professional web developer. Generate complete, modern, responsive HTML websites. Always use Tailwind CSS via CDN. Output ONLY the HTML code."
                            },
                            {"role": "user", "content": prompt}
                        ],
                        "max_tokens": 8000,
                        "temperature": 0.7
                    }
                )

                if response.status_code == 200:
                    data = response.json()
                    content = data["choices"][0]["message"]["content"]
                    # Extract HTML from response
                    if "```html" in content:
                        content = content.split("```html")[1].split("```")[0]
                    elif "```" in content:
                        content = content.split("```")[1].split("```")[0]
                    return content.strip()

            return None
        except Exception as e:
            logger.error(f"Error generating HTML: {e}")
            return None

    def _summarize_changes(self, old_html: str, new_html: str) -> list:
        """Summarize changes between old and new HTML."""
        changes = []
        if not old_html:
            changes.append({"type": "full_rebuild", "description": "Laman web baru dijana sepenuhnya"})
            return changes

        old_len = len(old_html)
        new_len = len(new_html)

        if new_len > old_len * 1.2:
            changes.append({"type": "content_added", "description": "Lebih banyak kandungan ditambah"})
        elif new_len < old_len * 0.8:
            changes.append({"type": "content_reduced", "description": "Kandungan dioptimumkan"})

        # Check for responsive design
        if "responsive" in new_html.lower() or "md:" in new_html or "lg:" in new_html:
            changes.append({"type": "responsive", "description": "Reka bentuk responsif dipertingkatkan"})

        # Check for Tailwind
        if "tailwindcss" in new_html.lower():
            changes.append({"type": "styling", "description": "Gaya Tailwind CSS ditambah"})

        if not changes:
            changes.append({"type": "refresh", "description": "Reka bentuk dikemas kini"})

        return changes

    async def get_rebuild_history(self, website_id: str, user_id: str) -> List[Dict]:
        """Get rebuild history for a website."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.supabase_url}/rest/v1/website_rebuilds",
                    headers=self.headers,
                    params={
                        "website_id": f"eq.{website_id}",
                        "user_id": f"eq.{user_id}",
                        "select": "id,trigger_reason,old_health_score,new_health_score,status,changes_summary,created_at,approved_at,applied_at",
                        "order": "created_at.desc",
                        "limit": "20"
                    }
                )
            if response.status_code == 200:
                return response.json()
            return []
        except Exception as e:
            logger.error(f"Error getting rebuild history: {e}")
            return []

    async def get_preview(self, rebuild_id: str, user_id: str) -> Optional[Dict]:
        """Get before/after preview for a rebuild."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.supabase_url}/rest/v1/website_rebuilds",
                    headers=self.headers,
                    params={
                        "id": f"eq.{rebuild_id}",
                        "user_id": f"eq.{user_id}",
                        "select": "*"
                    }
                )
            if response.status_code == 200 and response.json():
                return response.json()[0]
            return None
        except Exception as e:
            logger.error(f"Error getting preview: {e}")
            return None

    async def approve_rebuild(self, rebuild_id: str, user_id: str) -> Dict[str, Any]:
        """Approve and apply a rebuild."""
        try:
            async with httpx.AsyncClient() as client:
                # Get the rebuild
                rebuild_resp = await client.get(
                    f"{self.supabase_url}/rest/v1/website_rebuilds",
                    headers=self.headers,
                    params={
                        "id": f"eq.{rebuild_id}",
                        "user_id": f"eq.{user_id}",
                        "select": "*"
                    }
                )

                if rebuild_resp.status_code != 200 or not rebuild_resp.json():
                    return {"success": False, "error": "Rekod bina semula tidak dijumpai"}

                rebuild = rebuild_resp.json()[0]
                if rebuild["status"] != "preview_ready":
                    return {"success": False, "error": "Bina semula tidak dalam status sedia untuk semakan"}

                new_html = rebuild.get("new_html")
                website_id = rebuild["website_id"]

                if not new_html:
                    return {"success": False, "error": "HTML baru tidak tersedia"}

                # Apply new HTML to website
                now = datetime.utcnow().isoformat()
                await client.patch(
                    f"{self.supabase_url}/rest/v1/websites",
                    headers={**self.headers, "Prefer": "return=minimal"},
                    params={"id": f"eq.{website_id}"},
                    json={"html_content": new_html, "updated_at": now}
                )

                # Update rebuild record
                await client.patch(
                    f"{self.supabase_url}/rest/v1/website_rebuilds",
                    headers={**self.headers, "Prefer": "return=minimal"},
                    params={"id": f"eq.{rebuild_id}"},
                    json={"status": "applied", "approved_at": now, "applied_at": now}
                )

            return {"success": True, "message": "Laman web berjaya dikemas kini!"}

        except Exception as e:
            logger.error(f"Error approving rebuild: {e}")
            return {"success": False, "error": str(e)}

    async def reject_rebuild(self, rebuild_id: str, user_id: str, reason: str = "") -> Dict[str, Any]:
        """Reject a rebuild."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.patch(
                    f"{self.supabase_url}/rest/v1/website_rebuilds",
                    headers={**self.headers, "Prefer": "return=minimal"},
                    params={"id": f"eq.{rebuild_id}", "user_id": f"eq.{user_id}"},
                    json={"status": "rejected", "rejected_reason": reason}
                )
            return {"success": response.status_code in [200, 204]}
        except Exception as e:
            logger.error(f"Error rejecting rebuild: {e}")
            return {"success": False, "error": str(e)}


ai_website_rebuilder = AIWebsiteRebuilder()
