"""
Broker abstraction layer.

This package provides trading broker implementations. Currently supports
Kite Connect (Zerodha). The architecture is extensible for adding
other brokers (Webull, Robinhood, Alpaca, etc.) in the future.

:copyright: (c) 2025
:license: MIT

Usage::

    from src.brokers.kite import KiteClient, KiteTickerClient, KiteAuth


    client = KiteClient(api_key="xxx", access_token="yyy")
    positions = client.positions()


    auth = KiteAuth()
    client = auth.get_client()
"""

from .base import BaseBroker, BaseTicker
from src.models import (
    Order,
    OrderResult,
    OrderSide,
    OrderStatus,
    OrderType,
    Position,
    ProductType,
    Quote,
    Trade,
    UserProfile,
)

__all__ = [
    "BaseBroker",
    "BaseTicker",
    "Position",
    "Order",
    "OrderResult",
    "Quote",
    "Trade",
    "UserProfile",
    "OrderSide",
    "OrderType",
    "OrderStatus",
    "ProductType",
]
