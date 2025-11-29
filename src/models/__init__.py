"""
Models package for rule-based trading system.

This package contains all Pydantic models organized by domain:
- enums: All enumeration types
- user: User profile and session models
- orders: Order-related models
- positions: Position and holding models
- market: Market data models (quotes, ticks, instruments)
- trades: Trade execution models
"""

from src.models.enums import (
    Exchange,
    OrderSide,
    OrderStatus,
    OrderType,
    PositionType,
    ProductType,
    TransactionType,
    Validity,
    Variety,
)
from src.models.market import (
    HistoricalData,
    Instrument,
    MarketDepth,
    MarketDepthItem,
    OHLC,
    Quote,
    Tick,
)
from src.models.orders import (
    GTT,
    GTTOrder,
    Order,
    OrderRequest,
    OrderResponse,
    OrderResult,
)
from src.models.positions import Holding, Position
from src.models.trades import Trade
from src.models.user import SessionData, UserMargins, UserProfile

__all__ = [
    "Exchange",
    "OrderSide",
    "OrderStatus",
    "OrderType",
    "PositionType",
    "ProductType",
    "TransactionType",
    "Validity",
    "Variety",
    "UserProfile",
    "UserMargins",
    "SessionData",
    "Order",
    "OrderRequest",
    "OrderResponse",
    "OrderResult",
    "GTT",
    "GTTOrder",
    "Position",
    "Holding",
    "OHLC",
    "Quote",
    "Tick",
    "MarketDepth",
    "MarketDepthItem",
    "Instrument",
    "HistoricalData",
    "Trade",
]
