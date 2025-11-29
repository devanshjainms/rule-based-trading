"""
Authentication API router.

Provides endpoints for user authentication and session management.

:copyright: (c) 2025
:license: MIT
"""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr, Field

from src.auth import (
    AuthError,
    CurrentUser,
    JWTManager,
    OAuthManager,
    get_jwt_manager,
    get_oauth_manager,
)
from src.core.sessions import SessionManager, get_session_manager
from src.database.repositories import PostgresUserRepository

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["Authentication"])


class LoginRequest(BaseModel):
    """Login request."""

    email: EmailStr
    password: str = Field(min_length=8)


class RegisterRequest(BaseModel):
    """Registration request."""

    email: EmailStr
    password: str = Field(min_length=8)
    name: str = Field(min_length=1, max_length=100)


class TokenResponse(BaseModel):
    """Token response."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class RefreshRequest(BaseModel):
    """Token refresh request."""

    refresh_token: str


class UserResponse(BaseModel):
    """User information response."""

    id: str
    email: str
    name: str
    is_active: bool


class BrokerAuthRequest(BaseModel):
    """Broker API credentials request - NOT login credentials."""

    broker: str = Field(description="Broker name (e.g., 'kite')")
    api_key: str = Field(description="Kite Connect API key from developer console")
    api_secret: str = Field(
        description="Kite Connect API secret from developer console"
    )
    redirect_uri: Optional[str] = None


class BrokerAuthResponse(BaseModel):
    """Broker OAuth response."""

    auth_url: str
    state: str


class BrokerCallbackRequest(BaseModel):
    """Broker OAuth callback."""

    broker: str
    code: str
    state: str


async def get_user_repository():
    """
    Get user repository instance with managed session.

    Yields a repository with a session that is automatically
    cleaned up when the request completes.
    """
    from src.database import get_database_manager

    db = get_database_manager()
    async with db.session() as session:
        yield PostgresUserRepository(session)


@router.post(
    "/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED
)
async def register(
    request: RegisterRequest,
    jwt_manager: JWTManager = Depends(get_jwt_manager),
    user_repo: PostgresUserRepository = Depends(get_user_repository),
) -> TokenResponse:
    """
    Register a new user.

    :param request: Registration details.
    :type request: RegisterRequest
    :param jwt_manager: JWT manager.
    :type jwt_manager: JWTManager
    :param user_repo: User repository.
    :type user_repo: PostgresUserRepository
    :returns: Access and refresh tokens.
    :rtype: TokenResponse
    :raises HTTPException: If email already registered.
    """

    existing = await user_repo.get_by_email(request.email)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered",
        )

    password_hash = jwt_manager.hash_password(request.password)

    from src.database.models import User

    user = User(
        email=request.email,
        hashed_password=password_hash,
        full_name=request.name,
    )

    created = await user_repo.create(user)

    tokens = jwt_manager.create_tokens(str(created.id))

    logger.info(f"User registered: {created.email}")

    return tokens


@router.post("/login", response_model=TokenResponse)
async def login(
    request: LoginRequest,
    jwt_manager: JWTManager = Depends(get_jwt_manager),
    user_repo: PostgresUserRepository = Depends(get_user_repository),
) -> TokenResponse:
    """
    Authenticate user and return tokens.

    :param request: Login credentials.
    :type request: LoginRequest
    :param jwt_manager: JWT manager.
    :type jwt_manager: JWTManager
    :param user_repo: User repository.
    :type user_repo: PostgresUserRepository
    :returns: Access and refresh tokens.
    :rtype: TokenResponse
    :raises AuthError: If credentials invalid.
    """

    user = await user_repo.get_by_email(request.email)
    if not user:
        raise AuthError("Invalid email or password")

    if not jwt_manager.verify_password(request.password, user.hashed_password):
        raise AuthError("Invalid email or password")

    if not user.is_active:
        raise AuthError("Account is disabled")

    tokens = jwt_manager.create_tokens(str(user.id))

    logger.info(f"User logged in: {user.email}")

    return tokens


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    request: RefreshRequest,
    jwt_manager: JWTManager = Depends(get_jwt_manager),
) -> TokenResponse:
    """
    Refresh access token.

    :param request: Refresh token.
    :type request: RefreshRequest
    :param jwt_manager: JWT manager.
    :type jwt_manager: JWTManager
    :returns: New access and refresh tokens.
    :rtype: TokenResponse
    :raises AuthError: If refresh token invalid.
    """
    result = jwt_manager.refresh_tokens(request.refresh_token)
    if not result:
        raise AuthError("Invalid or expired refresh token")

    return result


@router.get("/me", response_model=UserResponse)
async def get_current_user(
    user_id: CurrentUser,
    user_repo: PostgresUserRepository = Depends(get_user_repository),
) -> UserResponse:
    """
    Get current user information.

    :param user_id: Current user ID.
    :type user_id: str
    :param user_repo: User repository.
    :type user_repo: PostgresUserRepository
    :returns: User information.
    :rtype: UserResponse
    """
    user = await user_repo.get(user_id)
    if not user:
        raise AuthError("User not found")

    return UserResponse(
        id=str(user.id),
        email=user.email,
        name=user.full_name,
        is_active=user.is_active,
    )


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    user_id: CurrentUser,
    session_manager: SessionManager = Depends(get_session_manager),
) -> None:
    """
    Logout current user and end session.

    :param user_id: Current user ID.
    :type user_id: str
    :param session_manager: Session manager.
    :type session_manager: SessionManager
    """
    await session_manager.end_session(user_id)
    logger.info(f"User logged out: {user_id}")


@router.post("/broker/connect", response_model=BrokerAuthResponse)
async def connect_broker(
    request: BrokerAuthRequest,
    user_id: CurrentUser,
    oauth_manager: OAuthManager = Depends(get_oauth_manager),
) -> BrokerAuthResponse:
    """
    Start broker OAuth flow with user's own API credentials.

    Users provide their own Kite API key and secret. The system
    generates an OAuth URL for them to authorize.

    :param request: Broker auth request with user's API credentials.
    :type request: BrokerAuthRequest
    :param user_id: Current user ID.
    :type user_id: str
    :param oauth_manager: OAuth manager.
    :type oauth_manager: OAuthManager
    :returns: OAuth authorization URL.
    :rtype: BrokerAuthResponse
    """

    auth_url, state = await oauth_manager.start_oauth_flow(
        user_id=user_id,
        broker=request.broker,
        api_key=request.api_key,
        api_secret=request.api_secret,
    )

    return BrokerAuthResponse(
        auth_url=auth_url,
        state=state,
    )


@router.post("/broker/callback")
async def broker_callback(
    request: BrokerCallbackRequest,
    user_id: CurrentUser,
    oauth_manager: OAuthManager = Depends(get_oauth_manager),
) -> dict:
    """
    Handle broker OAuth callback.

    :param request: OAuth callback data.
    :type request: BrokerCallbackRequest
    :param user_id: Current user ID.
    :type user_id: str
    :param oauth_manager: OAuth manager.
    :type oauth_manager: OAuthManager
    :returns: Success response.
    :rtype: dict
    :raises HTTPException: If OAuth flow fails.
    """
    try:
        tokens = await oauth_manager.handle_callback(
            state=request.state,
            code=request.code,
        )

        logger.info(f"Broker {request.broker} connected for user {user_id}")

        return {"status": "connected", "broker": request.broker}

    except Exception as e:
        logger.error(f"Broker callback failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"OAuth flow failed: {str(e)}",
        )
