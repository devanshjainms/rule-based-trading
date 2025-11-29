"""
FastAPI authentication dependencies and middleware.

Provides request-level authentication and user context injection.

:copyright: (c) 2025
:license: MIT
"""

import logging
from typing import Annotated, Optional

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from src.auth.jwt import JWTManager, TokenPayload, get_jwt_manager
from src.cache import get_redis_cache
from src.core.sessions import SessionManager, UserContext, get_session_manager

logger = logging.getLogger(__name__)


security = HTTPBearer(auto_error=False)


class AuthError(HTTPException):
    """Authentication error."""

    def __init__(self, detail: str = "Could not validate credentials"):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail,
            headers={"WWW-Authenticate": "Bearer"},
        )


class PermissionError(HTTPException):
    """Permission denied error."""

    def __init__(self, detail: str = "Permission denied"):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=detail,
        )


async def get_current_token(
    credentials: Annotated[Optional[HTTPAuthorizationCredentials], Depends(security)],
    jwt_manager: Annotated[JWTManager, Depends(get_jwt_manager)],
) -> TokenPayload:
    """
    Extract and validate JWT token from request.

    :param credentials: HTTP Bearer credentials.
    :type credentials: Optional[HTTPAuthorizationCredentials]
    :param jwt_manager: JWT manager.
    :type jwt_manager: JWTManager
    :returns: Token payload.
    :rtype: TokenPayload
    :raises AuthError: If token invalid or missing.
    """
    if not credentials:
        raise AuthError("Missing authentication token")

    payload = jwt_manager.verify_token(credentials.credentials)
    if not payload:
        raise AuthError("Invalid or expired token")

    return payload


async def get_current_user_id(
    token: Annotated[TokenPayload, Depends(get_current_token)],
) -> str:
    """
    Get current user ID from token.

    :param token: Validated token payload.
    :type token: TokenPayload
    :returns: User ID.
    :rtype: str
    """
    return token.sub


async def get_current_context(
    user_id: Annotated[str, Depends(get_current_user_id)],
    session_manager: Annotated[SessionManager, Depends(get_session_manager)],
) -> UserContext:
    """
    Get current user context.

    :param user_id: Current user ID.
    :type user_id: str
    :param session_manager: Session manager.
    :type session_manager: SessionManager
    :returns: User context.
    :rtype: UserContext
    :raises AuthError: If no active session.
    """
    context = session_manager.get_context(user_id)
    if not context:
        raise AuthError("No active trading session")

    if not context.is_active:
        raise AuthError("Session is no longer active")

    return context


async def get_optional_context(
    credentials: Annotated[Optional[HTTPAuthorizationCredentials], Depends(security)],
    jwt_manager: Annotated[JWTManager, Depends(get_jwt_manager)],
    session_manager: Annotated[SessionManager, Depends(get_session_manager)],
) -> Optional[UserContext]:
    """
    Get user context if authenticated, None otherwise.

    :param credentials: HTTP Bearer credentials.
    :type credentials: Optional[HTTPAuthorizationCredentials]
    :param jwt_manager: JWT manager.
    :type jwt_manager: JWTManager
    :param session_manager: Session manager.
    :type session_manager: SessionManager
    :returns: User context or None.
    :rtype: Optional[UserContext]
    """
    if not credentials:
        return None

    payload = jwt_manager.verify_token(credentials.credentials)
    if not payload:
        return None

    return session_manager.get_context(payload.sub)


class RequirePermission:
    """
    Permission checker dependency.

    Example::

        @router.delete("/admin/users/{user_id}")
        async def delete_user(
            user_id: str,
            _: None = Depends(RequirePermission("admin")),
        ):
            pass
    """

    def __init__(self, *permissions: str) -> None:
        """
        Initialize permission checker.

        :param permissions: Required permissions.
        :type permissions: str
        """
        self.permissions = set(permissions)

    async def __call__(
        self,
        token: Annotated[TokenPayload, Depends(get_current_token)],
    ) -> None:
        """
        Check permissions.

        :param token: Current token.
        :type token: TokenPayload
        :raises PermissionError: If missing permissions.
        """
        user_permissions = set(token.data.get("permissions", []))
        if not self.permissions.issubset(user_permissions):
            missing = self.permissions - user_permissions
            raise PermissionError(f"Missing permissions: {missing}")


class RateLimiter:
    """
    Simple rate limiter using Redis.

    Example::

        limiter = RateLimiter(requests=100, window=60)

        @router.get("/api/data")
        async def get_data(_: None = Depends(limiter)):
            pass
    """

    def __init__(
        self,
        requests: int = 100,
        window: int = 60,
        key_prefix: str = "ratelimit:",
    ) -> None:
        """
        Initialize rate limiter.

        :param requests: Max requests per window.
        :type requests: int
        :param window: Window size in seconds.
        :type window: int
        :param key_prefix: Redis key prefix.
        :type key_prefix: str
        """
        self.requests = requests
        self.window = window
        self.key_prefix = key_prefix

    async def __call__(
        self,
        request: Request,
        user_id: Annotated[str, Depends(get_current_user_id)],
    ) -> None:
        """
        Check rate limit.

        :param request: HTTP request.
        :type request: Request
        :param user_id: Current user ID.
        :type user_id: str
        :raises HTTPException: If rate limited.
        """
        try:
            cache = get_redis_cache()
            key = f"{self.key_prefix}{user_id}"

            count = await cache.client.incr(cache._key(key))

            if count == 1:
                await cache.expire(key, self.window)

            if count > self.requests:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Rate limit exceeded",
                    headers={"Retry-After": str(self.window)},
                )
        except Exception as e:

            logger.warning(f"Rate limiter error: {e}")


async def get_user_broker_client(
    user_id: Annotated[str, Depends(get_current_user_id)],
):
    """
    Get broker client for current user from database.

    This dependency retrieves the user's broker credentials from
    the database and creates/returns a broker client instance.

    :param user_id: Current authenticated user ID.
    :type user_id: str
    :returns: Broker client or None if not configured.
    :rtype: Optional[any]
    """
    from src.brokers.factory import get_broker_factory

    factory = get_broker_factory()
    return await factory.get_client(user_id)


async def require_broker_client(
    user_id: Annotated[str, Depends(get_current_user_id)],
):
    """
    Require an active broker connection.

    Returns broker client if connected, raises HTTPException otherwise.

    :param user_id: Current authenticated user ID.
    :type user_id: str
    :returns: Broker client.
    :raises HTTPException: If no broker connected.
    """
    from src.brokers.factory import get_broker_factory

    factory = get_broker_factory()
    client = await factory.get_client(user_id)

    if not client:
        raise HTTPException(
            status_code=status.HTTP_428_PRECONDITION_REQUIRED,
            detail={
                "error": "broker_not_connected",
                "message": "No active broker connection. Please connect your broker first.",
                "action": "redirect_to_broker_auth",
                "auth_endpoint": "/user/broker",
                "supported_brokers": ["kite"],
                "instructions": [
                    "1. POST to /user/broker with your broker API key and secret",
                    "2. Redirect user to the returned auth_url",
                    "3. After broker login, handle callback at /auth/broker/callback",
                    "4. Retry this request after successful broker connection",
                ],
            },
        )

    return client


CurrentUser = Annotated[str, Depends(get_current_user_id)]
CurrentToken = Annotated[TokenPayload, Depends(get_current_token)]
CurrentContext = Annotated[UserContext, Depends(get_current_context)]
OptionalContext = Annotated[Optional[UserContext], Depends(get_optional_context)]
BrokerClient = Annotated[any, Depends(require_broker_client)]
OptionalBrokerClient = Annotated[Optional[any], Depends(get_user_broker_client)]
