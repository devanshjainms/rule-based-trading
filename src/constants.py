"""
Constants module for Kite Connect API.

This module contains all the constants used across the trading framework
including products, order types, exchanges, validity types, and API routes.

:copyright: (c) 2025
:license: MIT
"""

DEFAULT_ROOT_URI = "https://api.kite.trade"
DEFAULT_LOGIN_URI = "https://kite.zerodha.com/connect/login"
DEFAULT_TIMEOUT = 7
KITE_HEADER_VERSION = "3"

WEBSOCKET_ROOT_URI = "wss://ws.kite.trade"
WEBSOCKET_CONNECT_TIMEOUT = 30
WEBSOCKET_RECONNECT_MAX_DELAY = 60
WEBSOCKET_RECONNECT_MAX_TRIES = 50


PRODUCT_MIS = "MIS"
"""Intraday / Margin Intraday Squareoff."""

PRODUCT_CNC = "CNC"
"""Cash and Carry for equity delivery trades."""

PRODUCT_NRML = "NRML"
"""Normal for F&O and commodity trades."""

PRODUCT_CO = "CO"
"""Cover Order."""


ORDER_TYPE_MARKET = "MARKET"
"""Market order type."""

ORDER_TYPE_LIMIT = "LIMIT"
"""Limit order type."""

ORDER_TYPE_SLM = "SL-M"
"""Stop Loss Market order type."""

ORDER_TYPE_SL = "SL"
"""Stop Loss order type."""


VARIETY_REGULAR = "regular"
"""Regular order variety."""

VARIETY_CO = "co"
"""Cover order variety."""

VARIETY_AMO = "amo"
"""After Market Order variety."""

VARIETY_ICEBERG = "iceberg"
"""Iceberg order variety."""

VARIETY_AUCTION = "auction"
"""Auction order variety."""


TRANSACTION_TYPE_BUY = "BUY"
"""Buy transaction type."""

TRANSACTION_TYPE_SELL = "SELL"
"""Sell transaction type."""


VALIDITY_DAY = "DAY"
"""Day validity - order valid for the day."""

VALIDITY_IOC = "IOC"
"""Immediate or Cancel validity."""

VALIDITY_TTL = "TTL"
"""Time to Live validity."""


POSITION_TYPE_DAY = "day"
"""Day position type."""

POSITION_TYPE_OVERNIGHT = "overnight"
"""Overnight position type."""


EXCHANGE_NSE = "NSE"
"""National Stock Exchange."""

EXCHANGE_BSE = "BSE"
"""Bombay Stock Exchange."""

EXCHANGE_NFO = "NFO"
"""NSE Futures & Options."""

EXCHANGE_CDS = "CDS"
"""Currency Derivatives Segment."""

EXCHANGE_BFO = "BFO"
"""BSE Futures & Options."""

EXCHANGE_MCX = "MCX"
"""Multi Commodity Exchange."""

EXCHANGE_BCD = "BCD"
"""BSE Currency Derivatives."""


EXCHANGE_MAP = {
    "nse": 1,
    "nfo": 2,
    "cds": 3,
    "bse": 4,
    "bfo": 5,
    "bcd": 6,
    "mcx": 7,
    "mcxsx": 8,
    "indices": 9,
}


MARGIN_EQUITY = "equity"
"""Equity margin segment."""

MARGIN_COMMODITY = "commodity"
"""Commodity margin segment."""


STATUS_COMPLETE = "COMPLETE"
"""Order completed status."""

STATUS_REJECTED = "REJECTED"
"""Order rejected status."""

STATUS_CANCELLED = "CANCELLED"
"""Order cancelled status."""

STATUS_PENDING = "PENDING"
"""Order pending status."""

STATUS_OPEN = "OPEN"
"""Order open status."""

STATUS_TRIGGER_PENDING = "TRIGGER PENDING"
"""Order trigger pending status."""


GTT_TYPE_OCO = "two-leg"
"""OCO (One Cancels Other) GTT order type."""

GTT_TYPE_SINGLE = "single"
"""Single leg GTT order type."""


GTT_STATUS_ACTIVE = "active"
"""GTT order active status."""

GTT_STATUS_TRIGGERED = "triggered"
"""GTT order triggered status."""

GTT_STATUS_DISABLED = "disabled"
"""GTT order disabled status."""

GTT_STATUS_EXPIRED = "expired"
"""GTT order expired status."""

GTT_STATUS_CANCELLED = "cancelled"
"""GTT order cancelled status."""

GTT_STATUS_REJECTED = "rejected"
"""GTT order rejected status."""

GTT_STATUS_DELETED = "deleted"
"""GTT order deleted status."""


MODE_FULL = "full"
"""Full mode - complete tick data with market depth."""

MODE_QUOTE = "quote"
"""Quote mode - OHLC, volume and other data without market depth."""

MODE_LTP = "ltp"
"""LTP mode - only last traded price."""


API_ROUTES = {
    "api.token": "/session/token",
    "api.token.invalidate": "/session/token",
    "api.token.renew": "/session/refresh_token",
    "user.profile": "/user/profile",
    "user.margins": "/user/margins",
    "user.margins.segment": "/user/margins/{segment}",
    "orders": "/orders",
    "trades": "/trades",
    "order.info": "/orders/{order_id}",
    "order.place": "/orders/{variety}",
    "order.modify": "/orders/{variety}/{order_id}",
    "order.cancel": "/orders/{variety}/{order_id}",
    "order.trades": "/orders/{order_id}/trades",
    "portfolio.positions": "/portfolio/positions",
    "portfolio.holdings": "/portfolio/holdings",
    "portfolio.holdings.auction": "/portfolio/holdings/auctions",
    "portfolio.positions.convert": "/portfolio/positions",
    "mf.orders": "/mf/orders",
    "mf.order.info": "/mf/orders/{order_id}",
    "mf.order.place": "/mf/orders",
    "mf.order.cancel": "/mf/orders/{order_id}",
    "mf.sips": "/mf/sips",
    "mf.sip.info": "/mf/sips/{sip_id}",
    "mf.sip.place": "/mf/sips",
    "mf.sip.modify": "/mf/sips/{sip_id}",
    "mf.sip.cancel": "/mf/sips/{sip_id}",
    "mf.holdings": "/mf/holdings",
    "mf.instruments": "/mf/instruments",
    "market.instruments.all": "/instruments",
    "market.instruments": "/instruments/{exchange}",
    "market.margins": "/margins/{segment}",
    "market.historical": "/instruments/historical/{instrument_token}/{interval}",
    "market.trigger_range": "/instruments/trigger_range/{transaction_type}",
    "market.quote": "/quote",
    "market.quote.ohlc": "/quote/ohlc",
    "market.quote.ltp": "/quote/ltp",
    "gtt": "/gtt/triggers",
    "gtt.place": "/gtt/triggers",
    "gtt.info": "/gtt/triggers/{trigger_id}",
    "gtt.modify": "/gtt/triggers/{trigger_id}",
    "gtt.delete": "/gtt/triggers/{trigger_id}",
    "order.margins": "/margins/orders",
    "order.margins.basket": "/margins/basket",
    "order.contract_note": "/charges/orders",
}


INTERVAL_MINUTE = "minute"
"""1 minute interval."""

INTERVAL_3MINUTE = "3minute"
"""3 minute interval."""

INTERVAL_5MINUTE = "5minute"
"""5 minute interval."""

INTERVAL_10MINUTE = "10minute"
"""10 minute interval."""

INTERVAL_15MINUTE = "15minute"
"""15 minute interval."""

INTERVAL_30MINUTE = "30minute"
"""30 minute interval."""

INTERVAL_60MINUTE = "60minute"
"""60 minute interval."""

INTERVAL_DAY = "day"
"""Daily interval."""

INTERVAL_WEEK = "week"
"""Weekly interval."""

INTERVAL_MONTH = "month"
"""Monthly interval."""


SIP_FREQUENCY_WEEKLY = "weekly"
"""Weekly SIP frequency."""

SIP_FREQUENCY_MONTHLY = "monthly"
"""Monthly SIP frequency."""

SIP_FREQUENCY_QUARTERLY = "quarterly"
"""Quarterly SIP frequency."""
