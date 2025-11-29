"""
User settings API router.

Provides endpoints for user profile and broker settings management.

:copyright: (c) 2025
:license: MIT
"""

import logging
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from src.auth import CurrentUser
from src.database import get_database_manager
from src.database.models import BrokerAccount
from src.database.repositories import PostgresBrokerAccountRepository
from src.utils.encryption import encrypt_credential, decrypt_credential

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/user", tags=["User Settings"])


class BrokerCredentialsRequest(BaseModel):
    """Request to set broker API credentials."""

    broker_type: str = Field(
        description="Broker identifier (e.g., 'kite', 'upstox', 'angel')",
        examples=["kite"],
    )
    api_key: str = Field(
        description="Broker API key from developer console", min_length=1
    )
    api_secret: str = Field(
        description="Broker API secret from developer console", min_length=1
    )


class BrokerAccountResponse(BaseModel):
    """Broker account information response."""

    id: str
    broker_type: str
    api_key_masked: str = Field(description="Masked API key for display")
    is_active: bool
    is_connected: bool = Field(description="Whether OAuth flow is complete")
    token_expires_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime


class BrokerAccountListResponse(BaseModel):
    """List of broker accounts response."""

    total: int
    accounts: List[BrokerAccountResponse]


class BrokerOAuthUrlResponse(BaseModel):
    """Response with OAuth URL for broker connection."""

    auth_url: str
    state: str
    message: str = "Please complete authorization in browser"


async def get_broker_repository():
    """
    Get broker account repository instance with managed session.
    """
    db = get_database_manager()
    async with db.session() as session:
        yield PostgresBrokerAccountRepository(session)


def mask_api_key(api_key: str) -> str:
    """
    Mask API key for display.

    :param api_key: Full API key.
    :returns: Masked key showing first 4 and last 4 characters.
    """
    if len(api_key) <= 8:
        return "*" * len(api_key)
    return f"{api_key[:4]}{'*' * (len(api_key) - 8)}{api_key[-4:]}"


def broker_to_response(account: BrokerAccount) -> BrokerAccountResponse:
    """Convert BrokerAccount model to response."""

    try:
        api_key = decrypt_credential(account.api_key)
    except Exception:
        api_key = account.api_key

    return BrokerAccountResponse(
        id=account.id,
        broker_type=account.broker_id,
        api_key_masked=mask_api_key(api_key),
        is_active=account.is_active,
        is_connected=bool(account.access_token),
        token_expires_at=account.token_expires_at,
        created_at=account.created_at,
        updated_at=account.updated_at,
    )


@router.post("/broker", response_model=BrokerOAuthUrlResponse)
async def set_broker_credentials(
    request: BrokerCredentialsRequest,
    user_id: CurrentUser,
    broker_repo: PostgresBrokerAccountRepository = Depends(get_broker_repository),
) -> BrokerOAuthUrlResponse:
    """
    Set broker API credentials and get OAuth URL.

    This endpoint:
    1. Validates the broker type
    2. Encrypts and stores the API credentials
    3. Returns the OAuth authorization URL

    After calling this endpoint, redirect the user to the auth_url
    to complete the broker connection.

    :param request: Broker credentials.
    :param user_id: Current authenticated user ID.
    :param broker_repo: Broker account repository.
    :returns: OAuth authorization URL.
    :raises HTTPException: If broker type not supported.
    """

    supported_brokers = ["kite", "upstox", "angel", "fyers"]
    if request.broker_type.lower() not in supported_brokers:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported broker type. Supported: {', '.join(supported_brokers)}",
        )

    encrypted_api_key = encrypt_credential(request.api_key)
    encrypted_api_secret = encrypt_credential(request.api_secret)

    await broker_repo.create_or_update(
        user_id=user_id,
        broker_id=request.broker_type.lower(),
        api_key=encrypted_api_key,
        api_secret=encrypted_api_secret,
    )

    from src.auth import get_oauth_manager

    oauth_manager = get_oauth_manager()
    auth_url, state = await oauth_manager.start_oauth_flow(
        user_id=user_id,
        broker=request.broker_type.lower(),
        api_key=request.api_key,
        api_secret=request.api_secret,
    )

    logger.info(
        f"Broker credentials set for user {user_id}, broker {request.broker_type}"
    )

    return BrokerOAuthUrlResponse(
        auth_url=auth_url,
        state=state,
    )


@router.get("/broker", response_model=BrokerAccountListResponse)
async def list_broker_accounts(
    user_id: CurrentUser,
    broker_repo: PostgresBrokerAccountRepository = Depends(get_broker_repository),
) -> BrokerAccountListResponse:
    """
    Get all broker accounts for current user.

    :param user_id: Current authenticated user ID.
    :param broker_repo: Broker account repository.
    :returns: List of broker accounts.
    """
    accounts = await broker_repo.get_all_by_user(user_id)

    return BrokerAccountListResponse(
        total=len(accounts),
        accounts=[broker_to_response(acc) for acc in accounts],
    )


@router.get("/broker/{broker_type}", response_model=BrokerAccountResponse)
async def get_broker_account(
    broker_type: str,
    user_id: CurrentUser,
    broker_repo: PostgresBrokerAccountRepository = Depends(get_broker_repository),
) -> BrokerAccountResponse:
    """
    Get specific broker account for current user.

    :param broker_type: Broker identifier.
    :param user_id: Current authenticated user ID.
    :param broker_repo: Broker account repository.
    :returns: Broker account details.
    :raises HTTPException: If broker account not found.
    """
    account = await broker_repo.get_by_user_and_broker(user_id, broker_type.lower())

    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No {broker_type} account found for this user",
        )

    return broker_to_response(account)


@router.delete("/broker/{broker_type}", status_code=status.HTTP_204_NO_CONTENT)
async def disconnect_broker(
    broker_type: str,
    user_id: CurrentUser,
    broker_repo: PostgresBrokerAccountRepository = Depends(get_broker_repository),
) -> None:
    """
    Disconnect and remove broker account.

    This removes the broker credentials and revokes any active tokens.

    :param broker_type: Broker identifier.
    :param user_id: Current authenticated user ID.
    :param broker_repo: Broker account repository.
    :raises HTTPException: If broker account not found.
    """
    account = await broker_repo.get_by_user_and_broker(user_id, broker_type.lower())

    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No {broker_type} account found for this user",
        )

    await broker_repo.delete(account.id)

    logger.info(f"Broker {broker_type} disconnected for user {user_id}")


@router.post("/broker/{broker_type}/reconnect", response_model=BrokerOAuthUrlResponse)
async def reconnect_broker(
    broker_type: str,
    user_id: CurrentUser,
    broker_repo: PostgresBrokerAccountRepository = Depends(get_broker_repository),
) -> BrokerOAuthUrlResponse:
    """
    Reconnect to broker (refresh OAuth).

    Use this when the access token has expired and needs re-authorization.

    :param broker_type: Broker identifier.
    :param user_id: Current authenticated user ID.
    :param broker_repo: Broker account repository.
    :returns: OAuth authorization URL.
    :raises HTTPException: If broker account not found.
    """
    account = await broker_repo.get_by_user_and_broker(user_id, broker_type.lower())

    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No {broker_type} account found. Please set credentials first via POST /user/broker",
        )

    try:
        api_key = decrypt_credential(account.api_key)
        api_secret = decrypt_credential(account.api_secret)
    except Exception as e:
        logger.error(f"Failed to decrypt broker credentials: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to decrypt broker credentials",
        )

    from src.auth import get_oauth_manager

    oauth_manager = get_oauth_manager()
    auth_url, state = await oauth_manager.start_oauth_flow(
        user_id=user_id,
        broker=broker_type.lower(),
        api_key=api_key,
        api_secret=api_secret,
    )

    logger.info(f"Broker {broker_type} reconnection initiated for user {user_id}")

    return BrokerOAuthUrlResponse(
        auth_url=auth_url,
        state=state,
    )


@router.get("/broker/{broker_type}/status")
async def get_broker_status(
    broker_type: str,
    user_id: CurrentUser,
    broker_repo: PostgresBrokerAccountRepository = Depends(get_broker_repository),
) -> dict:
    """
    Get broker connection status.

    :param broker_type: Broker identifier.
    :param user_id: Current authenticated user ID.
    :param broker_repo: Broker account repository.
    :returns: Connection status.
    """
    account = await broker_repo.get_by_user_and_broker(user_id, broker_type.lower())

    if not account:
        return {
            "connected": False,
            "broker_type": broker_type,
            "message": "No broker account configured",
            "action": "POST /user/broker to set credentials",
        }

    if not account.access_token:
        return {
            "connected": False,
            "broker_type": broker_type,
            "message": "Credentials set but not connected",
            "action": "POST /user/broker/{broker_type}/reconnect to authorize",
        }

    is_expired = False
    if account.token_expires_at:
        is_expired = datetime.utcnow() > account.token_expires_at

    if is_expired:
        return {
            "connected": False,
            "broker_type": broker_type,
            "message": "Token expired",
            "expired_at": account.token_expires_at.isoformat(),
            "action": "POST /user/broker/{broker_type}/reconnect to re-authorize",
        }

    return {
        "connected": True,
        "broker_type": broker_type,
        "message": "Connected",
        "token_expires_at": (
            account.token_expires_at.isoformat() if account.token_expires_at else None
        ),
    }
