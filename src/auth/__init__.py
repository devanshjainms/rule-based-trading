"""
Authentication and authorization package.

Provides JWT authentication, OAuth flows, and FastAPI dependencies.

:copyright: (c) 2025
:license: MIT
"""

from src.auth.dependencies import (
    AuthError,
    BrokerClient,
    CurrentContext,
    CurrentToken,
    CurrentUser,
    OptionalBrokerClient,
    OptionalContext,
    PermissionError,
    RateLimiter,
    RequirePermission,
    get_current_context,
    get_current_token,
    get_current_user_id,
    get_optional_context,
    get_user_broker_client,
    require_broker_client,
)
from src.auth.jwt import (
    JWTManager,
    TokenPayload,
    get_jwt_manager,
)
from src.auth.oauth import (
    OAuthManager,
    OAuthState,
    get_oauth_manager,
)

__all__ = [
    "JWTManager",
    "TokenPayload",
    "get_jwt_manager",
    "OAuthManager",
    "OAuthState",
    "get_oauth_manager",
    "AuthError",
    "PermissionError",
    "RequirePermission",
    "RateLimiter",
    "get_current_token",
    "get_current_user_id",
    "get_current_context",
    "get_optional_context",
    "get_user_broker_client",
    "require_broker_client",
    "CurrentUser",
    "CurrentToken",
    "CurrentContext",
    "OptionalContext",
    "BrokerClient",
    "OptionalBrokerClient",
]
