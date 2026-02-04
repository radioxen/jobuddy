from fastapi import APIRouter

from app.services.browser_manager import get_browser_manager

router = APIRouter()


@router.post("/start")
async def start_browser():
    """Initialize the Playwright browser."""
    bm = get_browser_manager()
    await bm.initialize()
    return {"message": "Browser started", "status": await bm.get_status()}


@router.get("/status")
async def browser_status():
    """Get current browser status including login state."""
    bm = get_browser_manager()
    return await bm.get_status()


@router.post("/login/{platform}")
async def open_login(platform: str):
    """Open a login page for manual authentication."""
    if platform not in ("linkedin", "indeed"):
        return {"error": f"Unknown platform: {platform}"}

    bm = get_browser_manager()
    await bm.open_login_page(platform)
    return {"message": f"Opened {platform} login page. Please log in manually."}


@router.post("/close")
async def close_browser():
    """Close the browser."""
    bm = get_browser_manager()
    await bm.close()
    return {"message": "Browser closed"}
