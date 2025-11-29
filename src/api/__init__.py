"""
API package.

Provides FastAPI application and routers.

:copyright: (c) 2025
:license: MIT
"""

from src.api.app import app, create_app
from src.api.middleware import (
    ErrorHandlingMiddleware,
    RequestLoggingMiddleware,
    setup_cors,
    setup_middleware,
)
from src.api.routers import (
    MarketDataBroadcaster,
    WebSocketManager,
    auth_router,
    get_market_broadcaster,
    get_ws_manager,
    rules_router,
    trading_router,
    websocket_router,
)

__all__ = [
    "app",
    "create_app",
    "ErrorHandlingMiddleware",
    "RequestLoggingMiddleware",
    "setup_cors",
    "setup_middleware",
    "auth_router",
    "trading_router",
    "rules_router",
    "websocket_router",
    "WebSocketManager",
    "MarketDataBroadcaster",
    "get_ws_manager",
    "get_market_broadcaster",
]
