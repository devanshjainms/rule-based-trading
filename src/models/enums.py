"""
Enumeration types for the trading system.

This module contains all enum definitions used across the trading platform,
including order types, product types, exchanges, and status codes.
"""

from enum import Enum


class Exchange(str, Enum):
    """
    Exchange codes supported by the trading system.

    :cvar NSE: National Stock Exchange.
    :cvar BSE: Bombay Stock Exchange.
    :cvar NFO: NSE Futures & Options.
    :cvar BFO: BSE Futures & Options.
    :cvar CDS: Currency Derivatives Segment.
    :cvar BCD: BSE Currency Derivatives.
    :cvar MCX: Multi Commodity Exchange.
    """

    NSE = "NSE"
    BSE = "BSE"
    NFO = "NFO"
    BFO = "BFO"
    CDS = "CDS"
    BCD = "BCD"
    MCX = "MCX"


class ProductType(str, Enum):
    """
    Product/position types for orders.

    :cvar CNC: Cash and Carry (delivery).
    :cvar NRML: Normal (F&O overnight).
    :cvar MIS: Margin Intraday Square-off.
    :cvar INTRADAY: Alias for MIS.
    :cvar DELIVERY: Alias for CNC.
    :cvar MARGIN: Alias for NRML.
    """

    CNC = "CNC"
    NRML = "NRML"
    MIS = "MIS"
    INTRADAY = "INTRADAY"
    DELIVERY = "DELIVERY"
    MARGIN = "MARGIN"


class PositionType(str, Enum):
    """
    Position type (direction).

    :cvar LONG: Long position (buy).
    :cvar SHORT: Short position (sell).
    """

    LONG = "LONG"
    SHORT = "SHORT"


class OrderType(str, Enum):
    """
    Order types supported by the trading system.

    :cvar MARKET: Market order.
    :cvar LIMIT: Limit order.
    :cvar SL: Stop-loss order.
    :cvar SL_M: Stop-loss market order.
    :cvar STOP_LOSS: Alias for SL.
    :cvar STOP_LOSS_MARKET: Alias for SL_M.
    """

    MARKET = "MARKET"
    LIMIT = "LIMIT"
    SL = "SL"
    SL_M = "SL-M"
    STOP_LOSS = "STOP_LOSS"
    STOP_LOSS_MARKET = "STOP_LOSS_MARKET"


class TransactionType(str, Enum):
    """
    Transaction type for orders.

    :cvar BUY: Buy transaction.
    :cvar SELL: Sell transaction.
    """

    BUY = "BUY"
    SELL = "SELL"


class OrderSide(str, Enum):
    """
    Order side (broker-agnostic version of TransactionType).

    :cvar BUY: Buy side.
    :cvar SELL: Sell side.
    """

    BUY = "BUY"
    SELL = "SELL"


class Variety(str, Enum):
    """
    Order variety types.

    :cvar REGULAR: Regular order.
    :cvar AMO: After Market Order.
    :cvar CO: Cover Order.
    :cvar ICEBERG: Iceberg order.
    :cvar AUCTION: Auction order.
    """

    REGULAR = "regular"
    AMO = "amo"
    CO = "co"
    ICEBERG = "iceberg"
    AUCTION = "auction"


class Validity(str, Enum):
    """
    Order validity types.

    :cvar DAY: Valid for the day.
    :cvar IOC: Immediate or Cancel.
    :cvar TTL: Time to Live (GTT).
    """

    DAY = "DAY"
    IOC = "IOC"
    TTL = "TTL"


class OrderStatus(str, Enum):
    """
    Order status codes.

    :cvar PENDING: Order pending.
    :cvar OPEN: Order open.
    :cvar COMPLETE: Order completed.
    :cvar CANCELLED: Order cancelled.
    :cvar REJECTED: Order rejected.
    :cvar TRIGGER_PENDING: Trigger pending for SL orders.
    :cvar FILLED: Order fully filled.
    :cvar PARTIALLY_FILLED: Order partially filled.
    :cvar FAILED: Order failed.
    """

    PENDING = "PENDING"
    OPEN = "OPEN"
    COMPLETE = "COMPLETE"
    CANCELLED = "CANCELLED"
    REJECTED = "REJECTED"
    TRIGGER_PENDING = "TRIGGER PENDING"
    FILLED = "FILLED"
    PARTIALLY_FILLED = "PARTIALLY_FILLED"
    FAILED = "FAILED"
