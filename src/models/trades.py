"""
Trade execution models.

This module contains models for trade records and executions.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from src.models.enums import ProductType, TransactionType


class Trade(BaseModel):
    """
    Trade execution model.

    :ivar trade_id: Unique trade identifier.
    :ivar order_id: Associated order ID.
    :ivar exchange_order_id: Exchange order ID.
    :ivar tradingsymbol: Trading symbol.
    :ivar exchange: Exchange code.
    :ivar instrument_token: Instrument token.
    :ivar transaction_type: BUY or SELL.
    :ivar product: Product type.
    :ivar quantity: Trade quantity.
    :ivar price: Trade price.
    :ivar average_price: Average price.
    :ivar fill_timestamp: Fill timestamp.
    :ivar exchange_timestamp: Exchange timestamp.
    :ivar order_timestamp: Order timestamp.
    """

    trade_id: str = Field(..., description="Trade ID")
    order_id: str = Field(..., description="Order ID")
    exchange_order_id: Optional[str] = Field(None, description="Exchange order ID")
    tradingsymbol: str = Field(..., description="Trading symbol")
    exchange: str = Field(..., description="Exchange")
    instrument_token: Optional[int] = Field(None, description="Instrument token")
    transaction_type: TransactionType = Field(..., description="Transaction type")
    product: ProductType = Field(..., description="Product type")
    quantity: int = Field(..., description="Quantity")
    price: float = Field(..., description="Price")
    average_price: float = Field(default=0, description="Average price")
    fill_timestamp: Optional[datetime] = Field(None, description="Fill timestamp")
    exchange_timestamp: Optional[datetime] = Field(None, description="Exchange time")
    order_timestamp: Optional[datetime] = Field(None, description="Order timestamp")

    class Config:
        """Pydantic configuration."""

        extra = "allow"
