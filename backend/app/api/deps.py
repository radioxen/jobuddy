from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.services.websocket_manager import get_ws_manager, WebSocketManager
from app.services.browser_manager import get_browser_manager, BrowserManager


async def get_user_id() -> int:
    """Get the current user ID. Single-user app, always returns 1."""
    return 1
