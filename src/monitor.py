"""
Position and Order Monitor.

This module monitors the Kite account for new positions and orders,
automatically detecting trades placed via Kite Web/App.

:copyright: (c) 2025
:license: MIT
"""

import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Optional, Set, Any, Callable
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class TrackedPosition:
    """
    Represents a tracked position from the account.

    This dataclass holds all relevant information about a trading position
    including quantities, prices, and timestamps.

    :ivar instrument_token: Kite instrument token.
    :ivar trading_symbol: Trading symbol (e.g., "SENSEX25D0486000CE").
    :ivar exchange: Exchange name (NFO, BFO, NSE, etc.).
    :ivar product: Product type (NRML, MIS, CNC).
    :ivar quantity: Net quantity (positive=long, negative=short).
    :ivar average_price: Average entry price.
    :ivar last_price: Last traded price.
    :ivar pnl: Unrealized P&L.
    :ivar buy_quantity: Total buy quantity.
    :ivar sell_quantity: Total sell quantity.
    :ivar buy_price: Average buy price.
    :ivar sell_price: Average sell price.
    :ivar multiplier: Lot multiplier.
    :ivar first_seen: When position was first detected.
    :ivar last_updated: When position was last updated.

    Example::

        pos = TrackedPosition(
            instrument_token=12345,
            trading_symbol="SENSEX25D0486000CE",
            exchange="BFO",
            product="NRML",
            quantity=1000,
            average_price=366.0,
        )
        print(pos.position_type)
    """

    instrument_token: int
    trading_symbol: str
    exchange: str
    product: str
    quantity: int
    average_price: float
    last_price: float = 0.0
    pnl: float = 0.0
    buy_quantity: int = 0
    sell_quantity: int = 0
    buy_price: float = 0.0
    sell_price: float = 0.0
    multiplier: int = 1
    first_seen: datetime = field(default_factory=datetime.now)
    last_updated: datetime = field(default_factory=datetime.now)

    @property
    def position_type(self) -> str:
        """
        Get the position type based on quantity.

        :returns: "LONG" if positive quantity, "SHORT" if negative, "FLAT" if zero.
        :rtype: str
        """
        if self.quantity > 0:
            return "LONG"
        elif self.quantity < 0:
            return "SHORT"
        return "FLAT"

    @property
    def entry_price(self) -> float:
        """
        Get entry price based on position type.

        For LONG positions, returns buy_price.
        For SHORT positions, returns sell_price.

        :returns: The entry price for the position.
        :rtype: float
        """
        if self.quantity > 0:
            return self.buy_price
        elif self.quantity < 0:
            return self.sell_price
        return self.average_price

    @property
    def abs_quantity(self) -> int:
        """
        Get the absolute quantity.

        :returns: Absolute value of quantity.
        :rtype: int
        """
        return abs(self.quantity)

    @property
    def symbol_key(self) -> str:
        """
        Get the unique symbol key.

        :returns: Symbol key in format "EXCHANGE:SYMBOL".
        :rtype: str
        """
        return f"{self.exchange}:{self.trading_symbol}"

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the position to a dictionary.

        :returns: Dictionary representation of the position.
        :rtype: Dict[str, Any]
        """
        return {
            "instrument_token": self.instrument_token,
            "trading_symbol": self.trading_symbol,
            "exchange": self.exchange,
            "product": self.product,
            "quantity": self.quantity,
            "position_type": self.position_type,
            "entry_price": self.entry_price,
            "average_price": self.average_price,
            "last_price": self.last_price,
            "pnl": self.pnl,
            "buy_quantity": self.buy_quantity,
            "sell_quantity": self.sell_quantity,
            "first_seen": self.first_seen.isoformat(),
            "last_updated": self.last_updated.isoformat(),
        }


@dataclass
class TrackedOrder:
    """
    Represents a tracked order from the account.

    This dataclass holds all relevant information about an order
    including status, quantities, and timestamps.

    :ivar order_id: Unique order ID.
    :ivar exchange_order_id: Exchange order ID.
    :ivar trading_symbol: Trading symbol.
    :ivar exchange: Exchange name.
    :ivar transaction_type: BUY or SELL.
    :ivar order_type: MARKET, LIMIT, SL, SL-M.
    :ivar product: Product type.
    :ivar variety: Order variety.
    :ivar status: Order status.
    :ivar quantity: Order quantity.
    :ivar filled_quantity: Filled quantity.
    :ivar pending_quantity: Pending quantity.
    :ivar price: Order price.
    :ivar average_price: Average fill price.
    :ivar trigger_price: Trigger price for SL orders.
    :ivar instrument_token: Instrument token.
    :ivar placed_at: Order placement time.
    :ivar exchange_timestamp: Exchange timestamp.
    :ivar tag: Order tag.
    """

    order_id: str
    exchange_order_id: Optional[str]
    trading_symbol: str
    exchange: str
    transaction_type: str
    order_type: str
    product: str
    variety: str
    status: str
    quantity: int
    filled_quantity: int
    pending_quantity: int
    price: float
    average_price: float
    trigger_price: Optional[float]
    instrument_token: int
    placed_at: Optional[datetime]
    exchange_timestamp: Optional[datetime]
    tag: Optional[str] = None

    @property
    def is_complete(self) -> bool:
        """
        Check if order is fully executed.

        :returns: True if order status is COMPLETE.
        :rtype: bool
        """
        return self.status == "COMPLETE"

    @property
    def is_open(self) -> bool:
        """
        Check if order is still open/pending.

        :returns: True if order is OPEN, TRIGGER PENDING, or AMO REQ RECEIVED.
        :rtype: bool
        """
        return self.status in ("OPEN", "TRIGGER PENDING", "AMO REQ RECEIVED")

    @property
    def is_buy(self) -> bool:
        """
        Check if this is a buy order.

        :returns: True if transaction type is BUY.
        :rtype: bool
        """
        return self.transaction_type == "BUY"

    @property
    def symbol_key(self) -> str:
        """
        Get the unique symbol key.

        :returns: Symbol key in format "EXCHANGE:SYMBOL".
        :rtype: str
        """
        return f"{self.exchange}:{self.trading_symbol}"

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the order to a dictionary.

        :returns: Dictionary representation of the order.
        :rtype: Dict[str, Any]
        """
        return {
            "order_id": self.order_id,
            "trading_symbol": self.trading_symbol,
            "exchange": self.exchange,
            "transaction_type": self.transaction_type,
            "order_type": self.order_type,
            "product": self.product,
            "status": self.status,
            "quantity": self.quantity,
            "filled_quantity": self.filled_quantity,
            "price": self.price,
            "average_price": self.average_price,
            "instrument_token": self.instrument_token,
            "is_complete": self.is_complete,
            "placed_at": self.placed_at.isoformat() if self.placed_at else None,
        }


class PositionMonitor:
    """
    Monitors Kite account for positions and orders.

    Continuously polls the account and tracks:
    - New positions (trades executed via Kite Web/App)
    - Position updates (quantity/price changes)
    - Order status changes

    :param kite_client: Initialized KiteClient instance.
    :type kite_client: Any
    :param poll_interval: Seconds between polls.
    :type poll_interval: float
    :param on_new_position: Callback for new positions.
    :type on_new_position: Optional[Callable[[TrackedPosition], None]]
    :param on_position_update: Callback for position updates.
    :type on_position_update: Optional[Callable[[TrackedPosition], None]]
    :param on_position_closed: Callback when position closes.
    :type on_position_closed: Optional[Callable[[TrackedPosition], None]]
    :param on_order_complete: Callback for completed orders.
    :type on_order_complete: Optional[Callable[[TrackedOrder], None]]

    :ivar kite_client: The Kite client instance.
    :ivar poll_interval: Polling interval in seconds.
    :ivar _positions: Dictionary of tracked positions.
    :ivar _orders: Dictionary of tracked orders.

    Example::

        monitor = PositionMonitor(
            kite_client=client,
            poll_interval=2.0,
            on_new_position=handle_new_position,
        )
        await monitor.start()
    """

    def __init__(
        self,
        kite_client: Any,
        poll_interval: float = 2.0,
        on_new_position: Optional[Callable[[TrackedPosition], None]] = None,
        on_position_update: Optional[Callable[[TrackedPosition], None]] = None,
        on_position_closed: Optional[Callable[[TrackedPosition], None]] = None,
        on_order_complete: Optional[Callable[[TrackedOrder], None]] = None,
    ) -> None:
        """
        Initialize the position monitor.

        :param kite_client: KiteClient instance for API calls.
        :type kite_client: Any
        :param poll_interval: Polling interval in seconds.
        :type poll_interval: float
        :param on_new_position: Callback when new position detected.
        :type on_new_position: Optional[Callable[[TrackedPosition], None]]
        :param on_position_update: Callback when position quantity changes.
        :type on_position_update: Optional[Callable[[TrackedPosition], None]]
        :param on_position_closed: Callback when position is closed.
        :type on_position_closed: Optional[Callable[[TrackedPosition], None]]
        :param on_order_complete: Callback when order is completed.
        :type on_order_complete: Optional[Callable[[TrackedOrder], None]]
        """
        self.kite_client = kite_client
        self.poll_interval = poll_interval
        self.on_new_position = on_new_position
        self.on_position_update = on_position_update
        self.on_position_closed = on_position_closed
        self.on_order_complete = on_order_complete
        self._running = False
        self._task: Optional[asyncio.Task] = None
        self._positions: Dict[str, TrackedPosition] = {}
        self._orders: Dict[str, TrackedOrder] = {}
        self._completed_order_ids: Set[str] = set()

    def _parse_position(self, pos_data: Dict) -> TrackedPosition:
        """
        Parse position data from Kite API response.

        :param pos_data: Raw position data dictionary from API.
        :type pos_data: Dict
        :returns: Parsed TrackedPosition instance.
        :rtype: TrackedPosition
        """
        return TrackedPosition(
            instrument_token=pos_data.get("instrument_token", 0),
            trading_symbol=pos_data.get("tradingsymbol", ""),
            exchange=pos_data.get("exchange", ""),
            product=pos_data.get("product", ""),
            quantity=pos_data.get("quantity", 0),
            average_price=pos_data.get("average_price", 0.0),
            last_price=pos_data.get("last_price", 0.0),
            pnl=pos_data.get("pnl", 0.0),
            buy_quantity=pos_data.get("buy_quantity", 0),
            sell_quantity=pos_data.get("sell_quantity", 0),
            buy_price=pos_data.get("buy_price", 0.0),
            sell_price=pos_data.get("sell_price", 0.0),
            multiplier=pos_data.get("multiplier", 1),
        )

    def _parse_order(self, order_data: Dict) -> TrackedOrder:
        """
        Parse order data from Kite API response.

        :param order_data: Raw order data dictionary from API.
        :type order_data: Dict
        :returns: Parsed TrackedOrder instance.
        :rtype: TrackedOrder
        """
        placed_at = None
        if order_data.get("order_timestamp"):
            try:
                placed_at = datetime.fromisoformat(
                    str(order_data["order_timestamp"]).replace("Z", "+00:00")
                )
            except:
                pass

        exchange_ts = None
        if order_data.get("exchange_timestamp"):
            try:
                exchange_ts = datetime.fromisoformat(
                    str(order_data["exchange_timestamp"]).replace("Z", "+00:00")
                )
            except:
                pass

        return TrackedOrder(
            order_id=order_data.get("order_id", ""),
            exchange_order_id=order_data.get("exchange_order_id"),
            trading_symbol=order_data.get("tradingsymbol", ""),
            exchange=order_data.get("exchange", ""),
            transaction_type=order_data.get("transaction_type", ""),
            order_type=order_data.get("order_type", ""),
            product=order_data.get("product", ""),
            variety=order_data.get("variety", ""),
            status=order_data.get("status", ""),
            quantity=order_data.get("quantity", 0),
            filled_quantity=order_data.get("filled_quantity", 0),
            pending_quantity=order_data.get("pending_quantity", 0),
            price=order_data.get("price", 0.0),
            average_price=order_data.get("average_price", 0.0),
            trigger_price=order_data.get("trigger_price"),
            instrument_token=order_data.get("instrument_token", 0),
            placed_at=placed_at,
            exchange_timestamp=exchange_ts,
            tag=order_data.get("tag"),
        )

    async def _poll_positions(self) -> None:
        """
        Poll and process positions from Kite API.

        Fetches all net positions and:
        - Detects new positions and triggers on_new_position callback
        - Detects quantity changes and triggers on_position_update callback
        - Detects closed positions and triggers on_position_closed callback

        :returns: None
        :rtype: None
        """
        try:
            response = self.kite_client.positions()
            net_positions = response.get("net", [])

            current_keys = set()

            for pos_data in net_positions:
                pos = self._parse_position(pos_data)
                key = pos.symbol_key

                existing = self._positions.get(key)
                if pos.quantity == 0:
                    if existing is not None:
                        closed_pos = self._positions.pop(key)
                        logger.info(f"Position closed: {closed_pos.trading_symbol}")

                        if self.on_position_closed:
                            try:
                                if asyncio.iscoroutinefunction(self.on_position_closed):
                                    await self.on_position_closed(closed_pos)
                                else:
                                    self.on_position_closed(closed_pos)
                            except Exception as e:
                                logger.error(f"on_position_closed callback error: {e}")
                    continue

                current_keys.add(key)

                if existing is None:
                    self._positions[key] = pos
                    logger.info(
                        f"New position: {pos.trading_symbol} {pos.position_type} qty={pos.quantity}"
                    )

                    if self.on_new_position:
                        try:
                            if asyncio.iscoroutinefunction(self.on_new_position):
                                await self.on_new_position(pos)
                            else:
                                self.on_new_position(pos)
                        except Exception as e:
                            logger.error(f"on_new_position callback error: {e}")
                else:
                    pos.first_seen = existing.first_seen
                    pos.last_updated = datetime.now()
                    self._positions[key] = pos
                    if pos.quantity != existing.quantity:
                        logger.info(
                            f"Position updated: {pos.trading_symbol} qty={existing.quantity} -> {pos.quantity}"
                        )

                        if self.on_position_update:
                            try:
                                if asyncio.iscoroutinefunction(self.on_position_update):
                                    await self.on_position_update(pos)
                                else:
                                    self.on_position_update(pos)
                            except Exception as e:
                                logger.error(f"on_position_update callback error: {e}")

            closed_keys = set(self._positions.keys()) - current_keys
            for key in closed_keys:
                pos = self._positions.pop(key)
                logger.info(f"Position closed: {pos.trading_symbol}")

                if self.on_position_closed:
                    try:
                        if asyncio.iscoroutinefunction(self.on_position_closed):
                            await self.on_position_closed(pos)
                        else:
                            self.on_position_closed(pos)
                    except Exception as e:
                        logger.error(f"on_position_closed callback error: {e}")

        except Exception as e:
            logger.error(f"Error polling positions: {e}")

    async def _poll_orders(self) -> None:
        """
        Poll and process orders from Kite API.

        Fetches all orders and:
        - Tracks newly completed orders
        - Triggers on_order_complete callback for non-system orders
        - Skips orders with TP_ or SL_ tags (system-generated)

        :returns: None
        :rtype: None
        """
        try:
            orders = self.kite_client.orders()

            for order_data in orders:
                order = self._parse_order(order_data)
                if (
                    order.is_complete
                    and order.order_id not in self._completed_order_ids
                ):
                    self._completed_order_ids.add(order.order_id)
                    self._orders[order.order_id] = order
                    if order.tag and order.tag.startswith(("TP_", "SL_")):
                        continue

                    logger.info(
                        f"Order complete: {order.order_id} {order.transaction_type} "
                        f"{order.trading_symbol} @ {order.average_price}"
                    )

                    if self.on_order_complete:
                        try:
                            if asyncio.iscoroutinefunction(self.on_order_complete):
                                await self.on_order_complete(order)
                            else:
                                self.on_order_complete(order)
                        except Exception as e:
                            logger.error(f"on_order_complete callback error: {e}")
                else:
                    self._orders[order.order_id] = order

        except Exception as e:
            logger.error(f"Error polling orders: {e}")

    async def _run_loop(self) -> None:
        """
        Main monitoring loop.

        Continuously polls positions and orders at the configured
        interval until stopped.

        :returns: None
        :rtype: None
        """
        logger.info("Position monitor started")

        while self._running:
            await self._poll_positions()
            await self._poll_orders()
            await asyncio.sleep(self.poll_interval)

        logger.info("Position monitor stopped")

    async def start(self) -> None:
        """
        Start the position monitor.

        Creates a background task to run the monitoring loop.
        Does nothing if already running.

        :returns: None
        :rtype: None
        """
        if self._running:
            return

        self._running = True
        self._task = asyncio.create_task(self._run_loop())

    async def stop(self) -> None:
        """
        Stop the position monitor.

        Cancels the background monitoring task and waits for cleanup.

        :returns: None
        :rtype: None
        """
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None

    def is_running(self) -> bool:
        """
        Check if monitor is running.

        :returns: True if monitoring loop is active.
        :rtype: bool
        """
        return self._running

    def get_positions(self) -> Dict[str, TrackedPosition]:
        """
        Get all tracked positions.

        :returns: Copy of positions dictionary keyed by symbol_key.
        :rtype: Dict[str, TrackedPosition]
        """
        return self._positions.copy()

    def get_position(self, symbol_key: str) -> Optional[TrackedPosition]:
        """
        Get position by symbol key.

        :param symbol_key: Position key in format "EXCHANGE:SYMBOL".
        :type symbol_key: str
        :returns: Position if found, None otherwise.
        :rtype: Optional[TrackedPosition]
        """
        return self._positions.get(symbol_key)

    def get_orders(self) -> Dict[str, TrackedOrder]:
        """
        Get all tracked orders.

        :returns: Copy of orders dictionary keyed by order_id.
        :rtype: Dict[str, TrackedOrder]
        """
        return self._orders.copy()

    def get_instrument_tokens(self) -> List[int]:
        """
        Get list of instrument tokens for all positions.

        :returns: List of instrument tokens for price subscriptions.
        :rtype: List[int]
        """
        return [p.instrument_token for p in self._positions.values()]
