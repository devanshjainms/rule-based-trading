"""
OAuth authentication flow for brokers.

Handles OAuth authorization code flow with broker APIs.

:copyright: (c) 2025
:license: MIT
"""

import logging
import secrets
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from typing import Any, Dict, Optional
from urllib.parse import urlencode

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class OAuthConfig(BaseModel):
    """
    OAuth configuration model.

    :ivar client_id: OAuth client ID (API key).
    :ivar client_secret: OAuth client secret.
    :ivar redirect_uri: OAuth callback URL.
    :ivar scopes: Requested scopes.
    :ivar authorize_url: Authorization endpoint.
    :ivar token_url: Token exchange endpoint.
    """

    client_id: str
    client_secret: str
    redirect_uri: str = "http://localhost:8000/auth/callback"
    scopes: list = Field(default_factory=list)
    authorize_url: str = ""
    token_url: str = ""


class OAuthTokens(BaseModel):
    """
    OAuth tokens model.

    :ivar access_token: Access token.
    :ivar refresh_token: Refresh token.
    :ivar token_type: Token type.
    :ivar expires_in: TTL in seconds.
    :ivar expires_at: Expiration datetime.
    :ivar scope: Granted scopes.
    :ivar raw_response: Full token response.
    """

    access_token: str
    refresh_token: Optional[str] = None
    token_type: str = "Bearer"
    expires_in: Optional[int] = None
    expires_at: Optional[datetime] = None
    scope: Optional[str] = None
    raw_response: Dict[str, Any] = Field(default_factory=dict)


class OAuthState(BaseModel):
    """
    OAuth state for CSRF protection.

    :ivar state: Random state string.
    :ivar user_id: Associated user ID.
    :ivar broker_id: Target broker.
    :ivar api_key: User's API key for this broker.
    :ivar api_secret: User's API secret for this broker.
    :ivar created_at: State creation time.
    :ivar redirect_to: Post-auth redirect URL.
    """

    state: str = Field(default_factory=lambda: secrets.token_urlsafe(32))
    user_id: Optional[str] = None
    broker_id: str = ""
    api_key: Optional[str] = None
    api_secret: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    redirect_to: Optional[str] = None

    def is_expired(self, ttl_seconds: int = 600) -> bool:
        """
        Check if state has expired.

        :param ttl_seconds: State TTL.
        :type ttl_seconds: int
        :returns: True if expired.
        :rtype: bool
        """
        return datetime.utcnow() > self.created_at + timedelta(seconds=ttl_seconds)


class BaseOAuthProvider(ABC):
    """
    Abstract base class for OAuth providers.

    Implement this for each broker's OAuth flow.

    Example::

        class KiteOAuthProvider(BaseOAuthProvider):
            PROVIDER_ID = "kite"
            PROVIDER_NAME = "Kite Connect"

            def get_authorization_url(self, state: str) -> str:
                return f"https://kite.zerodha.com/connect/login?..."
    """

    PROVIDER_ID: str = "base"
    PROVIDER_NAME: str = "Base Provider"

    def __init__(self, config: OAuthConfig) -> None:
        """
        Initialize OAuth provider.

        :param config: OAuth configuration.
        :type config: OAuthConfig
        """
        self.config = config

    @abstractmethod
    def get_authorization_url(self, state: str) -> str:
        """
        Get authorization URL for redirect.

        :param state: CSRF state token.
        :type state: str
        :returns: Authorization URL.
        :rtype: str
        """

    @abstractmethod
    async def exchange_code(self, code: str) -> OAuthTokens:
        """
        Exchange authorization code for tokens.

        :param code: Authorization code.
        :type code: str
        :returns: OAuth tokens.
        :rtype: OAuthTokens
        :raises OAuthError: If exchange fails.
        """

    @abstractmethod
    async def refresh_tokens(self, refresh_token: str) -> OAuthTokens:
        """
        Refresh access token.

        :param refresh_token: Refresh token.
        :type refresh_token: str
        :returns: New tokens.
        :rtype: OAuthTokens
        :raises OAuthError: If refresh fails.
        """

    async def revoke_token(self, token: str) -> bool:
        """
        Revoke a token.

        :param token: Token to revoke.
        :type token: str
        :returns: True if revoked.
        :rtype: bool
        """

        return False


class KiteOAuthProvider(BaseOAuthProvider):
    """
    Kite Connect OAuth provider.

    Implements Zerodha Kite's OAuth flow.

    Example::

        config = OAuthConfig(
            client_id="your_api_key",
            client_secret="your_api_secret",
            redirect_uri="http://localhost:8000/auth/kite/callback"
        )
        provider = KiteOAuthProvider(config)


        url = provider.get_authorization_url(state="random_state")


        tokens = await provider.exchange_code(request_token)
    """

    PROVIDER_ID = "kite"
    PROVIDER_NAME = "Kite Connect"

    def __init__(self, config: OAuthConfig) -> None:
        """
        Initialize Kite OAuth provider.

        :param config: OAuth configuration.
        :type config: OAuthConfig
        """
        super().__init__(config)
        self.config.authorize_url = "https://kite.zerodha.com/connect/login"
        self.config.token_url = "https://api.kite.trade/session/token"

    def get_authorization_url(self, state: str) -> str:
        """
        Get Kite authorization URL.

        :param state: CSRF state token.
        :type state: str
        :returns: Authorization URL.
        :rtype: str
        """
        params = {
            "v": "3",
            "api_key": self.config.client_id,
            "redirect_uri": self.config.redirect_uri,
        }
        return f"{self.config.authorize_url}?{urlencode(params)}"

    async def exchange_code(self, code: str) -> OAuthTokens:
        """
        Exchange request token for access token.

        :param code: Request token from callback.
        :type code: str
        :returns: OAuth tokens.
        :rtype: OAuthTokens
        :raises OAuthError: If exchange fails.
        """
        import hashlib

        import httpx

        checksum = hashlib.sha256(
            f"{self.config.client_id}{code}{self.config.client_secret}".encode()
        ).hexdigest()

        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.config.token_url,
                data={
                    "api_key": self.config.client_id,
                    "request_token": code,
                    "checksum": checksum,
                },
            )

            if response.status_code != 200:
                logger.error(f"Kite token exchange failed: {response.text}")
                raise OAuthError(f"Token exchange failed: {response.status_code}")

            data = response.json()
            if data.get("status") == "error":
                raise OAuthError(data.get("message", "Unknown error"))

            return OAuthTokens(
                access_token=data["data"]["access_token"],
                refresh_token=data["data"].get("refresh_token"),
                expires_at=datetime.utcnow() + timedelta(hours=8),
                raw_response=data["data"],
            )

    async def refresh_tokens(self, refresh_token: str) -> OAuthTokens:
        """
        Refresh Kite access token.

        Note: Kite doesn't support refresh tokens in the traditional sense.
        Users must re-authenticate daily.

        :param refresh_token: Refresh token (not used).
        :type refresh_token: str
        :returns: OAuth tokens.
        :rtype: OAuthTokens
        :raises OAuthError: Always, as Kite requires re-auth.
        """
        from src.exceptions import OAuthError

        raise OAuthError("Kite requires daily re-authentication", provider="kite")


from src.exceptions import OAuthError


class OAuthManager:
    """
    OAuth flow manager.

    Manages OAuth state and coordinates with providers.

    Example::

        manager = OAuthManager()
        manager.register_provider(KiteOAuthProvider(config))


        state = manager.create_state(user_id="user123", broker_id="kite")
        url = manager.get_auth_url("kite", state.state)


        tokens = await manager.handle_callback("kite", code, state.state)
    """

    def __init__(self) -> None:
        """Initialize OAuth manager."""
        self._providers: Dict[str, BaseOAuthProvider] = {}
        self._states: Dict[str, OAuthState] = {}

    def register_provider(self, provider: BaseOAuthProvider) -> None:
        """
        Register an OAuth provider.

        :param provider: OAuth provider instance.
        :type provider: BaseOAuthProvider
        """
        self._providers[provider.PROVIDER_ID] = provider
        logger.info(f"Registered OAuth provider: {provider.PROVIDER_NAME}")

    def get_provider(self, provider_id: str) -> Optional[BaseOAuthProvider]:
        """
        Get registered provider.

        :param provider_id: Provider identifier.
        :type provider_id: str
        :returns: Provider or None.
        :rtype: Optional[BaseOAuthProvider]
        """
        return self._providers.get(provider_id)

    def create_state(
        self,
        user_id: Optional[str] = None,
        broker_id: str = "",
        redirect_to: Optional[str] = None,
    ) -> OAuthState:
        """
        Create new OAuth state.

        :param user_id: Associated user ID.
        :type user_id: Optional[str]
        :param broker_id: Target broker.
        :type broker_id: str
        :param redirect_to: Post-auth redirect.
        :type redirect_to: Optional[str]
        :returns: OAuth state.
        :rtype: OAuthState
        """
        state = OAuthState(
            user_id=user_id,
            broker_id=broker_id,
            redirect_to=redirect_to,
        )
        self._states[state.state] = state
        return state

    def verify_state(self, state: str) -> Optional[OAuthState]:
        """
        Verify and consume OAuth state.

        :param state: State string.
        :type state: str
        :returns: State object or None.
        :rtype: Optional[OAuthState]
        """
        oauth_state = self._states.pop(state, None)
        if oauth_state and not oauth_state.is_expired():
            return oauth_state
        return None

    def get_auth_url(self, provider_id: str, state: str) -> str:
        """
        Get authorization URL for provider.

        :param provider_id: Provider identifier.
        :type provider_id: str
        :param state: CSRF state token.
        :type state: str
        :returns: Authorization URL.
        :rtype: str
        :raises ValueError: If provider not found.
        """
        provider = self._providers.get(provider_id)
        if not provider:
            raise ValueError(f"Unknown provider: {provider_id}")
        return provider.get_authorization_url(state)

    async def refresh_tokens(
        self,
        provider_id: str,
        refresh_token: str,
    ) -> OAuthTokens:
        """
        Refresh tokens for provider.

        :param provider_id: Provider identifier.
        :type provider_id: str
        :param refresh_token: Refresh token.
        :type refresh_token: str
        :returns: New tokens.
        :rtype: OAuthTokens
        :raises OAuthError: If refresh fails.
        """
        provider = self._providers.get(provider_id)
        if not provider:
            raise OAuthError(f"Unknown provider: {provider_id}")
        return await provider.refresh_tokens(refresh_token)

    def cleanup_expired_states(self) -> int:
        """
        Remove expired states.

        :returns: Number of states removed.
        :rtype: int
        """
        expired = [s for s, state in self._states.items() if state.is_expired()]
        for s in expired:
            del self._states[s]
        return len(expired)

    async def start_oauth_flow(
        self,
        user_id: str,
        broker: str,
        api_key: str,
        api_secret: str,
        redirect_uri: str = "http://localhost:8000/auth/broker/callback",
    ) -> tuple[str, str]:
        """
        Start OAuth flow with user-provided credentials.

        Each user provides their own broker API credentials.
        The system stores them and initiates OAuth.

        :param user_id: User ID.
        :type user_id: str
        :param broker: Broker identifier (e.g., 'kite').
        :type broker: str
        :param api_key: User's broker API key.
        :type api_key: str
        :param api_secret: User's broker API secret.
        :type api_secret: str
        :param redirect_uri: OAuth callback URL.
        :type redirect_uri: str
        :returns: Tuple of (auth_url, state).
        :rtype: tuple[str, str]
        """

        config = OAuthConfig(
            client_id=api_key,
            client_secret=api_secret,
            redirect_uri=redirect_uri,
        )

        if broker.lower() == "kite":
            provider = KiteOAuthProvider(config)
        else:
            raise ValueError(f"Unsupported broker: {broker}")

        state = self.create_state(
            user_id=user_id,
            broker_id=broker,
        )

        state.api_key = api_key
        state.api_secret = api_secret

        self._providers[f"{broker}:{state.state}"] = provider

        auth_url = provider.get_authorization_url(state.state)

        logger.info(f"Started OAuth flow for user {user_id} with broker {broker}")

        return auth_url, state.state

    async def handle_callback(
        self,
        state: str,
        code: str,
    ) -> Optional[OAuthTokens]:
        """
        Handle OAuth callback and exchange code for tokens.

        :param state: State token from callback.
        :type state: str
        :param code: Authorization code.
        :type code: str
        :returns: OAuth tokens.
        :rtype: Optional[OAuthTokens]
        """

        oauth_state = self.verify_state(state)
        if not oauth_state:
            raise OAuthError("Invalid or expired state")

        provider_key = f"{oauth_state.broker_id}:{state}"
        provider = self._providers.pop(provider_key, None)

        if not provider:
            raise OAuthError("OAuth flow expired or invalid")

        tokens = await provider.exchange_code(code)

        await self._store_broker_credentials(
            user_id=oauth_state.user_id,
            broker_id=oauth_state.broker_id,
            api_key=getattr(oauth_state, "api_key", ""),
            api_secret=getattr(oauth_state, "api_secret", ""),
            tokens=tokens,
        )

        return tokens

    async def _store_broker_credentials(
        self,
        user_id: str,
        broker_id: str,
        api_key: str,
        api_secret: str,
        tokens: OAuthTokens,
    ) -> None:
        """
        Store user's broker credentials in database.

        Credentials are encrypted before storage.

        :param user_id: User ID.
        :type user_id: str
        :param broker_id: Broker identifier.
        :type broker_id: str
        :param api_key: Broker API key.
        :type api_key: str
        :param api_secret: Broker API secret.
        :type api_secret: str
        :param tokens: OAuth tokens.
        :type tokens: OAuthTokens
        """
        try:
            from src.database import get_database_manager
            from src.database.repositories import PostgresBrokerAccountRepository
            from src.utils.encryption import encrypt_credential

            db = get_database_manager()

            async with db.session() as session:
                repo = PostgresBrokerAccountRepository(session)

                encrypted_api_key = encrypt_credential(api_key)
                encrypted_api_secret = encrypt_credential(api_secret)
                encrypted_access_token = encrypt_credential(tokens.access_token)
                encrypted_refresh_token = (
                    encrypt_credential(tokens.refresh_token)
                    if tokens.refresh_token
                    else None
                )

                await repo.create_or_update(
                    user_id=user_id,
                    broker_id=broker_id,
                    api_key=encrypted_api_key,
                    api_secret=encrypted_api_secret,
                    access_token=encrypted_access_token,
                    refresh_token=encrypted_refresh_token,
                    token_expires_at=tokens.expires_at,
                )

            logger.info(f"Stored broker credentials for user {user_id}")

        except Exception as e:
            logger.error(f"Failed to store broker credentials: {e}")


_oauth_manager: Optional[OAuthManager] = None


def get_oauth_manager() -> OAuthManager:
    """
    Get global OAuth manager.

    :returns: OAuth manager instance.
    :rtype: OAuthManager
    """
    global _oauth_manager
    if _oauth_manager is None:
        _oauth_manager = OAuthManager()
    return _oauth_manager
