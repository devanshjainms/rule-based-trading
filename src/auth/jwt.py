"""
JWT authentication utilities.

Handles JWT token generation, validation, and refresh for API authentication.

:copyright: (c) 2025
:license: MIT
"""

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

import bcrypt
from jose import JWTError, jwt
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class JWTConfig:
    """
    JWT configuration.

    :ivar secret_key: Secret key for signing tokens.
    :ivar algorithm: JWT algorithm (default: HS256).
    :ivar access_token_expire_minutes: Access token TTL.
    :ivar refresh_token_expire_days: Refresh token TTL.
    :ivar issuer: Token issuer.
    :ivar audience: Token audience.
    """

    def __init__(
        self,
        secret_key: str = "your-super-secret-key-change-in-production",
        algorithm: str = "HS256",
        access_token_expire_minutes: int = 30,
        refresh_token_expire_days: int = 7,
        issuer: str = "trading-api",
        audience: str = "trading-client",
    ) -> None:
        """
        Initialize JWT configuration.

        :param secret_key: Signing secret.
        :type secret_key: str
        :param algorithm: JWT algorithm.
        :type algorithm: str
        :param access_token_expire_minutes: Access token TTL.
        :type access_token_expire_minutes: int
        :param refresh_token_expire_days: Refresh token TTL.
        :type refresh_token_expire_days: int
        :param issuer: Token issuer.
        :type issuer: str
        :param audience: Token audience.
        :type audience: str
        """
        self.secret_key = secret_key
        self.algorithm = algorithm
        self.access_token_expire_minutes = access_token_expire_minutes
        self.refresh_token_expire_days = refresh_token_expire_days
        self.issuer = issuer
        self.audience = audience


class TokenPayload(BaseModel):
    """
    JWT token payload model.

    :ivar sub: Subject (user ID).
    :ivar exp: Expiration timestamp.
    :ivar iat: Issued at timestamp.
    :ivar type: Token type (access/refresh).
    :ivar jti: JWT ID (unique token identifier).
    :ivar iss: Issuer.
    :ivar aud: Audience.
    """

    sub: str = Field(..., description="Subject (user ID)")
    exp: datetime = Field(..., description="Expiration time")
    iat: datetime = Field(default_factory=datetime.utcnow, description="Issued at")
    type: str = Field(default="access", description="Token type")
    jti: Optional[str] = Field(None, description="JWT ID")
    iss: Optional[str] = Field(None, description="Issuer")
    aud: Optional[str] = Field(None, description="Audience")
    data: Dict[str, Any] = Field(default_factory=dict, description="Custom claims")


class TokenResponse(BaseModel):
    """
    Token response model.

    :ivar access_token: JWT access token.
    :ivar refresh_token: JWT refresh token.
    :ivar token_type: Token type (Bearer).
    :ivar expires_in: Access token TTL in seconds.
    """

    access_token: str
    refresh_token: Optional[str] = None
    token_type: str = "Bearer"
    expires_in: int


class JWTManager:
    """
    JWT token manager.

    Handles token creation, validation, and refresh.

    Example::

        jwt_mgr = JWTManager(config)


        tokens = jwt_mgr.create_tokens(user_id="user123")


        payload = jwt_mgr.verify_token(tokens.access_token)


        new_tokens = jwt_mgr.refresh_tokens(tokens.refresh_token)
    """

    def __init__(self, config: Optional[JWTConfig] = None) -> None:
        """
        Initialize JWT manager.

        :param config: JWT configuration.
        :type config: Optional[JWTConfig]
        """
        self.config = config or JWTConfig()

    def create_access_token(
        self,
        user_id: str,
        data: Optional[Dict[str, Any]] = None,
        expires_delta: Optional[timedelta] = None,
    ) -> str:
        """
        Create access token.

        :param user_id: User identifier.
        :type user_id: str
        :param data: Additional claims.
        :type data: Optional[Dict[str, Any]]
        :param expires_delta: Custom expiration.
        :type expires_delta: Optional[timedelta]
        :returns: JWT access token.
        :rtype: str
        """
        expires_delta = expires_delta or timedelta(
            minutes=self.config.access_token_expire_minutes
        )
        expire = datetime.utcnow() + expires_delta

        payload = {
            "sub": user_id,
            "exp": expire,
            "iat": datetime.utcnow(),
            "type": "access",
            "iss": self.config.issuer,
            "aud": self.config.audience,
        }
        if data:
            payload["data"] = data

        return jwt.encode(
            payload, self.config.secret_key, algorithm=self.config.algorithm
        )

    def create_refresh_token(
        self,
        user_id: str,
        expires_delta: Optional[timedelta] = None,
    ) -> str:
        """
        Create refresh token.

        :param user_id: User identifier.
        :type user_id: str
        :param expires_delta: Custom expiration.
        :type expires_delta: Optional[timedelta]
        :returns: JWT refresh token.
        :rtype: str
        """
        expires_delta = expires_delta or timedelta(
            days=self.config.refresh_token_expire_days
        )
        expire = datetime.utcnow() + expires_delta

        payload = {
            "sub": user_id,
            "exp": expire,
            "iat": datetime.utcnow(),
            "type": "refresh",
            "iss": self.config.issuer,
            "aud": self.config.audience,
        }

        return jwt.encode(
            payload, self.config.secret_key, algorithm=self.config.algorithm
        )

    def create_tokens(
        self,
        user_id: str,
        data: Optional[Dict[str, Any]] = None,
    ) -> TokenResponse:
        """
        Create both access and refresh tokens.

        :param user_id: User identifier.
        :type user_id: str
        :param data: Additional claims for access token.
        :type data: Optional[Dict[str, Any]]
        :returns: Token response with both tokens.
        :rtype: TokenResponse
        """
        access_token = self.create_access_token(user_id, data)
        refresh_token = self.create_refresh_token(user_id)

        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="Bearer",
            expires_in=self.config.access_token_expire_minutes * 60,
        )

    def verify_token(
        self,
        token: str,
        token_type: str = "access",
    ) -> Optional[TokenPayload]:
        """
        Verify and decode JWT token.

        :param token: JWT token string.
        :type token: str
        :param token_type: Expected token type.
        :type token_type: str
        :returns: Token payload or None if invalid.
        :rtype: Optional[TokenPayload]
        """
        try:
            payload = jwt.decode(
                token,
                self.config.secret_key,
                algorithms=[self.config.algorithm],
                audience=self.config.audience,
                issuer=self.config.issuer,
            )

            if payload.get("type") != token_type:
                logger.warning(f"Token type mismatch: expected {token_type}")
                return None

            return TokenPayload(
                sub=payload["sub"],
                exp=datetime.fromtimestamp(payload["exp"]),
                iat=datetime.fromtimestamp(payload["iat"]),
                type=payload.get("type", "access"),
                iss=payload.get("iss"),
                aud=payload.get("aud"),
                data=payload.get("data", {}),
            )

        except JWTError as e:
            logger.warning(f"JWT verification failed: {e}")
            return None

    def refresh_tokens(self, refresh_token: str) -> Optional[TokenResponse]:
        """
        Refresh access token using refresh token.

        :param refresh_token: Valid refresh token.
        :type refresh_token: str
        :returns: New token response or None if invalid.
        :rtype: Optional[TokenResponse]
        """
        payload = self.verify_token(refresh_token, token_type="refresh")
        if not payload:
            return None

        return self.create_tokens(payload.sub)

    def get_user_id(self, token: str) -> Optional[str]:
        """
        Extract user ID from token.

        :param token: JWT token.
        :type token: str
        :returns: User ID or None.
        :rtype: Optional[str]
        """
        payload = self.verify_token(token)
        return payload.sub if payload else None

    def hash_password(self, password: str) -> str:
        """
        Hash a password using bcrypt.

        :param password: Plain text password.
        :type password: str
        :returns: Hashed password.
        :rtype: str
        """
        salt = bcrypt.gensalt()
        return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """
        Verify password against hash.

        :param plain_password: Plain text password.
        :type plain_password: str
        :param hashed_password: Hashed password.
        :type hashed_password: str
        :returns: True if password matches.
        :rtype: bool
        """
        return bcrypt.checkpw(
            plain_password.encode("utf-8"), hashed_password.encode("utf-8")
        )


def hash_password(password: str) -> str:
    """
    Hash a password using bcrypt.

    :param password: Plain text password.
    :type password: str
    :returns: Hashed password.
    :rtype: str
    """
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify password against hash.

    :param plain_password: Plain text password.
    :type plain_password: str
    :param hashed_password: Hashed password.
    :type hashed_password: str
    :returns: True if password matches.
    :rtype: bool
    """
    return bcrypt.checkpw(
        plain_password.encode("utf-8"), hashed_password.encode("utf-8")
    )


_jwt_manager: Optional[JWTManager] = None


def get_jwt_manager() -> JWTManager:
    """
    Get global JWT manager.

    :returns: JWT manager instance.
    :rtype: JWTManager
    """
    global _jwt_manager
    if _jwt_manager is None:
        _jwt_manager = JWTManager()
    return _jwt_manager


def configure_jwt(config: JWTConfig) -> JWTManager:
    """
    Configure global JWT manager.

    :param config: JWT configuration.
    :type config: JWTConfig
    :returns: Configured manager.
    :rtype: JWTManager
    """
    global _jwt_manager
    _jwt_manager = JWTManager(config)
    return _jwt_manager
