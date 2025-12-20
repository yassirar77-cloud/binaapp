from loguru import logger

class ScreenshotService:
    def __init__(self):
        self.enabled = False

    async def initialize(self):
        logger.info("Screenshot service disabled")
        self.enabled = False

    async def capture(self, url: str, width: int = 1280, height: int = 800):
        return None

    async def close(self):
        pass

screenshot_service = ScreenshotService()
