"""
API routers package.

:copyright: (c) 2025
:license: MIT
"""

from src.api.routers.auth import router as auth_router
from src.api.routers.rules import router as rules_router
from src.api.routers.trading import router as trading_router
from src.api.routers.user import router as user_router
from src.api.routers.websocket import (
    MarketDataBroadcaster,
    WebSocketManager,
    get_market_broadcaster,
    get_ws_manager,
    router as websocket_router,
)

__all__ = [
    "auth_router",
    "rules_router",
    "trading_router",
    "user_router",
    "websocket_router",
    "WebSocketManager",
    "MarketDataBroadcaster",
    "get_ws_manager",
    "get_market_broadcaster",
]
