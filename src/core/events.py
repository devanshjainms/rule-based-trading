"""
Event system for pub/sub architecture.

This module provides an event bus for decoupled communication
between system components. Supports async handlers and event filtering.

:copyright: (c) 2025
:license: MIT
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Union
from uuid import uuid4

logger = logging.getLogger(__name__)


class EventType(str, Enum):
    """
    Standard event types in the trading system.

    :cvar POSITION_OPENED: New position detected.
    :cvar POSITION_CLOSED: Position fully closed.
    :cvar POSITION_UPDATED: Position quantity/price changed.
    :cvar ORDER_PLACED: Order submitted.
    :cvar ORDER_FILLED: Order fully executed.
    :cvar ORDER_CANCELLED: Order cancelled.
    :cvar ORDER_REJECTED: Order rejected.
    :cvar PRICE_UPDATE: Real-time price tick.
    :cvar TP_TRIGGERED: Take-profit condition met.
    :cvar SL_TRIGGERED: Stop-loss condition met.
    :cvar TIME_TRIGGER: Time-based condition met.
    :cvar RULE_MATCHED: Position matched to rule.
    :cvar RULE_CREATED: Trading rule created.
    :cvar RULE_UPDATED: Trading rule updated.
    :cvar RULE_DELETED: Trading rule deleted.
    :cvar SESSION_STARTED: User session started.
    :cvar SESSION_EXPIRED: User session expired.
    :cvar SYSTEM_ERROR: System error occurred.
    :cvar BROKER_CONNECTED: Broker connection established.
    :cvar BROKER_DISCONNECTED: Broker connection lost.
    """

    POSITION_OPENED = "position.opened"
    POSITION_CLOSED = "position.closed"
    POSITION_UPDATED = "position.updated"
    ORDER_PLACED = "order.placed"
    ORDER_FILLED = "order.filled"
    ORDER_CANCELLED = "order.cancelled"
    ORDER_REJECTED = "order.rejected"
    PRICE_UPDATE = "price.update"
    TP_TRIGGERED = "trigger.tp"
    SL_TRIGGERED = "trigger.sl"
    TIME_TRIGGER = "trigger.time"
    RULE_MATCHED = "rule.matched"
    RULE_CREATED = "rule.created"
    RULE_UPDATED = "rule.updated"
    RULE_DELETED = "rule.deleted"
    RULE_ENABLED = "rule.enabled"
    RULE_DISABLED = "rule.disabled"
    SESSION_STARTED = "session.started"
    SESSION_EXPIRED = "session.expired"
    SYSTEM_ERROR = "system.error"
    BROKER_CONNECTED = "broker.connected"
    BROKER_DISCONNECTED = "broker.disconnected"
    ENGINE_STARTED = "engine.started"
    ENGINE_STOPPED = "engine.stopped"


@dataclass
class Event:
    """
    Base event class for all system events.

    :ivar id: Unique event identifier.
    :ivar type: Event type from EventType enum.
    :ivar timestamp: When the event occurred.
    :ivar user_id: Associated user ID (if applicable).
    :ivar data: Event payload data.
    :ivar metadata: Additional event metadata.

    Example::

        event = Event(
            type=EventType.ORDER_PLACED,
            user_id="user123",
            data={"order_id": "ord_456", "symbol": "RELIANCE"}
        )
    """

    type: EventType
    user_id: Optional[str] = None
    data: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    id: str = field(default_factory=lambda: str(uuid4()))
    timestamp: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert event to dictionary.

        :returns: Event as dictionary.
        :rtype: Dict[str, Any]
        """
        return {
            "id": self.id,
            "type": self.type.value,
            "timestamp": self.timestamp.isoformat(),
            "user_id": self.user_id,
            "data": self.data,
            "metadata": self.metadata,
        }


EventHandler = Callable[[Event], Any]
AsyncEventHandler = Callable[[Event], Any]


class EventBus:
    """
    Central event bus for publish/subscribe pattern.

    Allows components to publish events and subscribe to event types
    without direct coupling. Supports both sync and async handlers.

    Example::

        bus = EventBus()


        @bus.subscribe(EventType.ORDER_PLACED)
        async def on_order(event: Event):
            print(f"Order placed: {event.data}")


        await bus.publish(Event(
            type=EventType.ORDER_PLACED,
            data={"symbol": "INFY"}
        ))
    """

    def __init__(self) -> None:
        """Initialize the event bus."""
        self._handlers: Dict[EventType, List[AsyncEventHandler]] = {}
        self._global_handlers: List[AsyncEventHandler] = []
        self._user_handlers: Dict[str, Dict[EventType, List[AsyncEventHandler]]] = {}

    def subscribe(
        self,
        event_type: Union[EventType, List[EventType]],
        user_id: Optional[str] = None,
    ) -> Callable:
        """
        Decorator to subscribe a handler to event type(s).

        :param event_type: Event type or list of types to subscribe to.
        :type event_type: Union[EventType, List[EventType]]
        :param user_id: Optional user ID for user-specific events.
        :type user_id: Optional[str]
        :returns: Decorator function.
        :rtype: Callable

        Example::

            @bus.subscribe(EventType.PRICE_UPDATE)
            async def handle_price(event):
                pass

            @bus.subscribe([EventType.TP_TRIGGERED, EventType.SL_TRIGGERED])
            async def handle_triggers(event):
                pass
        """

        def decorator(handler: AsyncEventHandler) -> AsyncEventHandler:
            types = [event_type] if isinstance(event_type, EventType) else event_type
            for et in types:
                if user_id:
                    if user_id not in self._user_handlers:
                        self._user_handlers[user_id] = {}
                    if et not in self._user_handlers[user_id]:
                        self._user_handlers[user_id][et] = []
                    self._user_handlers[user_id][et].append(handler)
                else:
                    if et not in self._handlers:
                        self._handlers[et] = []
                    self._handlers[et].append(handler)
            return handler

        return decorator

    def subscribe_all(self) -> Callable:
        """
        Subscribe to all events.

        :returns: Decorator function.
        :rtype: Callable

        Example::

            @bus.subscribe_all()
            async def log_all_events(event):
                logger.info(f"Event: {event.type}")
        """

        def decorator(handler: AsyncEventHandler) -> AsyncEventHandler:
            self._global_handlers.append(handler)
            return handler

        return decorator

    def add_handler(
        self,
        event_type: EventType,
        handler: AsyncEventHandler,
        user_id: Optional[str] = None,
    ) -> None:
        """
        Programmatically add an event handler.

        :param event_type: Event type to handle.
        :type event_type: EventType
        :param handler: Handler function.
        :type handler: AsyncEventHandler
        :param user_id: Optional user ID for user-specific events.
        :type user_id: Optional[str]
        """
        if user_id:
            if user_id not in self._user_handlers:
                self._user_handlers[user_id] = {}
            if event_type not in self._user_handlers[user_id]:
                self._user_handlers[user_id][event_type] = []
            self._user_handlers[user_id][event_type].append(handler)
        else:
            if event_type not in self._handlers:
                self._handlers[event_type] = []
            self._handlers[event_type].append(handler)

    def remove_handler(
        self,
        event_type: EventType,
        handler: AsyncEventHandler,
        user_id: Optional[str] = None,
    ) -> bool:
        """
        Remove an event handler.

        :param event_type: Event type.
        :type event_type: EventType
        :param handler: Handler to remove.
        :type handler: AsyncEventHandler
        :param user_id: Optional user ID.
        :type user_id: Optional[str]
        :returns: True if handler was removed.
        :rtype: bool
        """
        try:
            if user_id and user_id in self._user_handlers:
                if event_type in self._user_handlers[user_id]:
                    self._user_handlers[user_id][event_type].remove(handler)
                    return True
            elif event_type in self._handlers:
                self._handlers[event_type].remove(handler)
                return True
        except ValueError:
            pass
        return False

    def remove_user_handlers(self, user_id: str) -> None:
        """
        Remove all handlers for a specific user.

        :param user_id: User ID to remove handlers for.
        :type user_id: str
        """
        if user_id in self._user_handlers:
            del self._user_handlers[user_id]

    async def publish(self, event: Event) -> None:
        """
        Publish an event to all subscribers.

        :param event: Event to publish.
        :type event: Event
        """
        handlers_to_call: List[AsyncEventHandler] = []

        handlers_to_call.extend(self._global_handlers)

        if event.type in self._handlers:
            handlers_to_call.extend(self._handlers[event.type])

        if event.user_id and event.user_id in self._user_handlers:
            if event.type in self._user_handlers[event.user_id]:
                handlers_to_call.extend(self._user_handlers[event.user_id][event.type])

        for handler in handlers_to_call:
            try:
                result = handler(event)
                if asyncio.iscoroutine(result):
                    await result
            except Exception as e:
                logger.error(f"Event handler error for {event.type}: {e}")

    async def publish_many(self, events: List[Event]) -> None:
        """
        Publish multiple events.

        :param events: List of events to publish.
        :type events: List[Event]
        """
        for event in events:
            await self.publish(event)


event_bus = EventBus()


def get_event_bus() -> EventBus:
    """
    Get the global event bus instance.

    :returns: Global EventBus instance.
    :rtype: EventBus
    """
    return event_bus
