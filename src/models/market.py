"""
Market data models.

This module contains models for market data including quotes, ticks,
instruments, OHLC data, and market depth.
"""

from datetime import date, datetime
from typing import List, Optional

from pydantic import BaseModel, Field


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
