"""
Data models for Kite Connect API.

This module defines Pydantic models for all data structures used
in the Kite Connect API including orders, positions, holdings,
quotes, and user data.

:copyright: (c) 2025
:license: MIT
"""

from datetime import datetime, date
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from enum import Enum


class ProductType(str, Enum):
    """
    Product type enumeration for orders.

    :cvar MIS: Intraday / Margin Intraday Squareoff.
    :cvar CNC: Cash and Carry for equity delivery trades.
    :cvar NRML: Normal for F&O and commodity trades.
    :cvar CO: Cover Order.
    """

    MIS = "MIS"
    CNC = "CNC"
    NRML = "NRML"
    CO = "CO"


class OrderType(str, Enum):
    """
    Order type enumeration.

    :cvar MARKET: Market order.
    :cvar LIMIT: Limit order.
    :cvar SL: Stop Loss order.
    :cvar SL_M: Stop Loss Market order.
    """

    MARKET = "MARKET"
    LIMIT = "LIMIT"
    SL = "SL"
    SL_M = "SL-M"


class TransactionType(str, Enum):
    """
    Transaction type enumeration.

    :cvar BUY: Buy transaction.
    :cvar SELL: Sell transaction.
    """

    BUY = "BUY"
    SELL = "SELL"


class Variety(str, Enum):
    """
    Order variety enumeration.

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


class Exchange(str, Enum):
    """
    Exchange enumeration.

    :cvar NSE: National Stock Exchange.
    :cvar BSE: Bombay Stock Exchange.
    :cvar NFO: NSE Futures & Options.
    :cvar CDS: Currency Derivatives Segment.
    :cvar BFO: BSE Futures & Options.
    :cvar MCX: Multi Commodity Exchange.
    :cvar BCD: BSE Currency Derivatives.
    """

    NSE = "NSE"
    BSE = "BSE"
    NFO = "NFO"
    CDS = "CDS"
    BFO = "BFO"
    MCX = "MCX"
    BCD = "BCD"


class Validity(str, Enum):
    """
    Order validity enumeration.

    :cvar DAY: Day validity.
    :cvar IOC: Immediate or Cancel.
    :cvar TTL: Time to Live.
    """

    DAY = "DAY"
    IOC = "IOC"
    TTL = "TTL"


class OrderStatus(str, Enum):
    """
    Order status enumeration.

    :cvar COMPLETE: Order completed.
    :cvar REJECTED: Order rejected.
    :cvar CANCELLED: Order cancelled.
    :cvar PENDING: Order pending.
    :cvar OPEN: Order open.
    :cvar TRIGGER_PENDING: Trigger pending.
    """

    COMPLETE = "COMPLETE"
    REJECTED = "REJECTED"
    CANCELLED = "CANCELLED"
    PENDING = "PENDING"
    OPEN = "OPEN"
    TRIGGER_PENDING = "TRIGGER PENDING"


class UserProfile(BaseModel):
    """
    User profile model.

    :ivar user_id: The unique user ID.
    :ivar user_name: The user's full name.
    :ivar user_shortname: The user's short name.
    :ivar email: The user's email address.
    :ivar user_type: The type of user account.
    :ivar broker: The broker name.
    :ivar exchanges: List of enabled exchanges.
    :ivar products: List of enabled products.
    :ivar order_types: List of enabled order types.
    :ivar avatar_url: URL to user's avatar image.
    """

    user_id: str = Field(..., description="The unique user ID")
    user_name: str = Field(..., description="The user's full name")
    user_shortname: str = Field(..., description="The user's short name")
    email: str = Field(..., description="The user's email address")
    user_type: str = Field(..., description="The type of user account")
    broker: str = Field(..., description="The broker name")
    exchanges: List[str] = Field(
        default_factory=list, description="List of enabled exchanges"
    )
    products: List[str] = Field(
        default_factory=list, description="List of enabled products"
    )
    order_types: List[str] = Field(
        default_factory=list, description="List of enabled order types"
    )
    avatar_url: Optional[str] = Field(None, description="URL to user's avatar image")

    class Config:
        """Pydantic configuration."""

        extra = "allow"


class UserMargins(BaseModel):
    """
    User margin details model.

    :ivar enabled: Whether margin trading is enabled.
    :ivar net: Net available margin.
    :ivar available: Available margin details.
    :ivar utilised: Utilised margin details.
    """

    enabled: bool = Field(..., description="Whether margin trading is enabled")
    net: float = Field(..., description="Net available margin")
    available: Dict[str, float] = Field(
        default_factory=dict, description="Available margin details"
    )
    utilised: Dict[str, float] = Field(
        default_factory=dict, description="Utilised margin details"
    )

    class Config:
        """Pydantic configuration."""

        extra = "allow"


class OrderRequest(BaseModel):
    """
    Order placement request model.

    :ivar tradingsymbol: The trading symbol of the instrument.
    :ivar exchange: The exchange to place order on.
    :ivar transaction_type: BUY or SELL.
    :ivar quantity: Number of shares/units.
    :ivar product: Product type (MIS, CNC, NRML).
    :ivar order_type: Order type (MARKET, LIMIT, SL, SL-M).
    :ivar price: Price for LIMIT orders.
    :ivar trigger_price: Trigger price for SL orders.
    :ivar validity: Order validity (DAY, IOC).
    :ivar disclosed_quantity: Disclosed quantity.
    :ivar tag: Optional tag for the order.
    """

    tradingsymbol: str = Field(..., description="Trading symbol")
    exchange: Exchange = Field(..., description="Exchange")
    transaction_type: TransactionType = Field(..., description="BUY or SELL")
    quantity: int = Field(..., gt=0, description="Quantity")
    product: ProductType = Field(..., description="Product type")
    order_type: OrderType = Field(..., description="Order type")
    price: Optional[float] = Field(None, ge=0, description="Price for LIMIT")
    trigger_price: Optional[float] = Field(None, ge=0, description="Trigger price")
    validity: Validity = Field(default=Validity.DAY, description="Order validity")
    variety: Variety = Field(default=Variety.REGULAR, description="Order variety")
    disclosed_quantity: Optional[int] = Field(
        None, ge=0, description="Disclosed quantity"
    )
    validity_ttl: Optional[int] = Field(None, description="TTL validity minutes")
    iceberg_legs: Optional[int] = Field(None, description="Iceberg legs")
    iceberg_quantity: Optional[int] = Field(None, description="Iceberg quantity")
    tag: Optional[str] = Field(None, max_length=20, description="Order tag")


class Order(BaseModel):
    """
    Order details model.

    :ivar order_id: Unique order identifier.
    :ivar exchange_order_id: Exchange order identifier.
    :ivar parent_order_id: Parent order ID for bracket orders.
    :ivar status: Current order status.
    :ivar tradingsymbol: Trading symbol.
    :ivar exchange: Exchange name.
    :ivar transaction_type: BUY or SELL.
    :ivar order_type: Order type.
    :ivar product: Product type.
    :ivar validity: Order validity.
    :ivar quantity: Order quantity.
    :ivar disclosed_quantity: Disclosed quantity.
    :ivar price: Order price.
    :ivar trigger_price: Trigger price.
    :ivar average_price: Average fill price.
    :ivar filled_quantity: Filled quantity.
    :ivar pending_quantity: Pending quantity.
    :ivar cancelled_quantity: Cancelled quantity.
    :ivar order_timestamp: Order placement timestamp.
    :ivar exchange_timestamp: Exchange timestamp.
    :ivar status_message: Status message from exchange.
    :ivar tag: Order tag.
    """

    order_id: str = Field(..., description="Order ID")
    exchange_order_id: Optional[str] = Field(None, description="Exchange order ID")
    parent_order_id: Optional[str] = Field(None, description="Parent order ID")
    status: str = Field(..., description="Order status")
    tradingsymbol: str = Field(..., description="Trading symbol")
    exchange: str = Field(..., description="Exchange")
    transaction_type: str = Field(..., description="Transaction type")
    order_type: str = Field(..., description="Order type")
    product: str = Field(..., description="Product type")
    validity: str = Field(..., description="Validity")
    quantity: int = Field(..., description="Quantity")
    disclosed_quantity: int = Field(default=0, description="Disclosed quantity")
    price: float = Field(default=0, description="Price")
    trigger_price: float = Field(default=0, description="Trigger price")
    average_price: float = Field(default=0, description="Average price")
    filled_quantity: int = Field(default=0, description="Filled quantity")
    pending_quantity: int = Field(default=0, description="Pending quantity")
    cancelled_quantity: int = Field(default=0, description="Cancelled quantity")
    order_timestamp: Optional[datetime] = Field(None, description="Order timestamp")
    exchange_timestamp: Optional[datetime] = Field(
        None, description="Exchange timestamp"
    )
    status_message: Optional[str] = Field(None, description="Status message")
    tag: Optional[str] = Field(None, description="Order tag")
    variety: str = Field(default="regular", description="Order variety")

    class Config:
        """Pydantic configuration."""

        extra = "allow"


class Trade(BaseModel):
    """
    Trade details model.

    :ivar trade_id: Unique trade identifier.
    :ivar order_id: Associated order ID.
    :ivar exchange_order_id: Exchange order ID.
    :ivar tradingsymbol: Trading symbol.
    :ivar exchange: Exchange name.
    :ivar transaction_type: BUY or SELL.
    :ivar product: Product type.
    :ivar quantity: Trade quantity.
    :ivar price: Trade price.
    :ivar fill_timestamp: Fill timestamp.
    """

    trade_id: str = Field(..., description="Trade ID")
    order_id: str = Field(..., description="Order ID")
    exchange_order_id: Optional[str] = Field(None, description="Exchange order ID")
    tradingsymbol: str = Field(..., description="Trading symbol")
    exchange: str = Field(..., description="Exchange")
    transaction_type: str = Field(..., description="Transaction type")
    product: str = Field(..., description="Product type")
    quantity: int = Field(..., description="Quantity")
    price: float = Field(..., description="Price")
    fill_timestamp: Optional[datetime] = Field(None, description="Fill timestamp")

    class Config:
        """Pydantic configuration."""

        extra = "allow"


class Position(BaseModel):
    """
    Position details model.

    :ivar tradingsymbol: Trading symbol.
    :ivar exchange: Exchange name.
    :ivar product: Product type.
    :ivar quantity: Net quantity.
    :ivar overnight_quantity: Overnight quantity.
    :ivar multiplier: Contract multiplier.
    :ivar average_price: Average price.
    :ivar close_price: Closing price.
    :ivar last_price: Last traded price.
    :ivar value: Position value.
    :ivar pnl: Profit/Loss.
    :ivar m2m: Mark to market.
    :ivar unrealised: Unrealised P&L.
    :ivar realised: Realised P&L.
    :ivar buy_quantity: Buy quantity.
    :ivar buy_price: Average buy price.
    :ivar buy_value: Total buy value.
    :ivar sell_quantity: Sell quantity.
    :ivar sell_price: Average sell price.
    :ivar sell_value: Total sell value.
    :ivar day_buy_quantity: Day buy quantity.
    :ivar day_buy_price: Day buy price.
    :ivar day_buy_value: Day buy value.
    :ivar day_sell_quantity: Day sell quantity.
    :ivar day_sell_price: Day sell price.
    :ivar day_sell_value: Day sell value.
    """

    tradingsymbol: str = Field(..., description="Trading symbol")
    exchange: str = Field(..., description="Exchange")
    product: str = Field(..., description="Product type")
    quantity: int = Field(default=0, description="Net quantity")
    overnight_quantity: int = Field(default=0, description="Overnight quantity")
    multiplier: float = Field(default=1, description="Multiplier")
    average_price: float = Field(default=0, description="Average price")
    close_price: float = Field(default=0, description="Close price")
    last_price: float = Field(default=0, description="Last price")
    value: float = Field(default=0, description="Value")
    pnl: float = Field(default=0, description="P&L")
    m2m: float = Field(default=0, description="M2M")
    unrealised: float = Field(default=0, description="Unrealised P&L")
    realised: float = Field(default=0, description="Realised P&L")
    buy_quantity: int = Field(default=0, description="Buy quantity")
    buy_price: float = Field(default=0, description="Buy price")
    buy_value: float = Field(default=0, description="Buy value")
    sell_quantity: int = Field(default=0, description="Sell quantity")
    sell_price: float = Field(default=0, description="Sell price")
    sell_value: float = Field(default=0, description="Sell value")
    day_buy_quantity: int = Field(default=0, description="Day buy quantity")
    day_buy_price: float = Field(default=0, description="Day buy price")
    day_buy_value: float = Field(default=0, description="Day buy value")
    day_sell_quantity: int = Field(default=0, description="Day sell quantity")
    day_sell_price: float = Field(default=0, description="Day sell price")
    day_sell_value: float = Field(default=0, description="Day sell value")

    class Config:
        """Pydantic configuration."""

        extra = "allow"


class Holding(BaseModel):
    """
    Holdings details model.

    :ivar tradingsymbol: Trading symbol.
    :ivar exchange: Exchange name.
    :ivar isin: ISIN code.
    :ivar quantity: Quantity held.
    :ivar t1_quantity: T+1 quantity.
    :ivar average_price: Average buy price.
    :ivar last_price: Last traded price.
    :ivar close_price: Previous close price.
    :ivar pnl: Profit/Loss.
    :ivar day_change: Day change value.
    :ivar day_change_percentage: Day change percentage.
    :ivar collateral_quantity: Collateral quantity.
    :ivar collateral_type: Type of collateral.
    """

    tradingsymbol: str = Field(..., description="Trading symbol")
    exchange: str = Field(..., description="Exchange")
    isin: str = Field(..., description="ISIN code")
    quantity: int = Field(default=0, description="Quantity")
    t1_quantity: int = Field(default=0, description="T+1 quantity")
    average_price: float = Field(default=0, description="Average price")
    last_price: float = Field(default=0, description="Last price")
    close_price: float = Field(default=0, description="Close price")
    pnl: float = Field(default=0, description="P&L")
    day_change: float = Field(default=0, description="Day change")
    day_change_percentage: float = Field(default=0, description="Day change %")
    collateral_quantity: int = Field(default=0, description="Collateral quantity")
    collateral_type: Optional[str] = Field(None, description="Collateral type")

    class Config:
        """Pydantic configuration."""

        extra = "allow"


class OHLC(BaseModel):
    """
    OHLC (Open, High, Low, Close) data model.

    :ivar open: Opening price.
    :ivar high: High price.
    :ivar low: Low price.
    :ivar close: Closing price.
    """

    open: float = Field(..., description="Open price")
    high: float = Field(..., description="High price")
    low: float = Field(..., description="Low price")
    close: float = Field(..., description="Close price")


class MarketDepthItem(BaseModel):
    """
    Market depth item model.

    :ivar price: Price level.
    :ivar quantity: Quantity at price level.
    :ivar orders: Number of orders.
    """

    price: float = Field(..., description="Price")
    quantity: int = Field(..., description="Quantity")
    orders: int = Field(..., description="Orders")


class MarketDepth(BaseModel):
    """
    Market depth model with buy and sell sides.

    :ivar buy: List of buy depth items.
    :ivar sell: List of sell depth items.
    """

    buy: List[MarketDepthItem] = Field(default_factory=list, description="Buy depth")
    sell: List[MarketDepthItem] = Field(default_factory=list, description="Sell depth")


class Quote(BaseModel):
    """
    Quote data model.

    :ivar instrument_token: Instrument token.
    :ivar timestamp: Quote timestamp.
    :ivar last_price: Last traded price.
    :ivar last_quantity: Last traded quantity.
    :ivar last_trade_time: Last trade timestamp.
    :ivar average_price: Average traded price.
    :ivar volume: Total volume traded.
    :ivar buy_quantity: Total buy quantity.
    :ivar sell_quantity: Total sell quantity.
    :ivar ohlc: OHLC data.
    :ivar net_change: Net price change.
    :ivar oi: Open interest.
    :ivar oi_day_high: OI day high.
    :ivar oi_day_low: OI day low.
    :ivar depth: Market depth.
    """

    instrument_token: int = Field(..., description="Instrument token")
    timestamp: Optional[datetime] = Field(None, description="Timestamp")
    last_price: float = Field(..., description="Last price")
    last_quantity: int = Field(default=0, description="Last quantity")
    last_trade_time: Optional[datetime] = Field(None, description="Last trade time")
    average_price: float = Field(default=0, description="Average price")
    volume: int = Field(default=0, description="Volume")
    buy_quantity: int = Field(default=0, description="Buy quantity")
    sell_quantity: int = Field(default=0, description="Sell quantity")
    ohlc: Optional[OHLC] = Field(None, description="OHLC data")
    net_change: float = Field(default=0, description="Net change")
    oi: int = Field(default=0, description="Open interest")
    oi_day_high: int = Field(default=0, description="OI day high")
    oi_day_low: int = Field(default=0, description="OI day low")
    depth: Optional[MarketDepth] = Field(None, description="Market depth")

    class Config:
        """Pydantic configuration."""

        extra = "allow"


class HistoricalData(BaseModel):
    """
    Historical candle data model.

    :ivar date: Candle timestamp.
    :ivar open: Opening price.
    :ivar high: High price.
    :ivar low: Low price.
    :ivar close: Closing price.
    :ivar volume: Volume traded.
    :ivar oi: Open interest (for F&O).
    """

    date: datetime = Field(..., description="Candle timestamp")
    open: float = Field(..., description="Open price")
    high: float = Field(..., description="High price")
    low: float = Field(..., description="Low price")
    close: float = Field(..., description="Close price")
    volume: int = Field(..., description="Volume")
    oi: Optional[int] = Field(None, description="Open interest")


class Instrument(BaseModel):
    """
    Instrument details model.

    :ivar instrument_token: Unique instrument token.
    :ivar exchange_token: Exchange token.
    :ivar tradingsymbol: Trading symbol.
    :ivar name: Instrument name.
    :ivar last_price: Last traded price.
    :ivar expiry: Expiry date for derivatives.
    :ivar strike: Strike price for options.
    :ivar tick_size: Minimum tick size.
    :ivar lot_size: Lot size.
    :ivar instrument_type: Instrument type (EQ, FUT, CE, PE).
    :ivar segment: Trading segment.
    :ivar exchange: Exchange name.
    """

    instrument_token: int = Field(..., description="Instrument token")
    exchange_token: int = Field(..., description="Exchange token")
    tradingsymbol: str = Field(..., description="Trading symbol")
    name: str = Field(default="", description="Instrument name")
    last_price: float = Field(default=0, description="Last price")
    expiry: Optional[date] = Field(None, description="Expiry date")
    strike: float = Field(default=0, description="Strike price")
    tick_size: float = Field(default=0.05, description="Tick size")
    lot_size: int = Field(default=1, description="Lot size")
    instrument_type: str = Field(default="", description="Instrument type")
    segment: str = Field(default="", description="Segment")
    exchange: str = Field(..., description="Exchange")

    class Config:
        """Pydantic configuration."""

        extra = "allow"


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


class Tick(BaseModel):
    """
    WebSocket tick data model.

    :ivar instrument_token: Instrument token.
    :ivar mode: Tick mode (ltp, quote, full).
    :ivar tradable: Whether instrument is tradable.
    :ivar last_price: Last traded price.
    :ivar last_traded_quantity: Last traded quantity.
    :ivar average_traded_price: Average traded price.
    :ivar volume_traded: Volume traded.
    :ivar total_buy_quantity: Total buy quantity.
    :ivar total_sell_quantity: Total sell quantity.
    :ivar change: Price change percentage.
    :ivar last_trade_time: Last trade timestamp.
    :ivar exchange_timestamp: Exchange timestamp.
    :ivar oi: Open interest.
    :ivar oi_day_high: OI day high.
    :ivar oi_day_low: OI day low.
    :ivar ohlc: OHLC data.
    :ivar depth: Market depth.
    """

    instrument_token: int = Field(..., description="Instrument token")
    mode: str = Field(default="ltp", description="Tick mode")
    tradable: bool = Field(default=True, description="Is tradable")
    last_price: float = Field(..., description="Last price")
    last_traded_quantity: Optional[int] = Field(None, description="Last quantity")
    average_traded_price: Optional[float] = Field(None, description="Avg price")
    volume_traded: Optional[int] = Field(None, description="Volume")
    total_buy_quantity: Optional[int] = Field(None, description="Total buy qty")
    total_sell_quantity: Optional[int] = Field(None, description="Total sell qty")
    change: Optional[float] = Field(None, description="Change %")
    last_trade_time: Optional[datetime] = Field(None, description="Last trade time")
    exchange_timestamp: Optional[datetime] = Field(None, description="Exchange time")
    oi: Optional[int] = Field(None, description="Open interest")
    oi_day_high: Optional[int] = Field(None, description="OI day high")
    oi_day_low: Optional[int] = Field(None, description="OI day low")
    ohlc: Optional[OHLC] = Field(None, description="OHLC")
    depth: Optional[MarketDepth] = Field(None, description="Depth")

    class Config:
        """Pydantic configuration."""

        extra = "allow"


class OrderResponse(BaseModel):
    """
    Order placement response model.

    :ivar order_id: The placed order ID.
    """

    order_id: str = Field(..., description="Order ID")


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
