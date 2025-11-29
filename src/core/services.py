"""
Service layer for business logic.

This module provides service classes that encapsulate business logic,
separate from API handlers and data access.

:copyright: (c) 2025
:license: MIT
"""

import asyncio
import logging
from abc import ABC
from typing import Any, Dict, List, Optional

from src.brokers.base import BaseBroker
from src.core.events import Event, EventBus, EventType, get_event_bus
from src.core.sessions import SessionManager, UserContext, get_session_manager
from src.models import Order, OrderResult, Position, Trade

logger = logging.getLogger(__name__)


class BaseService(ABC):
    """
    Base class for all services.

    Provides common functionality like event publishing
    and session access.
    """

    def __init__(
        self,
        event_bus: Optional[EventBus] = None,
        session_manager: Optional[SessionManager] = None,
    ) -> None:
        """
        Initialize base service.

        :param event_bus: Event bus for publishing events.
        :type event_bus: Optional[EventBus]
        :param session_manager: Session manager for user contexts.
        :type session_manager: Optional[SessionManager]
        """
        self._event_bus = event_bus or get_event_bus()
        self._session_manager = session_manager or get_session_manager()

    async def _publish_event(
        self,
        event_type: EventType,
        user_id: Optional[str] = None,
        data: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Publish an event.

        :param event_type: Type of event.
        :type event_type: EventType
        :param user_id: Associated user ID.
        :type user_id: Optional[str]
        :param data: Event data.
        :type data: Optional[Dict[str, Any]]
        """
        await self._event_bus.publish(
            Event(type=event_type, user_id=user_id, data=data or {})
        )

    def _get_context(self, user_id: str) -> Optional[UserContext]:
        """
        Get user context.

        :param user_id: User identifier.
        :type user_id: str
        :returns: User context or None.
        :rtype: Optional[UserContext]
        """
        return self._session_manager.get_context(user_id)

    def _get_broker(self, user_id: str) -> Optional[BaseBroker]:
        """
        Get broker for user.

        :param user_id: User identifier.
        :type user_id: str
        :returns: Broker client or None.
        :rtype: Optional[BaseBroker]
        """
        context = self._get_context(user_id)
        return context.broker if context else None


class TradingService(BaseService):
    """
    Service for trading operations.

    Handles order placement, position management, and trade execution
    with proper event publishing and error handling.

    Example::

        service = TradingService()


        result = await service.place_order(
            user_id="user123",
            symbol="RELIANCE",
            exchange="NSE",
            quantity=10,
            side="BUY",
            order_type="MARKET"
        )
    """

    async def get_positions(self, user_id: str) -> List[Position]:
        """
        Get all positions for a user.

        :param user_id: User identifier.
        :type user_id: str
        :returns: List of positions.
        :rtype: List[Position]
        :raises ValueError: If user not found.
        """
        broker = self._get_broker(user_id)
        if not broker:
            raise ValueError(f"No active session for user {user_id}")

        try:
            return broker.get_positions()
        except Exception as e:
            logger.error(f"Error getting positions for {user_id}: {e}")
            await self._publish_event(
                EventType.SYSTEM_ERROR,
                user_id=user_id,
                data={"error": str(e), "operation": "get_positions"},
            )
            raise

    async def get_orders(self, user_id: str) -> List[Dict[str, Any]]:
        """
        Get all orders for a user.

        :param user_id: User identifier.
        :type user_id: str
        :returns: List of orders.
        :rtype: List[Dict[str, Any]]
        :raises ValueError: If user not found.
        """
        broker = self._get_broker(user_id)
        if not broker:
            raise ValueError(f"No active session for user {user_id}")

        try:
            return broker.get_orders()
        except Exception as e:
            logger.error(f"Error getting orders for {user_id}: {e}")
            raise

    async def place_order(
        self,
        user_id: str,
        symbol: str,
        exchange: str,
        quantity: int,
        side: str,
        order_type: str = "MARKET",
        price: Optional[float] = None,
        trigger_price: Optional[float] = None,
        product: str = "NRML",
        tag: Optional[str] = None,
    ) -> OrderResult:
        """
        Place an order for a user.

        :param user_id: User identifier.
        :type user_id: str
        :param symbol: Trading symbol.
        :type symbol: str
        :param exchange: Exchange code.
        :type exchange: str
        :param quantity: Order quantity.
        :type quantity: int
        :param side: BUY or SELL.
        :type side: str
        :param order_type: Order type (MARKET, LIMIT, etc.).
        :type order_type: str
        :param price: Limit price.
        :type price: Optional[float]
        :param trigger_price: Stop-loss trigger price.
        :type trigger_price: Optional[float]
        :param product: Product type.
        :type product: str
        :param tag: Order tag.
        :type tag: Optional[str]
        :returns: Order result.
        :rtype: OrderResult
        :raises ValueError: If user not found.
        """
        broker = self._get_broker(user_id)
        if not broker:
            raise ValueError(f"No active session for user {user_id}")

        order = Order(
            order_id="",
            tradingsymbol=symbol,
            exchange=exchange,
            transaction_type=side,
            quantity=quantity,
            order_type=order_type,
            product=product,
            price=price or 0,
            trigger_price=trigger_price or 0,
            status="PENDING",
            tag=tag,
        )

        try:
            result = broker.place_order(order)

            await self._publish_event(
                EventType.ORDER_PLACED,
                user_id=user_id,
                data={
                    "order_id": result.order_id,
                    "symbol": symbol,
                    "exchange": exchange,
                    "quantity": quantity,
                    "side": side,
                    "order_type": order_type,
                },
            )

            return result

        except Exception as e:
            logger.error(f"Error placing order for {user_id}: {e}")
            await self._publish_event(
                EventType.ORDER_REJECTED,
                user_id=user_id,
                data={
                    "symbol": symbol,
                    "error": str(e),
                },
            )
            raise

    async def cancel_order(self, user_id: str, order_id: str) -> bool:
        """
        Cancel an order.

        :param user_id: User identifier.
        :type user_id: str
        :param order_id: Order ID to cancel.
        :type order_id: str
        :returns: True if cancelled.
        :rtype: bool
        :raises ValueError: If user not found.
        """
        broker = self._get_broker(user_id)
        if not broker:
            raise ValueError(f"No active session for user {user_id}")

        try:
            result = broker.cancel_order(order_id)

            if result:
                await self._publish_event(
                    EventType.ORDER_CANCELLED,
                    user_id=user_id,
                    data={"order_id": order_id},
                )

            return result

        except Exception as e:
            logger.error(f"Error cancelling order {order_id} for {user_id}: {e}")
            raise

    async def get_trades(self, user_id: str) -> List[Trade]:
        """
        Get all trades for a user.

        :param user_id: User identifier.
        :type user_id: str
        :returns: List of trades.
        :rtype: List[Trade]
        :raises ValueError: If user not found.
        """
        broker = self._get_broker(user_id)
        if not broker:
            raise ValueError(f"No active session for user {user_id}")

        try:
            return broker.get_trades()
        except Exception as e:
            logger.error(f"Error getting trades for {user_id}: {e}")
            raise


class RuleExecutionService(BaseService):
    """
    Service for rule-based trade execution.

    Manages matching positions to rules and executing
    exit conditions (TP/SL).

    Example::

        service = RuleExecutionService()


        await service.start_monitoring(user_id="user123")


        triggered = await service.check_triggers(user_id="user123")
    """

    def __init__(
        self,
        event_bus: Optional[EventBus] = None,
        session_manager: Optional[SessionManager] = None,
        trading_service: Optional[TradingService] = None,
    ) -> None:
        """
        Initialize rule execution service.

        :param event_bus: Event bus.
        :type event_bus: Optional[EventBus]
        :param session_manager: Session manager.
        :type session_manager: Optional[SessionManager]
        :param trading_service: Trading service for order placement.
        :type trading_service: Optional[TradingService]
        """
        super().__init__(event_bus, session_manager)
        self._trading_service = trading_service or TradingService(
            event_bus, session_manager
        )
        self._monitoring_tasks: Dict[str, asyncio.Task] = {}

    async def start_monitoring(
        self,
        user_id: str,
        poll_interval: float = 1.0,
    ) -> bool:
        """
        Start position monitoring for a user.

        :param user_id: User identifier.
        :type user_id: str
        :param poll_interval: Price check interval in seconds.
        :type poll_interval: float
        :returns: True if monitoring started.
        :rtype: bool
        """
        if user_id in self._monitoring_tasks:
            return False

        context = self._get_context(user_id)
        if not context:
            raise ValueError(f"No active session for user {user_id}")

        async def monitor_loop():
            while True:
                try:
                    await self.check_triggers(user_id)
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    logger.error(f"Monitoring error for {user_id}: {e}")
                await asyncio.sleep(poll_interval)

        task = asyncio.create_task(monitor_loop())
        self._monitoring_tasks[user_id] = task
        context.add_task(task)

        logger.info(f"Started monitoring for user {user_id}")
        return True

    async def stop_monitoring(self, user_id: str) -> bool:
        """
        Stop position monitoring for a user.

        :param user_id: User identifier.
        :type user_id: str
        :returns: True if monitoring stopped.
        :rtype: bool
        """
        task = self._monitoring_tasks.pop(user_id, None)
        if task:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
            logger.info(f"Stopped monitoring for user {user_id}")
            return True
        return False

    async def check_triggers(self, user_id: str) -> List[Dict[str, Any]]:
        """
        Check for triggered exit conditions.

        :param user_id: User identifier.
        :type user_id: str
        :returns: List of triggered conditions.
        :rtype: List[Dict[str, Any]]
        """

        return []

    async def execute_exit(
        self,
        user_id: str,
        position: Position,
        trigger_type: str,
        trigger_price: float,
    ) -> Optional[OrderResult]:
        """
        Execute exit order for a position.

        :param user_id: User identifier.
        :type user_id: str
        :param position: Position to exit.
        :type position: Position
        :param trigger_type: TP or SL.
        :type trigger_type: str
        :param trigger_price: Price that triggered exit.
        :type trigger_price: float
        :returns: Order result or None.
        :rtype: Optional[OrderResult]
        """
        side = "SELL" if position.quantity > 0 else "BUY"
        quantity = abs(position.quantity)

        try:
            result = await self._trading_service.place_order(
                user_id=user_id,
                symbol=position.tradingsymbol,
                exchange=position.exchange,
                quantity=quantity,
                side=side,
                order_type="MARKET",
                product=position.product.value,
                tag=f"AUTO_{trigger_type}",
            )

            event_type = (
                EventType.TP_TRIGGERED
                if trigger_type == "TP"
                else EventType.SL_TRIGGERED
            )
            await self._publish_event(
                event_type,
                user_id=user_id,
                data={
                    "symbol": position.tradingsymbol,
                    "trigger_price": trigger_price,
                    "order_id": result.order_id,
                },
            )

            return result

        except Exception as e:
            logger.error(f"Failed to execute exit for {user_id}: {e}")
            return None
