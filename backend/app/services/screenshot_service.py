"""
Screenshot Service - Playwright Integration
Generates screenshots and preview images for websites
"""

import asyncio
import base64
import tempfile
import os
from pathlib import Path
from typing import Optional, Dict, List
from loguru import logger
from io import BytesIO
from PIL import Image

try:
    from playwright.async_api import async_playwright, Browser, Page
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False
    logger.warning("Playwright not installed. Screenshot functionality will be disabled.")


class ScreenshotService:
    """Service for generating website screenshots and previews"""

    def __init__(self):
        self.browser: Optional[Browser] = None
        self.playwright = None
        self.screenshots_dir = Path("storage/screenshots")
        self.screenshots_dir.mkdir(parents=True, exist_ok=True)
        logger.info("Screenshot service initialized")

    async def initialize(self):
        """Initialize Playwright browser"""
        global PLAYWRIGHT_AVAILABLE
        if not PLAYWRIGHT_AVAILABLE:
            logger.warning("Playwright not available, screenshots disabled")
            return

        try:
            if not self.playwright:
                self.playwright = await async_playwright().start()
                self.browser = await self.playwright.chromium.launch(
                    headless=True,
                    args=[
                        '--no-sandbox',
                        '--disable-setuid-sandbox',
                        '--disable-dev-shm-usage',
                        '--disable-gpu'
                    ]
                )
                logger.info("Playwright browser launched successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Playwright: {e}")
            PLAYWRIGHT_AVAILABLE = False

    async def close(self):
        """Close Playwright browser"""
        if self.browser:
            await self.browser.close()
            self.browser = None
        if self.playwright:
            await self.playwright.stop()
            self.playwright = None
            logger.info("Playwright browser closed")

    async def generate_screenshot(
        self,
        html_content: str,
        width: int = 1200,
        height: int = 800,
        full_page: bool = False,
        device: str = "desktop"
    ) -> Optional[bytes]:
        """
        Generate screenshot from HTML content

        Args:
            html_content: HTML string to render
            width: Viewport width in pixels
            height: Viewport height in pixels
            full_page: Capture full scrollable page
            device: Device type (desktop, tablet, mobile)

        Returns:
            Screenshot as bytes (PNG format) or None if failed
        """
        if not PLAYWRIGHT_AVAILABLE:
            logger.warning("Playwright not available, returning None")
            return None

        try:
            # Initialize browser if needed
            if not self.browser:
                await self.initialize()

            if not self.browser:
                return None

            # Device configurations
            device_configs = {
                "desktop": {"width": 1920, "height": 1080},
                "tablet": {"width": 768, "height": 1024},
                "mobile": {"width": 375, "height": 667}
            }

            viewport = device_configs.get(device, {"width": width, "height": height})

            # Create new page
            page = await self.browser.new_page(
                viewport=viewport,
                device_scale_factor=2  # Retina quality
            )

            try:
                # Set content
                await page.set_content(html_content, wait_until="networkidle")

                # Wait for any animations/fonts to load
                await asyncio.sleep(0.5)

                # Take screenshot
                screenshot_bytes = await page.screenshot(
                    type="png",
                    full_page=full_page,
                    animations="disabled"  # Disable animations for consistent screenshots
                )

                logger.info(f"Screenshot generated: {len(screenshot_bytes)} bytes ({device})")
                return screenshot_bytes

            finally:
                await page.close()

        except Exception as e:
            logger.error(f"Error generating screenshot: {e}")
            return None

    async def generate_thumbnail(
        self,
        html_content: str,
        width: int = 400,
        height: int = 300,
        device: str = "desktop"
    ) -> Optional[bytes]:
        """
        Generate thumbnail preview (smaller, fixed size)

        Args:
            html_content: HTML string to render
            width: Thumbnail width
            height: Thumbnail height
            device: Device type

        Returns:
            Thumbnail as bytes (PNG format) or None if failed
        """
        # Generate full screenshot first
        screenshot_bytes = await self.generate_screenshot(
            html_content,
            device=device,
            full_page=False
        )

        if not screenshot_bytes:
            return None

        try:
            # Resize to thumbnail
            image = Image.open(BytesIO(screenshot_bytes))
            image.thumbnail((width, height), Image.Resampling.LANCZOS)

            # Convert to bytes
            output = BytesIO()
            image.save(output, format="PNG", optimize=True)
            thumbnail_bytes = output.getvalue()

            logger.info(f"Thumbnail generated: {width}x{height}")
            return thumbnail_bytes

        except Exception as e:
            logger.error(f"Error generating thumbnail: {e}")
            return None

    async def generate_social_preview(
        self,
        html_content: str,
        business_name: str,
        style: str = "modern"
    ) -> Optional[bytes]:
        """
        Generate social media preview card (Open Graph image)
        Size: 1200x630 (Facebook/Twitter recommended)

        Args:
            html_content: HTML string to render
            business_name: Business name for overlay
            style: Design style (modern, minimal, bold)

        Returns:
            Social preview as bytes (PNG format) or None if failed
        """
        try:
            # Generate full screenshot
            screenshot_bytes = await self.generate_screenshot(
                html_content,
                width=1200,
                height=630,
                full_page=False,
                device="desktop"
            )

            if not screenshot_bytes:
                return None

            # Open image and add overlay
            image = Image.open(BytesIO(screenshot_bytes))

            # Crop to social media dimensions if needed
            if image.size != (1200, 630):
                # Center crop
                left = (image.width - 1200) / 2
                top = (image.height - 630) / 2
                right = left + 1200
                bottom = top + 630
                image = image.crop((left, top, right, bottom))

            # Convert to bytes
            output = BytesIO()
            image.save(output, format="PNG", optimize=True, quality=95)
            preview_bytes = output.getvalue()

            logger.info(f"Social preview generated for {business_name}")
            return preview_bytes

        except Exception as e:
            logger.error(f"Error generating social preview: {e}")
            return None

    async def generate_multi_device_screenshots(
        self,
        html_content: str
    ) -> Dict[str, Optional[bytes]]:
        """
        Generate screenshots for multiple devices

        Args:
            html_content: HTML string to render

        Returns:
            Dict with device names as keys and screenshot bytes as values
        """
        devices = ["desktop", "tablet", "mobile"]
        screenshots = {}

        try:
            # Generate all screenshots in parallel
            tasks = [
                self.generate_screenshot(html_content, device=device)
                for device in devices
            ]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            for device, result in zip(devices, results):
                if isinstance(result, Exception):
                    logger.error(f"Failed to generate {device} screenshot: {result}")
                    screenshots[device] = None
                else:
                    screenshots[device] = result

            logger.info(f"Generated {len([s for s in screenshots.values() if s])} device screenshots")
            return screenshots

        except Exception as e:
            logger.error(f"Error generating multi-device screenshots: {e}")
            return {device: None for device in devices}

    def screenshot_to_base64(self, screenshot_bytes: bytes) -> str:
        """
        Convert screenshot bytes to base64 data URI

        Args:
            screenshot_bytes: Screenshot as bytes

        Returns:
            Base64 data URI string
        """
        base64_str = base64.b64encode(screenshot_bytes).decode('utf-8')
        return f"data:image/png;base64,{base64_str}"

    async def save_screenshot(
        self,
        screenshot_bytes: bytes,
        filename: str
    ) -> str:
        """
        Save screenshot to disk

        Args:
            screenshot_bytes: Screenshot as bytes
            filename: Filename (without path)

        Returns:
            File path
        """
        try:
            filepath = self.screenshots_dir / filename
            filepath.write_bytes(screenshot_bytes)
            logger.info(f"Screenshot saved: {filepath}")
            return str(filepath)
        except Exception as e:
            logger.error(f"Error saving screenshot: {e}")
            raise

    async def generate_variation_previews(
        self,
        variations: List[Dict[str, str]]
    ) -> List[Dict[str, any]]:
        """
        Generate preview images for multiple style variations

        Args:
            variations: List of dicts with 'style' and 'html' keys

        Returns:
            List of dicts with added 'preview_image' (base64) and 'thumbnail' (base64)
        """
        if not PLAYWRIGHT_AVAILABLE:
            logger.warning("Playwright not available, returning variations without previews")
            return variations

        try:
            # Initialize browser
            if not self.browser:
                await self.initialize()

            results = []

            for variation in variations:
                style = variation.get('style', 'unknown')
                html = variation.get('html', '')

                try:
                    # Generate thumbnail for card preview
                    thumbnail_bytes = await self.generate_thumbnail(html, width=400, height=300)

                    # Generate social preview
                    social_bytes = await self.generate_social_preview(
                        html,
                        business_name=f"{style.capitalize()} Design",
                        style=style
                    )

                    # Add to variation
                    result = {
                        **variation,
                        'thumbnail': self.screenshot_to_base64(thumbnail_bytes) if thumbnail_bytes else None,
                        'social_preview': self.screenshot_to_base64(social_bytes) if social_bytes else None,
                    }
                    results.append(result)

                    logger.info(f"Generated previews for {style} variation")

                except Exception as e:
                    logger.error(f"Error generating preview for {style}: {e}")
                    results.append(variation)  # Return without preview

            return results

        except Exception as e:
            logger.error(f"Error generating variation previews: {e}")
            return variations


# Create singleton instance
screenshot_service = ScreenshotService()
