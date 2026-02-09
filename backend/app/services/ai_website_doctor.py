"""
AI Website Doctor Service
Scans websites, detects issues, and generates/applies fixes.
Uses Qwen VL for visual analysis and DeepSeek for code fixes.
"""

import json
import re
import uuid
from datetime import datetime
from typing import Optional
from html.parser import HTMLParser

import httpx
from loguru import logger
from openai import AsyncOpenAI

from app.core.config import settings
from app.core.supabase import get_supabase_client


class _HTMLIssueDetector(HTMLParser):
    """Lightweight HTML parser to detect common issues."""

    def __init__(self):
        super().__init__()
        self.issues: list[dict] = []
        self.has_viewport = False
        self.has_meta_description = False
        self.has_favicon = False
        self.has_title = False
        self.in_title = False
        self.title_text = ""
        self.img_count = 0
        self.img_no_alt = 0
        self.empty_sections = 0
        self.placeholder_texts: list[str] = []
        self._current_tag = ""
        self._current_attrs: list = []
        self._tag_stack: list[str] = []
        self._tag_content: dict[str, str] = {}

    def handle_starttag(self, tag: str, attrs: list):
        self._current_tag = tag
        self._current_attrs = attrs
        attr_dict = dict(attrs)

        if tag == "meta":
            name = attr_dict.get("name", "").lower()
            if name == "viewport":
                self.has_viewport = True
            if name == "description" and attr_dict.get("content", "").strip():
                self.has_meta_description = True

        if tag == "link":
            rel = attr_dict.get("rel", "").lower()
            if "icon" in rel:
                self.has_favicon = True

        if tag == "title":
            self.in_title = True

        if tag == "img":
            self.img_count += 1
            src = attr_dict.get("src", "").strip()
            alt = attr_dict.get("alt", "")
            if not src or src.startswith("data:image/svg") or src == "#" or src == "placeholder":
                self.issues.append({
                    "type": "broken_image",
                    "severity": "major",
                    "element": f"img[src='{src[:50]}']",
                    "description": "Image source is empty or placeholder",
                    "auto_fixable": True,
                })
            if not alt:
                self.img_no_alt += 1

        self._tag_stack.append(tag)
        self._tag_content[tag] = ""

    def handle_endtag(self, tag: str):
        if tag == "title":
            self.in_title = False
            if self.title_text.strip():
                self.has_title = True

        # Check for empty sections
        if tag in ("section", "div", "article") and self._tag_stack:
            content = self._tag_content.get(tag, "").strip()
            if not content:
                self.empty_sections += 1

        if self._tag_stack and self._tag_stack[-1] == tag:
            self._tag_stack.pop()

    def handle_data(self, data: str):
        if self.in_title:
            self.title_text += data

        for tag in self._tag_stack:
            if tag in self._tag_content:
                self._tag_content[tag] += data

        text = data.strip().lower()
        placeholder_patterns = [
            "lorem ipsum", "your text here", "add your", "placeholder",
            "coming soon", "under construction", "sample text",
            "edit this", "change this", "replace this",
        ]
        for pattern in placeholder_patterns:
            if pattern in text:
                self.placeholder_texts.append(data.strip()[:100])
                break

    def get_issues(self) -> list[dict]:
        issues = list(self.issues)

        if not self.has_viewport:
            issues.append({
                "type": "missing_viewport",
                "severity": "major",
                "element": "head",
                "description": "Missing mobile viewport meta tag",
                "auto_fixable": True,
            })

        if not self.has_meta_description:
            issues.append({
                "type": "missing_meta_description",
                "severity": "medium",
                "element": "head",
                "description": "Missing meta description for SEO",
                "auto_fixable": True,
            })

        if not self.has_favicon:
            issues.append({
                "type": "missing_favicon",
                "severity": "minor",
                "element": "head",
                "description": "Missing favicon",
                "auto_fixable": True,
            })

        if self.img_no_alt > 0:
            issues.append({
                "type": "missing_alt_tags",
                "severity": "medium",
                "element": "images",
                "description": f"{self.img_no_alt} image(s) missing alt text",
                "auto_fixable": True,
            })

        for placeholder in self.placeholder_texts[:5]:
            issues.append({
                "type": "placeholder_text",
                "severity": "major",
                "element": "content",
                "description": f"Placeholder text found: '{placeholder[:60]}...'",
                "auto_fixable": True,
            })

        if self.empty_sections > 2:
            issues.append({
                "type": "empty_sections",
                "severity": "medium",
                "element": "layout",
                "description": f"{self.empty_sections} empty sections detected",
                "auto_fixable": False,
            })

        return issues


class AIWebsiteDoctor:
    """
    AI service that scans websites, detects issues, and generates fixes.
    Uses Qwen VL for visual analysis and DeepSeek for code fixes.
    """

    def __init__(self):
        self.deepseek_client = AsyncOpenAI(
            api_key=settings.DEEPSEEK_API_KEY,
            base_url=settings.DEEPSEEK_API_URL,
        )
        self.qwen_client = AsyncOpenAI(
            api_key=settings.QWEN_API_KEY or "",
            base_url=settings.QWEN_API_URL,
        ) if settings.QWEN_API_KEY else None

    async def scan_website(self, website_id: str, user_id: str, scan_type: str = "manual") -> dict:
        """
        Full website health scan:
        1. Fetch website HTML
        2. Parse for technical issues
        3. Send to AI for analysis
        4. Score each category
        5. Store results
        """
        supabase = get_supabase_client()

        # Create scan record
        scan_id = str(uuid.uuid4())
        scan_data = {
            "id": scan_id,
            "website_id": website_id,
            "user_id": user_id,
            "scan_type": scan_type,
            "status": "scanning",
        }
        supabase.table("website_health_scans").insert(scan_data).execute()

        try:
            # 1. Fetch website HTML
            website_result = supabase.table("websites").select(
                "id, html_content, subdomain, business_name, business_type"
            ).eq("id", website_id).eq("user_id", user_id).execute()

            if not website_result.data:
                raise ValueError("Website not found or access denied")

            website = website_result.data[0]
            html_content = website.get("html_content", "")

            if not html_content:
                # Try fetching from storage
                try:
                    subdomain = website.get("subdomain", "")
                    if subdomain:
                        storage_url = f"{settings.SUPABASE_URL}/storage/v1/object/public/websites/{subdomain}/index.html"
                        async with httpx.AsyncClient() as client:
                            resp = await client.get(storage_url, timeout=15.0)
                            if resp.status_code == 200:
                                html_content = resp.text
                except Exception as e:
                    logger.warning(f"Failed to fetch from storage: {e}")

            if not html_content:
                supabase.table("website_health_scans").update({
                    "status": "failed",
                    "ai_summary": "Tiada kandungan HTML ditemui untuk laman web ini.",
                    "overall_score": 0,
                }).eq("id", scan_id).execute()
                return {"scan_id": scan_id, "status": "failed", "message": "No HTML content found"}

            # 2. Parse HTML for technical issues
            detector = _HTMLIssueDetector()
            try:
                detector.feed(html_content)
            except Exception:
                pass
            technical_issues = detector.get_issues()

            # 3. AI analysis
            ai_analysis = await self._ai_analyze(html_content, website)

            # 4. Merge issues and score
            all_issues = technical_issues + ai_analysis.get("issues", [])

            # Deduplicate by type
            seen_types = set()
            unique_issues = []
            for issue in all_issues:
                key = f"{issue['type']}:{issue.get('element', '')}"
                if key not in seen_types:
                    seen_types.add(key)
                    unique_issues.append(issue)

            # Calculate scores
            design_score = ai_analysis.get("design_score", 70)
            performance_score = ai_analysis.get("performance_score", 70)
            content_score = ai_analysis.get("content_score", 70)
            mobile_score = ai_analysis.get("mobile_score", 70)

            # Deduct points for technical issues
            for issue in unique_issues:
                sev = issue.get("severity", "medium")
                deduction = {"critical": 15, "major": 10, "medium": 5, "minor": 2}.get(sev, 5)
                issue_type = issue.get("type", "")
                if "image" in issue_type or "layout" in issue_type:
                    design_score = max(0, design_score - deduction)
                elif "viewport" in issue_type or "mobile" in issue_type:
                    mobile_score = max(0, mobile_score - deduction)
                elif "meta" in issue_type or "placeholder" in issue_type or "alt" in issue_type:
                    content_score = max(0, content_score - deduction)
                else:
                    performance_score = max(0, performance_score - deduction)

            overall_score = int(
                (design_score * 0.3 + performance_score * 0.2 + content_score * 0.3 + mobile_score * 0.2)
            )

            total_issues = len(unique_issues)
            critical_issues = sum(1 for i in unique_issues if i.get("severity") == "critical")
            auto_fixable_issues = sum(1 for i in unique_issues if i.get("auto_fixable"))

            # 5. Store results
            update_data = {
                "status": "completed",
                "overall_score": overall_score,
                "design_score": design_score,
                "performance_score": performance_score,
                "content_score": content_score,
                "mobile_score": mobile_score,
                "issues": json.dumps(unique_issues),
                "total_issues": total_issues,
                "critical_issues": critical_issues,
                "auto_fixable_issues": auto_fixable_issues,
                "ai_summary": ai_analysis.get("summary", ""),
                "ai_recommendations": json.dumps(ai_analysis.get("recommendations", [])),
                "model_used": "deepseek-chat",
            }
            supabase.table("website_health_scans").update(update_data).eq("id", scan_id).execute()

            # 6. Create fix records for each issue
            for issue in unique_issues:
                fix_data = {
                    "id": str(uuid.uuid4()),
                    "scan_id": scan_id,
                    "website_id": website_id,
                    "user_id": user_id,
                    "issue_type": issue["type"],
                    "issue_description": issue.get("description", ""),
                    "severity": issue.get("severity", "medium"),
                    "fix_type": "auto" if issue.get("auto_fixable") else "suggested",
                    "status": "pending",
                }
                supabase.table("website_fixes").insert(fix_data).execute()

            return {
                "scan_id": scan_id,
                "status": "completed",
                "overall_score": overall_score,
                "design_score": design_score,
                "performance_score": performance_score,
                "content_score": content_score,
                "mobile_score": mobile_score,
                "total_issues": total_issues,
                "critical_issues": critical_issues,
                "auto_fixable_issues": auto_fixable_issues,
                "ai_summary": ai_analysis.get("summary", ""),
            }

        except Exception as e:
            logger.error(f"Website scan failed: {e}")
            supabase.table("website_health_scans").update({
                "status": "failed",
                "ai_summary": f"Scan gagal: {str(e)}",
            }).eq("id", scan_id).execute()
            return {"scan_id": scan_id, "status": "failed", "message": str(e)}

    async def _ai_analyze(self, html_content: str, website: dict) -> dict:
        """Send HTML to DeepSeek for analysis."""
        truncated_html = html_content[:8000]
        business_name = website.get("business_name", "Unknown")
        business_type = website.get("business_type", "restaurant")

        prompt = f"""Analyze this website HTML for a Malaysian {business_type} called "{business_name}".

Rate each category from 0-100:
- design_score: Visual quality, layout, color scheme, typography
- performance_score: Code quality, no inline bloat, efficient structure
- content_score: Real content (not placeholder), proper descriptions, good copy
- mobile_score: Responsive design, touch-friendly, proper sizing

List any issues found as JSON array. Also provide a summary in Bahasa Melayu and recommendations.

HTML:
```
{truncated_html}
```

Return ONLY valid JSON:
{{
  "design_score": 75,
  "performance_score": 80,
  "content_score": 70,
  "mobile_score": 85,
  "summary": "Laman web ini ...",
  "issues": [
    {{"type": "issue_type", "severity": "minor|medium|major|critical", "element": "section", "description": "...", "auto_fixable": true}}
  ],
  "recommendations": ["...", "..."]
}}"""

        try:
            response = await self.deepseek_client.chat.completions.create(
                model=settings.DEEPSEEK_MODEL,
                messages=[
                    {"role": "system", "content": "You are a web design expert analyzing Malaysian business websites. Return ONLY valid JSON."},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.3,
                max_tokens=2000,
            )

            content = response.choices[0].message.content or "{}"
            # Strip markdown code blocks
            content = re.sub(r"^```(?:json)?\s*", "", content.strip())
            content = re.sub(r"\s*```$", "", content.strip())

            return json.loads(content)
        except Exception as e:
            logger.error(f"AI analysis failed: {e}")
            return {
                "design_score": 65,
                "performance_score": 65,
                "content_score": 65,
                "mobile_score": 65,
                "summary": "Analisis AI tidak tersedia buat masa ini.",
                "issues": [],
                "recommendations": [],
            }

    async def generate_fix(self, fix_id: str) -> dict:
        """Generate code fix for a specific issue."""
        supabase = get_supabase_client()

        fix_result = supabase.table("website_fixes").select("*").eq("id", fix_id).execute()
        if not fix_result.data:
            raise ValueError("Fix not found")

        fix = fix_result.data[0]
        website_id = fix["website_id"]

        website_result = supabase.table("websites").select("html_content").eq("id", website_id).execute()
        if not website_result.data:
            raise ValueError("Website not found")

        html_content = website_result.data[0].get("html_content", "")
        if not html_content:
            raise ValueError("No HTML content to fix")

        # Find relevant section
        issue_type = fix["issue_type"]
        issue_desc = fix["issue_description"]

        prompt = f"""Fix this specific issue in the website HTML:
Issue type: {issue_type}
Issue description: {issue_desc}

Current HTML (first 6000 chars):
```html
{html_content[:6000]}
```

Rules:
- Return ONLY the complete fixed HTML
- Keep ALL existing content and structure
- Only fix the specific issue mentioned
- For missing meta tags, add them to the <head>
- For placeholder text, replace with realistic Malaysian business content
- For missing alt tags, add descriptive alt text
- Do not change the overall design or layout

Return the fixed HTML wrapped in ```html ... ``` markers."""

        try:
            response = await self.deepseek_client.chat.completions.create(
                model=settings.DEEPSEEK_MODEL,
                messages=[
                    {"role": "system", "content": "You are a web developer fixing issues in Malaysian business websites. Return only the fixed HTML code."},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.2,
                max_tokens=8000,
            )

            content = response.choices[0].message.content or ""
            # Extract HTML from markdown code blocks
            html_match = re.search(r"```html\s*(.*?)\s*```", content, re.DOTALL)
            if html_match:
                fixed_html = html_match.group(1)
            else:
                # Try without language marker
                html_match = re.search(r"```\s*(.*?)\s*```", content, re.DOTALL)
                fixed_html = html_match.group(1) if html_match else content

            # Update fix record
            supabase.table("website_fixes").update({
                "code_before": html_content[:5000],
                "code_after": fixed_html[:5000],
                "fix_description": f"AI-generated fix for {issue_type}: {issue_desc}",
            }).eq("id", fix_id).execute()

            return {
                "fix_id": fix_id,
                "issue_type": issue_type,
                "code_before": html_content[:2000],
                "code_after": fixed_html[:2000],
                "fix_description": f"AI fix for: {issue_desc}",
            }

        except Exception as e:
            logger.error(f"Fix generation failed: {e}")
            raise ValueError(f"Failed to generate fix: {str(e)}")

    async def apply_fix(self, fix_id: str, applied_by: str = "user_approved") -> dict:
        """Apply a generated fix to the website."""
        supabase = get_supabase_client()

        fix_result = supabase.table("website_fixes").select("*").eq("id", fix_id).execute()
        if not fix_result.data:
            raise ValueError("Fix not found")

        fix = fix_result.data[0]
        if fix["status"] == "applied":
            return {"message": "Fix already applied", "fix_id": fix_id}

        code_after = fix.get("code_after")
        if not code_after:
            raise ValueError("No fix code generated. Generate the fix first.")

        website_id = fix["website_id"]

        # Update the website HTML
        supabase.table("websites").update({
            "html_content": code_after,
        }).eq("id", website_id).execute()

        # Try to also update storage
        try:
            website_result = supabase.table("websites").select("subdomain").eq("id", website_id).execute()
            if website_result.data:
                subdomain = website_result.data[0].get("subdomain", "")
                if subdomain:
                    from app.services.supabase_client import SupabaseService
                    svc = SupabaseService()
                    await svc.upload_file(
                        "websites",
                        f"{subdomain}/index.html",
                        code_after.encode("utf-8"),
                        "text/html; charset=utf-8",
                    )
        except Exception as e:
            logger.warning(f"Storage update failed (non-critical): {e}")

        # Update fix status
        supabase.table("website_fixes").update({
            "status": "applied",
            "applied_at": datetime.utcnow().isoformat(),
            "applied_by": applied_by,
        }).eq("id", fix_id).execute()

        # Update scan record
        scan_id = fix["scan_id"]
        scan_result = supabase.table("website_health_scans").select("auto_fixed_count").eq("id", scan_id).execute()
        if scan_result.data:
            current_count = scan_result.data[0].get("auto_fixed_count", 0)
            supabase.table("website_health_scans").update({
                "auto_fixed_count": current_count + 1,
            }).eq("id", scan_id).execute()

        return {"message": "Fix applied successfully", "fix_id": fix_id, "status": "applied"}

    async def revert_fix(self, fix_id: str) -> dict:
        """Revert an applied fix."""
        supabase = get_supabase_client()

        fix_result = supabase.table("website_fixes").select("*").eq("id", fix_id).execute()
        if not fix_result.data:
            raise ValueError("Fix not found")

        fix = fix_result.data[0]
        if fix["status"] != "applied":
            raise ValueError("Fix is not applied, cannot revert")

        code_before = fix.get("code_before")
        if not code_before:
            raise ValueError("No original code stored, cannot revert")

        website_id = fix["website_id"]
        supabase.table("websites").update({"html_content": code_before}).eq("id", website_id).execute()

        supabase.table("website_fixes").update({
            "status": "reverted",
        }).eq("id", fix_id).execute()

        return {"message": "Fix reverted successfully", "fix_id": fix_id, "status": "reverted"}

    async def auto_fix_safe_issues(self, scan_id: str, user_id: str) -> dict:
        """Auto-fix all safe/minor issues for a scan."""
        supabase = get_supabase_client()

        # Get pending auto-fixable issues
        fixes_result = supabase.table("website_fixes").select("*").eq(
            "scan_id", scan_id
        ).eq("status", "pending").eq("fix_type", "auto").execute()

        if not fixes_result.data:
            return {"message": "No auto-fixable issues found", "fixed_count": 0}

        safe_types = {
            "missing_alt_tags", "missing_meta_description", "placeholder_text",
            "missing_favicon", "broken_image", "missing_viewport",
        }

        fixed_count = 0
        errors = []

        for fix in fixes_result.data:
            if fix["issue_type"] not in safe_types:
                continue
            try:
                await self.generate_fix(fix["id"])
                await self.apply_fix(fix["id"], applied_by="ai_auto")
                fixed_count += 1
            except Exception as e:
                errors.append({"fix_id": fix["id"], "error": str(e)})
                logger.warning(f"Auto-fix failed for {fix['id']}: {e}")

        # Update scan status
        supabase.table("website_health_scans").update({
            "status": "fixed" if fixed_count > 0 else "completed",
            "auto_fixed_count": fixed_count,
        }).eq("id", scan_id).execute()

        return {
            "message": f"Auto-fixed {fixed_count} issues",
            "fixed_count": fixed_count,
            "errors": errors,
        }


# Singleton instance
website_doctor = AIWebsiteDoctor()
