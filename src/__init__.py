"""
KiteAPI Trading Framework.

A Python framework for trading using Zerodha Kite Connect API.

:copyright: (c) 2025
:license: MIT
"""

__version__ = "1.0.0"
__title__ = "KiteAPI"

from .client import KiteClient
from .ticker import KiteTickerClient
from .exceptions import (
    KiteException,
    TokenException,
    PermissionException,
    OrderException,
    InputException,
    DataException,
    NetworkException,
    WebSocketException,
)

__all__ = [
    "KiteClient",
    "KiteTickerClient",
    "KiteException",
    "TokenException",
    "PermissionException",
    "OrderException",
    "InputException",
    "DataException",
    "NetworkException",
    "WebSocketException",
]


def __getattr__(name: str):
    """Lazy import for module attributes."""
    if name == "KiteClient":
        from .client import KiteClient

        return KiteClient
    elif name == "KiteTickerClient":
        from .ticker import KiteTickerClient

        return KiteTickerClient
    elif name in (
        "KiteException",
        "TokenException",
        "PermissionException",
        "OrderException",
        "InputException",
        "DataException",
        "NetworkException",
        "WebSocketException",
    ):
        from . import exceptions

        return getattr(exceptions, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
