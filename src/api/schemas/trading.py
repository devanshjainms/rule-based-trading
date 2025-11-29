"""
Trading request/response schemas.

:copyright: (c) 2025
:license: MIT
"""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field

from src.models import OrderType, PositionType


class PlaceOrderRequest(BaseModel):
    """Place order request."""

    symbol: str = Field(min_length=1, max_length=20)
    quantity: int = Field(gt=0)
    order_type: OrderType = OrderType.MARKET
    position_type: PositionType = PositionType.LONG
    price: Optional[float] = Field(default=None, gt=0)
    trigger_price: Optional[float] = Field(default=None, gt=0)
    tag: Optional[str] = Field(default=None, max_length=50)


class ModifyOrderRequest(BaseModel):
    """Modify order request."""

    quantity: Optional[int] = Field(default=None, gt=0)
    price: Optional[float] = Field(default=None, gt=0)
    trigger_price: Optional[float] = Field(default=None, gt=0)


class OrderResponse(BaseModel):
    """Order response."""

    order_id: str
    symbol: str
    quantity: int
    order_type: str
    position_type: str
    status: str
    price: Optional[float]
    placed_at: datetime


class PositionResponse(BaseModel):
    """Position response."""

    symbol: str
    quantity: int
    average_price: float
    current_price: float
    pnl: float
    pnl_percent: float
    position_type: str


class TradeLogResponse(BaseModel):
    """Trade log response."""

    id: str
    symbol: str
    quantity: int
    entry_price: float
    exit_price: Optional[float]
    pnl: Optional[float]
    rule_id: Optional[str]
    entry_time: datetime
    exit_time: Optional[datetime]


class EngineStatusResponse(BaseModel):
    """Engine status response."""

    running: bool
    user_id: str
    active_trades: int = 0
    rules_loaded: int = 0
    started_at: Optional[datetime] = None
    message: Optional[str] = None


class BrokerNotConnectedResponse(BaseModel):
    """Response when broker is not connected."""

    error: str = "broker_not_connected"
    message: str = "No active broker connection. Please connect your broker first."
    action: str = "redirect_to_broker_auth"
    auth_endpoint: str = "/user/broker"
    supported_brokers: List[str] = ["kite"]
