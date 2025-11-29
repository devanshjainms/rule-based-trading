"""
Kite Connect broker adapter.

This package provides the Kite Connect API client for Zerodha.

:copyright: (c) 2025
:license: MIT

Usage::

    from src.brokers.kite import KiteClient, KiteTickerClient, KiteAuth

    client = KiteClient(api_key="xxx", access_token="yyy")
    positions = client.positions()

    ticker = KiteTickerClient(api_key="xxx", access_token="yyy")
    ticker.on_ticks = handle_ticks
    ticker.connect()
"""

from .client import KiteClient
from .ticker import KiteTickerClient
from .auth import KiteAuth

__all__ = ["KiteClient", "KiteTickerClient", "KiteAuth"]
