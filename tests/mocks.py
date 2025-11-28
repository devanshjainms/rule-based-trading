"""
Mock clients for testing.

These mock the Kite Connect API without making real API calls.

:copyright: (c) 2025
:license: MIT
"""

from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime
import asyncio


@dataclass
class MockPosition:
    """
    Mock position data for testing.

    :ivar tradingsymbol: Trading symbol name.
    :ivar exchange: Exchange code (NSE, BSE, NFO, etc.).
    :ivar quantity: Position quantity (positive=long, negative=short).
    :ivar average_price: Average entry price.
    :ivar last_price: Current market price.
    :ivar product: Product type (NRML, MIS, etc.).
    :ivar instrument_token: Unique instrument identifier.
    :ivar pnl: Profit/loss amount.
    :ivar buy_quantity: Total buy quantity.
    :ivar sell_quantity: Total sell quantity.
    :ivar buy_price: Average buy price.
    :ivar sell_price: Average sell price.
    """

    tradingsymbol: str
    exchange: str
    quantity: int
    average_price: float
    last_price: float
    product: str = "NRML"
    instrument_token: int = 12345
    pnl: float = 0.0
    buy_quantity: int = 0
    sell_quantity: int = 0
    buy_price: float = 0.0
    sell_price: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert to API response format.

        :returns: Position data as dictionary.
        :rtype: Dict[str, Any]
        """
        return {
            "tradingsymbol": self.tradingsymbol,
            "exchange": self.exchange,
            "quantity": self.quantity,
            "average_price": self.average_price,
            "last_price": self.last_price,
            "product": self.product,
            "instrument_token": self.instrument_token,
            "pnl": self.pnl,
            "buy_quantity": (
                self.buy_quantity
                if self.buy_quantity
                else abs(self.quantity) if self.quantity > 0 else 0
            ),
            "sell_quantity": (
                self.sell_quantity
                if self.sell_quantity
                else abs(self.quantity) if self.quantity < 0 else 0
            ),
            "buy_price": (
                self.buy_price
                if self.buy_price
                else self.average_price if self.quantity > 0 else 0
            ),
            "sell_price": (
                self.sell_price
                if self.sell_price
                else self.average_price if self.quantity < 0 else 0
            ),
            "multiplier": 1,
        }


@dataclass
class MockOrder:
    """
    Mock order placed during testing.

    :ivar order_id: Unique order identifier.
    :ivar tradingsymbol: Trading symbol name.
    :ivar exchange: Exchange code.
    :ivar transaction_type: BUY or SELL.
    :ivar quantity: Order quantity.
    :ivar order_type: MARKET, LIMIT, etc.
    :ivar product: Product type.
    :ivar variety: Order variety (regular, amo, etc.).
    :ivar status: Order status (COMPLETE, PENDING, etc.).
    :ivar price: Order price.
    :ivar trigger_price: Trigger price for SL orders.
    :ivar tag: Order tag for identification.
    :ivar placed_at: Order placement timestamp.
    """

    order_id: str
    tradingsymbol: str
    exchange: str
    transaction_type: str
    quantity: int
    order_type: str
    product: str
    variety: str = "regular"
    status: str = "COMPLETE"
    price: float = 0.0
    trigger_price: float = 0.0
    tag: Optional[str] = None
    placed_at: datetime = field(default_factory=datetime.now)


class MockKiteClient:
    """
    Mock Kite Connect client for testing.

    Simulates API responses without making real calls.

    :ivar _positions: List of mock positions.
    :ivar _orders: List of placed orders.
    :ivar _ltp: Last traded prices dictionary.
    :ivar order_callback: Callback for order events.

    Example::

        client = MockKiteClient()
        client.add_position(MockPosition(
            tradingsymbol="SENSEX25D0486000CE",
            exchange="BFO",
            quantity=1000,
            average_price=366.0,
            last_price=370.0,
        ))

        positions = client.positions()
    """

    def __init__(self) -> None:
        """
        Initialize mock Kite client.

        :returns: None
        :rtype: None
        """
        self._positions: List[MockPosition] = []
        self._orders: List[MockOrder] = []
        self._ltp: Dict[str, float] = {}
        self._order_counter = 0
        self.order_callback: Optional[Callable] = None

    def add_position(self, position: MockPosition) -> None:
        """
        Add a mock position.

        :param position: Position to add.
        :type position: MockPosition
        :returns: None
        :rtype: None
        """
        self._positions = [
            p for p in self._positions if p.tradingsymbol != position.tradingsymbol
        ]
        self._positions.append(position)
        self._ltp[f"{position.exchange}:{position.tradingsymbol}"] = position.last_price

    def update_ltp(self, symbol: str, exchange: str, price: float) -> None:
        """
        Update last traded price for a symbol.

        :param symbol: Trading symbol.
        :type symbol: str
        :param exchange: Exchange code.
        :type exchange: str
        :param price: New price.
        :type price: float
        :returns: None
        :rtype: None
        """
        self._ltp[f"{exchange}:{symbol}"] = price
        for pos in self._positions:
            if pos.tradingsymbol == symbol and pos.exchange == exchange:
                pos.last_price = price
                pos.pnl = (price - pos.average_price) * pos.quantity

    def close_position(self, symbol: str) -> None:
        """
        Close a position (set quantity to 0).

        :param symbol: Trading symbol to close.
        :type symbol: str
        :returns: None
        :rtype: None
        """
        for pos in self._positions:
            if pos.tradingsymbol == symbol:
                pos.quantity = 0

    def positions(self) -> Dict[str, List[Dict]]:
        """
        Get positions (mock API response).

        :returns: Positions in API response format.
        :rtype: Dict[str, List[Dict]]
        """
        return {
            "net": [p.to_dict() for p in self._positions],
            "day": [p.to_dict() for p in self._positions],
        }

    def orders(self) -> List[Dict[str, Any]]:
        """
        Get orders (mock API response).

        :returns: Orders in API response format.
        :rtype: List[Dict[str, Any]]
        """
        return [
            {
                "order_id": o.order_id,
                "tradingsymbol": o.tradingsymbol,
                "exchange": o.exchange,
                "transaction_type": o.transaction_type,
                "quantity": o.quantity,
                "order_type": o.order_type,
                "product": o.product,
                "variety": o.variety,
                "status": o.status,
                "price": o.price,
                "trigger_price": o.trigger_price,
                "tag": o.tag,
                "order_timestamp": o.placed_at.isoformat(),
            }
            for o in self._orders
        ]

    def ltp(self, *instruments: str) -> Dict[str, Dict[str, Any]]:
        """
        Get LTP for instruments.

        :param instruments: Instrument strings in "EXCHANGE:SYMBOL" format.
        :type instruments: str
        :returns: LTP data for each instrument.
        :rtype: Dict[str, Dict[str, Any]]
        """
        result = {}
        for inst in instruments:
            if inst in self._ltp:
                result[inst] = {
                    "instrument_token": 12345,
                    "last_price": self._ltp[inst],
                }
        return result

    def place_order(
        self,
        variety: str,
        exchange: str,
        tradingsymbol: str,
        transaction_type: str,
        quantity: int,
        product: str,
        order_type: str,
        price: float = 0.0,
        trigger_price: float = 0.0,
        tag: Optional[str] = None,
        **kwargs,
    ) -> str:
        """
        Place an order (mock).

        :param variety: Order variety (regular, amo, etc.).
        :type variety: str
        :param exchange: Exchange code.
        :type exchange: str
        :param tradingsymbol: Trading symbol.
        :type tradingsymbol: str
        :param transaction_type: BUY or SELL.
        :type transaction_type: str
        :param quantity: Order quantity.
        :type quantity: int
        :param product: Product type.
        :type product: str
        :param order_type: MARKET, LIMIT, etc.
        :type order_type: str
        :param price: Order price.
        :type price: float
        :param trigger_price: Trigger price for SL orders.
        :type trigger_price: float
        :param tag: Order tag.
        :type tag: Optional[str]
        :param kwargs: Additional order parameters.
        :returns: Order ID.
        :rtype: str
        """
        self._order_counter += 1
        order_id = f"MOCK{self._order_counter:06d}"

        order = MockOrder(
            order_id=order_id,
            tradingsymbol=tradingsymbol,
            exchange=exchange,
            transaction_type=transaction_type,
            quantity=quantity,
            order_type=order_type,
            product=product,
            variety=variety,
            price=price,
            trigger_price=trigger_price,
            tag=tag,
        )
        self._orders.append(order)

        if transaction_type == "SELL":
            for pos in self._positions:
                if pos.tradingsymbol == tradingsymbol and pos.quantity > 0:
                    pos.quantity -= quantity
        elif transaction_type == "BUY":
            for pos in self._positions:
                if pos.tradingsymbol == tradingsymbol and pos.quantity < 0:
                    pos.quantity += quantity

        if self.order_callback:
            self.order_callback(order)

        return order_id

    def profile(self) -> Dict[str, Any]:
        """
        Get user profile (mock).

        :returns: User profile data.
        :rtype: Dict[str, Any]
        """
        return {
            "user_id": "TEST123",
            "user_name": "Test User",
            "email": "test@example.com",
        }

    def get_placed_orders(self) -> List[MockOrder]:
        """
        Get all orders placed during test.

        :returns: List of placed orders.
        :rtype: List[MockOrder]
        """
        return self._orders.copy()

    def clear_orders(self) -> None:
        """
        Clear order history.

        :returns: None
        :rtype: None
        """
        self._orders.clear()
        self._order_counter = 0


class MockTickerClient:
    """
    Mock WebSocket ticker for testing.

    Simulates real-time price updates without actual connection.

    :ivar api_key: API key (mock).
    :ivar access_token: Access token (mock).
    :ivar on_ticks: Callback for tick events.
    :ivar on_connect: Callback for connect events.
    :ivar on_close: Callback for close events.
    :ivar on_error: Callback for error events.
    """

    def __init__(self, api_key: str = "test", access_token: str = "test") -> None:
        """
        Initialize mock ticker client.

        :param api_key: API key (default: "test").
        :type api_key: str
        :param access_token: Access token (default: "test").
        :type access_token: str
        """
        self.api_key = api_key
        self.access_token = access_token
        self._subscribed_tokens: List[int] = []
        self._connected = False
        self.on_ticks: Optional[Callable] = None
        self.on_connect: Optional[Callable] = None
        self.on_close: Optional[Callable] = None
        self.on_error: Optional[Callable] = None

    def connect(self, threaded: bool = True) -> None:
        """
        Connect (mock).

        :param threaded: Run in separate thread (ignored in mock).
        :type threaded: bool
        :returns: None
        :rtype: None
        """
        self._connected = True
        if self.on_connect:
            self.on_connect(self)

    def close(self) -> None:
        """
        Close connection.

        :returns: None
        :rtype: None
        """
        self._connected = False
        if self.on_close:
            self.on_close(self, 1000, "Test close")

    def is_connected(self) -> bool:
        """
        Check if connected.

        :returns: True if connected.
        :rtype: bool
        """
        return self._connected

    def subscribe(self, tokens: List[int]) -> None:
        """
        Subscribe to tokens.

        :param tokens: List of instrument tokens.
        :type tokens: List[int]
        :returns: None
        :rtype: None
        """
        for token in tokens:
            if token not in self._subscribed_tokens:
                self._subscribed_tokens.append(token)

    def unsubscribe(self, tokens: List[int]) -> None:
        """
        Unsubscribe from tokens.

        :param tokens: List of instrument tokens.
        :type tokens: List[int]
        :returns: None
        :rtype: None
        """
        for token in tokens:
            if token in self._subscribed_tokens:
                self._subscribed_tokens.remove(token)

    def set_mode(self, mode: str, tokens: List[int]) -> None:
        """
        Set subscription mode.

        :param mode: Subscription mode (LTP, QUOTE, FULL).
        :type mode: str
        :param tokens: List of instrument tokens.
        :type tokens: List[int]
        :returns: None
        :rtype: None
        """
        pass

    def simulate_tick(self, instrument_token: int, last_price: float, **extra) -> None:
        """
        Simulate a price tick.

        :param instrument_token: Token to update.
        :type instrument_token: int
        :param last_price: New price.
        :type last_price: float
        :param extra: Additional tick data.
        :returns: None
        :rtype: None
        """
        if self.on_ticks and instrument_token in self._subscribed_tokens:
            tick = {
                "instrument_token": instrument_token,
                "last_price": last_price,
                "timestamp": datetime.now(),
                **extra,
            }
            self.on_ticks(self, [tick])

    def simulate_ticks(self, ticks: List[Dict]) -> None:
        """
        Simulate multiple ticks at once.

        :param ticks: List of tick dictionaries.
        :type ticks: List[Dict]
        :returns: None
        :rtype: None
        """
        if self.on_ticks:
            for tick in ticks:
                tick.setdefault("timestamp", datetime.now())
            self.on_ticks(self, ticks)

    def get_subscribed_tokens(self) -> List[int]:
        """
        Get list of subscribed tokens.

        :returns: Copy of subscribed tokens list.
        :rtype: List[int]
        """
        return self._subscribed_tokens.copy()
