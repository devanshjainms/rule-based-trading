"""
Core infrastructure package.

This package provides foundational components for building
a scalable, extensible trading system:

- **repositories**: Abstract data access layer for database agnostic storage
- **events**: Event bus for publish/subscribe architecture
- **sessions**: Multi-user session management
- **container**: Dependency injection container
- **services**: Business logic service layer

:copyright: (c) 2025
:license: MIT

Usage::

    from src.core import (

        EventBus, Event, EventType, get_event_bus,


        SessionManager, UserSession, UserContext, get_session_manager,


        Container, Lifecycle, get_container,


        TradingService, RuleExecutionService,


        BaseRepository, SessionRepository, RulesRepository,
    )


    bus = get_event_bus()

    @bus.subscribe(EventType.ORDER_PLACED)
    async def on_order(event):
        print(f"Order placed: {event.data}")


    manager = get_session_manager()
    context = await manager.create_session(
        user_id="user123",
        broker_id="kite",
        access_token="token",
        broker=broker_client,
    )


    service = TradingService()
    await service.place_order(
        user_id="user123",
        symbol="RELIANCE",
        exchange="NSE",
        quantity=10,
        side="BUY",
    )
"""

from src.core.container import Container, Lifecycle, get_container, configure_container
from src.core.events import Event, EventBus, EventType, get_event_bus
from src.core.repositories import (
    BaseRepository,
    RulesRepository,
    SessionRepository,
    TradeLogRepository,
)
from src.core.services import (
    BaseService,
    RuleExecutionService,
    TradingService,
)
from src.core.sessions import (
    SessionManager,
    UserContext,
    UserSession,
    get_session_manager,
)

__all__ = [
    "Container",
    "Lifecycle",
    "get_container",
    "configure_container",
    "Event",
    "EventBus",
    "EventType",
    "get_event_bus",
    "BaseRepository",
    "SessionRepository",
    "RulesRepository",
    "TradeLogRepository",
    "BaseService",
    "TradingService",
    "RuleExecutionService",
    "SessionManager",
    "UserSession",
    "UserContext",
    "get_session_manager",
]
