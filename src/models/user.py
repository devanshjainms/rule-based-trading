"""
User-related models.

This module contains models for user profiles, margins, and session data.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class UserProfile(BaseModel):
    """
    User profile information.

    :ivar user_id: Unique user identifier.
    :ivar user_name: Full name of the user.
    :ivar user_shortname: Short name/nickname.
    :ivar email: Email address.
    :ivar user_type: Type of user account.
    :ivar broker: Broker name.
    :ivar exchanges: List of enabled exchanges.
    :ivar products: List of enabled products.
    :ivar order_types: List of enabled order types.
    :ivar avatar_url: URL to avatar image.
    :ivar meta: Additional metadata.
    """

    user_id: str = Field(..., description="User ID")
    user_name: str = Field(..., description="User name")
    user_shortname: str = Field(default="", description="Short name")
    email: str = Field(default="", description="Email")
    user_type: str = Field(default="", description="User type")
    broker: str = Field(default="", description="Broker")
    exchanges: List[str] = Field(default_factory=list, description="Enabled exchanges")
    products: List[str] = Field(default_factory=list, description="Enabled products")
    order_types: List[str] = Field(
        default_factory=list, description="Enabled order types"
    )
    avatar_url: Optional[str] = Field(None, description="Avatar URL")
    meta: Dict[str, Any] = Field(
        default_factory=dict, description="Additional metadata"
    )

    class Config:
        """Pydantic configuration."""

        extra = "allow"


class SegmentMargin(BaseModel):
    """
    Segment-wise margin details.

    :ivar enabled: Whether the segment is enabled.
    :ivar net: Net margin.
    :ivar available: Available margin details.
    :ivar utilised: Utilised margin details.
    """

    enabled: bool = Field(default=True, description="Segment enabled")
    net: float = Field(default=0, description="Net margin")
    available: Dict[str, float] = Field(
        default_factory=dict, description="Available margin"
    )
    utilised: Dict[str, float] = Field(
        default_factory=dict, description="Utilised margin"
    )


class UserMargins(BaseModel):
    """
    User margin information across segments.

    :ivar equity: Equity segment margins.
    :ivar commodity: Commodity segment margins.
    """

    equity: Optional[SegmentMargin] = Field(None, description="Equity margins")
    commodity: Optional[SegmentMargin] = Field(None, description="Commodity margins")

    class Config:
        """Pydantic configuration."""

        extra = "allow"


class SessionData(BaseModel):
    """
    Session/login data model.

    :ivar user_id: User ID.
    :ivar user_name: User name.
    :ivar user_shortname: User short name.
    :ivar email: Email address.
    :ivar user_type: User type.
    :ivar broker: Broker name.
    :ivar access_token: Access token for API calls.
    :ivar refresh_token: Refresh token.
    :ivar public_token: Public token.
    :ivar login_time: Login timestamp.
    :ivar api_key: API key.
    """

    user_id: str = Field(..., description="User ID")
    user_name: str = Field(..., description="User name")
    user_shortname: str = Field(..., description="User short name")
    email: str = Field(..., description="Email")
    user_type: str = Field(..., description="User type")
    broker: str = Field(..., description="Broker")
    access_token: str = Field(..., description="Access token")
    refresh_token: Optional[str] = Field(None, description="Refresh token")
    public_token: Optional[str] = Field(None, description="Public token")
    login_time: Optional[datetime] = Field(None, description="Login time")
    api_key: Optional[str] = Field(None, description="API key")

    class Config:
        """Pydantic configuration."""

        extra = "allow"
