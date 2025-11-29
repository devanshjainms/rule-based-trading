"""
Order-related models.

This module contains models for order requests, order responses,
order details, GTT orders, and order results.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from src.models.enums import (
    OrderStatus,
    OrderType,
    ProductType,
    TransactionType,
    Validity,
    Variety,
)


class OrderRequest(BaseModel):
    """
    Order placement request model.

    :ivar tradingsymbol: Trading symbol.
    :ivar exchange: Exchange code.
    :ivar transaction_type: BUY or SELL.
    :ivar quantity: Order quantity.
    :ivar order_type: Order type.
    :ivar product: Product type.
    :ivar price: Order price (for LIMIT orders).
    :ivar trigger_price: Trigger price (for SL orders).
    :ivar validity: Order validity.
    :ivar variety: Order variety.
    :ivar disclosed_quantity: Disclosed quantity.
    :ivar tag: Order tag for tracking.
    :ivar iceberg_legs: Number of iceberg legs.
    :ivar iceberg_quantity: Quantity per iceberg leg.
    """

    tradingsymbol: str = Field(..., description="Trading symbol")
    exchange: str = Field(..., description="Exchange")
    transaction_type: TransactionType = Field(..., description="Transaction type")
    quantity: int = Field(..., gt=0, description="Quantity")
    order_type: OrderType = Field(default=OrderType.MARKET, description="Order type")
    product: ProductType = Field(default=ProductType.CNC, description="Product type")
    price: Optional[float] = Field(None, ge=0, description="Price")
    trigger_price: Optional[float] = Field(None, ge=0, description="Trigger price")
    validity: Validity = Field(default=Validity.DAY, description="Validity")
    variety: Variety = Field(default=Variety.REGULAR, description="Variety")
    disclosed_quantity: Optional[int] = Field(None, ge=0, description="Disclosed qty")
    tag: Optional[str] = Field(None, max_length=20, description="Order tag")
    iceberg_legs: Optional[int] = Field(None, description="Iceberg legs")
    iceberg_quantity: Optional[int] = Field(None, description="Iceberg quantity")


class Order(BaseModel):
    """
    Order details model.

    :ivar order_id: Unique order identifier.
    :ivar exchange_order_id: Exchange order ID.
    :ivar parent_order_id: Parent order ID for bracket orders.
    :ivar status: Current order status.
    :ivar status_message: Status message.
    :ivar status_message_raw: Raw status message from exchange.
    :ivar tradingsymbol: Trading symbol.
    :ivar exchange: Exchange code.
    :ivar instrument_token: Instrument token.
    :ivar transaction_type: BUY or SELL.
    :ivar order_type: Order type.
    :ivar product: Product type.
    :ivar variety: Order variety.
    :ivar validity: Order validity.
    :ivar quantity: Total quantity.
    :ivar disclosed_quantity: Disclosed quantity.
    :ivar price: Order price.
    :ivar trigger_price: Trigger price.
    :ivar average_price: Average fill price.
    :ivar filled_quantity: Filled quantity.
    :ivar pending_quantity: Pending quantity.
    :ivar cancelled_quantity: Cancelled quantity.
    :ivar order_timestamp: Order placement time.
    :ivar exchange_timestamp: Exchange acknowledgment time.
    :ivar exchange_update_timestamp: Last exchange update time.
    :ivar tag: Order tag.
    :ivar guid: Global unique ID.
    :ivar market_protection: Market protection percentage.
    :ivar meta: Additional metadata.
    """

    order_id: str = Field(..., description="Order ID")
    exchange_order_id: Optional[str] = Field(None, description="Exchange order ID")
    parent_order_id: Optional[str] = Field(None, description="Parent order ID")
    status: OrderStatus = Field(..., description="Order status")
    status_message: Optional[str] = Field(None, description="Status message")
    status_message_raw: Optional[str] = Field(None, description="Raw status message")
    tradingsymbol: str = Field(..., description="Trading symbol")
    exchange: str = Field(..., description="Exchange")
    instrument_token: Optional[int] = Field(None, description="Instrument token")
    transaction_type: TransactionType = Field(..., description="Transaction type")
    order_type: OrderType = Field(..., description="Order type")
    product: ProductType = Field(..., description="Product type")
    variety: Variety = Field(default=Variety.REGULAR, description="Variety")
    validity: Validity = Field(default=Validity.DAY, description="Validity")
    quantity: int = Field(..., description="Quantity")
    disclosed_quantity: int = Field(default=0, description="Disclosed quantity")
    price: float = Field(default=0, description="Price")
    trigger_price: float = Field(default=0, description="Trigger price")
    average_price: float = Field(default=0, description="Average price")
    filled_quantity: int = Field(default=0, description="Filled quantity")
    pending_quantity: int = Field(default=0, description="Pending quantity")
    cancelled_quantity: int = Field(default=0, description="Cancelled quantity")
    order_timestamp: Optional[datetime] = Field(None, description="Order timestamp")
    exchange_timestamp: Optional[datetime] = Field(None, description="Exchange time")
    exchange_update_timestamp: Optional[datetime] = Field(
        None, description="Exchange update time"
    )
    tag: Optional[str] = Field(None, description="Order tag")
    guid: Optional[str] = Field(None, description="GUID")
    market_protection: Optional[float] = Field(None, description="Market protection")
    meta: Dict[str, Any] = Field(default_factory=dict, description="Metadata")

    class Config:
        """Pydantic configuration."""

        extra = "allow"


class OrderResponse(BaseModel):
    """
    Order placement response model.

    :ivar order_id: The placed order ID.
    """

    order_id: str = Field(..., description="Order ID")


class OrderResult(BaseModel):
    """
    Broker-agnostic order result model.

    :ivar success: Whether the order was successful.
    :ivar order_id: Order ID if successful.
    :ivar message: Status or error message.
    :ivar raw_response: Raw broker response.
    """

    success: bool = Field(..., description="Whether order was successful")
    order_id: Optional[str] = Field(None, description="Order ID")
    message: Optional[str] = Field(None, description="Status/error message")
    raw_response: Optional[Dict[str, Any]] = Field(None, description="Raw response")


class GTTOrder(BaseModel):
    """
    GTT (Good Till Triggered) order model.

    :ivar transaction_type: BUY or SELL.
    :ivar quantity: Order quantity.
    :ivar order_type: Order type.
    :ivar product: Product type.
    :ivar price: Order price.
    """

    transaction_type: TransactionType = Field(..., description="Transaction type")
    quantity: int = Field(..., gt=0, description="Quantity")
    order_type: OrderType = Field(..., description="Order type")
    product: ProductType = Field(..., description="Product type")
    price: float = Field(..., ge=0, description="Price")


class GTT(BaseModel):
    """
    GTT trigger model.

    :ivar id: GTT trigger ID.
    :ivar user_id: User ID.
    :ivar type: GTT type (single/two-leg).
    :ivar status: GTT status.
    :ivar condition: Trigger condition.
    :ivar orders: List of GTT orders.
    :ivar created_at: Creation timestamp.
    :ivar updated_at: Last update timestamp.
    :ivar expires_at: Expiry timestamp.
    """

    id: int = Field(..., description="GTT ID")
    user_id: str = Field(..., description="User ID")
    type: str = Field(..., description="GTT type")
    status: str = Field(..., description="Status")
    condition: Dict[str, Any] = Field(..., description="Trigger condition")
    orders: List[Dict[str, Any]] = Field(default_factory=list, description="GTT orders")
    created_at: Optional[datetime] = Field(None, description="Created at")
    updated_at: Optional[datetime] = Field(None, description="Updated at")
    expires_at: Optional[datetime] = Field(None, description="Expires at")

    class Config:
        """Pydantic configuration."""

        extra = "allow"
