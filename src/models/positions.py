"""
Position and holding models.

This module contains models for positions and holdings.
"""

from typing import Optional

from pydantic import BaseModel, Field

from src.models.enums import ProductType


class Position(BaseModel):
    """
    Trading position model.

    :ivar tradingsymbol: Trading symbol.
    :ivar exchange: Exchange code.
    :ivar instrument_token: Instrument token.
    :ivar product: Product type.
    :ivar quantity: Net quantity.
    :ivar overnight_quantity: Overnight quantity.
    :ivar multiplier: Lot multiplier.
    :ivar average_price: Average price.
    :ivar close_price: Previous close price.
    :ivar last_price: Last traded price.
    :ivar value: Position value.
    :ivar pnl: Profit/Loss.
    :ivar m2m: Mark-to-market P&L.
    :ivar unrealised: Unrealised P&L.
    :ivar realised: Realised P&L.
    :ivar buy_quantity: Total buy quantity.
    :ivar buy_price: Average buy price.
    :ivar buy_value: Total buy value.
    :ivar buy_m2m: Buy M2M value.
    :ivar sell_quantity: Total sell quantity.
    :ivar sell_price: Average sell price.
    :ivar sell_value: Total sell value.
    :ivar sell_m2m: Sell M2M value.
    :ivar day_buy_quantity: Day buy quantity.
    :ivar day_buy_price: Day buy average price.
    :ivar day_buy_value: Day buy value.
    :ivar day_sell_quantity: Day sell quantity.
    :ivar day_sell_price: Day sell average price.
    :ivar day_sell_value: Day sell value.
    """

    tradingsymbol: str = Field(..., description="Trading symbol")
    exchange: str = Field(..., description="Exchange")
    instrument_token: Optional[int] = Field(None, description="Instrument token")
    product: ProductType = Field(..., description="Product type")
    quantity: int = Field(default=0, description="Net quantity")
    overnight_quantity: int = Field(default=0, description="Overnight quantity")
    multiplier: int = Field(default=1, description="Multiplier")
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
    buy_m2m: float = Field(default=0, description="Buy M2M")
    sell_quantity: int = Field(default=0, description="Sell quantity")
    sell_price: float = Field(default=0, description="Sell price")
    sell_value: float = Field(default=0, description="Sell value")
    sell_m2m: float = Field(default=0, description="Sell M2M")
    day_buy_quantity: int = Field(default=0, description="Day buy quantity")
    day_buy_price: float = Field(default=0, description="Day buy price")
    day_buy_value: float = Field(default=0, description="Day buy value")
    day_sell_quantity: int = Field(default=0, description="Day sell quantity")
    day_sell_price: float = Field(default=0, description="Day sell price")
    day_sell_value: float = Field(default=0, description="Day sell value")

    class Config:
        """Pydantic configuration."""

        extra = "allow"

    @property
    def is_open(self) -> bool:
        """
        Check if position is open.

        :return: True if quantity is non-zero.
        """
        return self.quantity != 0

    @property
    def is_long(self) -> bool:
        """
        Check if position is long.

        :return: True if quantity is positive.
        """
        return self.quantity > 0

    @property
    def is_short(self) -> bool:
        """
        Check if position is short.

        :return: True if quantity is negative.
        """
        return self.quantity < 0


class Holding(BaseModel):
    """
    Holdings (CNC/delivery) model.

    :ivar tradingsymbol: Trading symbol.
    :ivar exchange: Exchange code.
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
