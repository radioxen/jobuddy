import asyncio
from typing import Optional

from playwright.async_api import async_playwright, Browser, BrowserContext, Page
from playwright._impl._errors import TargetClosedError

from app.config import settings


class BrowserManager:
    """Manages a Playwright browser with persistent context for job applications."""

    def __init__(self):
        self.profile_dir = settings.BROWSER_PROFILE_DIR
        self.headless = settings.PLAYWRIGHT_HEADLESS
        self._playwright = None
        self._context: Optional[BrowserContext] = None
        self._initialized = False

    async def initialize(self):
        """Start Playwright and create persistent browser context."""
        if self._initialized:
            return

        self._playwright = await async_playwright().start()
        self._context = await self._playwright.chromium.launch_persistent_context(
            user_data_dir=self.profile_dir,
            headless=self.headless,
            viewport={"width": 1280, "height": 900},
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
            ],
            ignore_default_args=["--enable-automation"],
        )
        self._initialized = True

    async def ensure_initialized(self):
        """Ensure browser is initialized, reinitializing if context was closed."""
        if not self._initialized:
            await self.initialize()
            return

        # Check if context is still valid
        try:
            # Try to access pages - will fail if context is closed
            _ = self._context.pages
        except Exception:
            # Context was closed, reinitialize
            self._initialized = False
            self._context = None
            if self._playwright:
                try:
                    await self._playwright.stop()
                except Exception:
                    pass
                self._playwright = None
            await self.initialize()

    async def _reset_and_reinitialize(self):
        """Reset state and reinitialize browser."""
        self._initialized = False
        self._context = None
        if self._playwright:
            try:
                await self._playwright.stop()
            except Exception:
                pass
            self._playwright = None
        await self.initialize()

    async def new_page(self, url: Optional[str] = None) -> Page:
        """Open a new browser tab, optionally navigating to a URL."""
        await self.ensure_initialized()
        try:
            page = await self._context.new_page()
        except TargetClosedError:
            # Browser was closed, reinitialize
            await self._reset_and_reinitialize()
            page = await self._context.new_page()
        if url:
            await page.goto(url, wait_until="domcontentloaded", timeout=30000)
        return page

    async def get_pages(self) -> list[Page]:
        """Get all open browser tabs."""
        await self.ensure_initialized()
        try:
            return self._context.pages
        except TargetClosedError:
            await self._reset_and_reinitialize()
            return self._context.pages

    async def close_page(self, page: Page):
        """Close a specific browser tab."""
        try:
            await page.close()
        except Exception:
            pass

    async def is_logged_in(self, platform: str) -> bool:
        """Check if the user is logged into a platform."""
        await self.ensure_initialized()
        page = await self.new_page()
        try:
            if platform == "linkedin":
                await page.goto(
                    "https://www.linkedin.com/feed/", wait_until="domcontentloaded"
                )
                await page.wait_for_timeout(2000)
                return "feed" in page.url and "login" not in page.url
            elif platform == "indeed":
                await page.goto(
                    "https://www.indeed.com/account/view",
                    wait_until="domcontentloaded",
                )
                await page.wait_for_timeout(2000)
                return "login" not in page.url and "auth" not in page.url
            return False
        except Exception:
            return False
        finally:
            await self.close_page(page)

    async def open_login_page(self, platform: str) -> Page:
        """Open a login page for the user to manually log in."""
        await self.ensure_initialized()
        urls = {
            "linkedin": "https://www.linkedin.com/login",
            "indeed": "https://secure.indeed.com/auth",
        }
        url = urls.get(platform, "")
        if not url:
            raise ValueError(f"Unknown platform: {platform}")
        return await self.new_page(url)

    async def get_status(self) -> dict:
        """Get current browser status."""
        if not self._initialized:
            return {
                "initialized": False,
                "pages": 0,
                "linkedin_logged_in": False,
                "indeed_logged_in": False,
            }

        pages = await self.get_pages()
        linkedin_status = await self.is_logged_in("linkedin")
        indeed_status = await self.is_logged_in("indeed")

        return {
            "initialized": True,
            "pages": len(pages),
            "linkedin_logged_in": linkedin_status,
            "indeed_logged_in": indeed_status,
        }

    async def close(self):
        """Shut down the browser."""
        if self._context:
            await self._context.close()
            self._context = None
        if self._playwright:
            await self._playwright.stop()
            self._playwright = None
        self._initialized = False


# Singleton
_browser_manager: Optional[BrowserManager] = None


def get_browser_manager() -> BrowserManager:
    global _browser_manager
    if _browser_manager is None:
        _browser_manager = BrowserManager()
    return _browser_manager
