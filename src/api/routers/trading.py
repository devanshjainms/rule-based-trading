"""
Trading API router.

Provides endpoints for trade management and execution.

:copyright: (c) 2025
:license: MIT
"""

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Annotated, Any, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from src.api.schemas.trading import (
    PlaceOrderRequest,
    ModifyOrderRequest,
    OrderResponse,
    PositionResponse,
    TradeLogResponse,
    EngineStatusResponse,
)
from src.auth import CurrentUser, RateLimiter
from src.core.events import Event, EventBus, EventType, get_event_bus

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/trading", tags=["Trading"])


order_limiter = RateLimiter(requests=60, window=60, key_prefix="order:")
data_limiter = RateLimiter(requests=300, window=60, key_prefix="data:")


@dataclass
class TradingContext:
    """
    Trading context containing user info and broker client.

    This is a lightweight context specifically for trading operations,
    using per-user broker credentials from the database.
    """

    user_id: str
    broker_client: Any


async def get_broker_auth_url(user_id: str) -> Optional[str]:
    """
    Get OAuth URL for broker authentication.

    If user has broker credentials stored but not connected,
    generate a new OAuth URL. Otherwise return None.
    """
    from src.database import get_database_manager
    from src.database.repositories import PostgresBrokerAccountRepository
    from src.utils.encryption import decrypt_credential
    from src.auth import get_oauth_manager

    db = get_database_manager()
    async with db.session() as session:
        repo = PostgresBrokerAccountRepository(session)
        account = await repo.get_active_by_user(user_id)

        if account and account.api_key:
            try:

                api_key = decrypt_credential(account.api_key)
                api_secret = decrypt_credential(account.api_secret)

                oauth_manager = get_oauth_manager()
                auth_url, _ = await oauth_manager.start_oauth_flow(
                    user_id=user_id,
                    broker=account.broker_id,
                    api_key=api_key,
                    api_secret=api_secret,
                )
                return auth_url
            except Exception as e:
                logger.error(f"Failed to generate auth URL: {e}")

    return None


async def get_trading_context(
    user_id: CurrentUser,
) -> TradingContext:
    """
    Get trading context with broker client for current user.

    Retrieves the user's broker credentials from the database
    and creates a broker client. If no broker is connected,
    returns JSON error with auth URL for client to handle redirect.

    :param user_id: Current authenticated user ID.
    :returns: Trading context with broker client.
    :raises HTTPException: If no broker connected (428 with auth_url).
    """
    from src.brokers.factory import get_broker_factory

    factory = get_broker_factory()
    client = await factory.get_client(user_id)

    if not client:

        auth_url = await get_broker_auth_url(user_id)

        response_data = {
            "error": "broker_not_connected",
            "message": "No active broker connection. Please connect your broker first.",
            "action": "redirect_to_broker_auth",
            "supported_brokers": ["kite"],
        }

        if auth_url:
            response_data["auth_url"] = auth_url
            response_data["instructions"] = [
                "1. Redirect user to auth_url to login to broker",
                "2. After broker login, callback will be sent to /auth/broker/callback",
                "3. Retry this request after successful broker connection",
            ]
        else:
            response_data["auth_endpoint"] = "/user/broker"
            response_data["instructions"] = [
                "1. POST to /user/broker with your broker API key and secret",
                "2. Redirect user to the returned auth_url",
                "3. After broker login, handle callback at /auth/broker/callback",
                "4. Retry this request after successful broker connection",
            ]

        raise HTTPException(
            status_code=status.HTTP_428_PRECONDITION_REQUIRED,
            detail=response_data,
            headers={"X-Auth-Url": auth_url} if auth_url else None,
        )

    return TradingContext(user_id=user_id, broker_client=client)


TradingCtx = Annotated[TradingContext, Depends(get_trading_context)]


@router.post(
    "/orders",
    response_model=OrderResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(order_limiter)],
)
async def place_order(
    request: PlaceOrderRequest,
    context: TradingCtx,
    event_bus: EventBus = Depends(get_event_bus),
) -> OrderResponse:
    """
    Place a new order.

    :param request: Order details.
    :type request: PlaceOrderRequest
    :param context: Current user context.
    :type context: UserContext
    :param event_bus: Event bus.
    :type event_bus: EventBus
    :returns: Order response.
    :rtype: OrderResponse
    :raises HTTPException: If order placement fails or no broker connected.
    """
    try:

        order = await context.broker_client.place_order(
            symbol=request.symbol,
            quantity=request.quantity,
            order_type=request.order_type,
            position_type=request.position_type,
            price=request.price,
            trigger_price=request.trigger_price,
            tag=request.tag,
        )

        await event_bus.emit(
            Event(
                type=EventType.ORDER_PLACED,
                data={
                    "order_id": order.order_id,
                    "symbol": request.symbol,
                    "quantity": request.quantity,
                },
                user_id=context.user_id,
            )
        )

        logger.info(f"Order placed: {order.order_id} for user {context.user_id}")

        return OrderResponse(
            order_id=order.order_id,
            symbol=request.symbol,
            quantity=request.quantity,
            order_type=request.order_type.value,
            position_type=request.position_type.value,
            status=order.status.value,
            price=request.price,
            placed_at=datetime.utcnow(),
        )

    except Exception as e:
        logger.error(f"Order placement failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Order placement failed: {str(e)}",
        )


@router.get("/orders", response_model=List[OrderResponse])
async def get_orders(
    context: TradingCtx,
    status_filter: Optional[str] = Query(default=None, alias="status"),
    limit: int = Query(default=50, le=100),
) -> List[OrderResponse]:
    """
    Get user's orders.

    :param context: Current user context.
    :type context: UserContext
    :param status_filter: Filter by order status.
    :type status_filter: Optional[str]
    :param limit: Maximum orders to return.
    :type limit: int
    :returns: List of orders.
    :rtype: List[OrderResponse]
    """
    orders = await context.broker_client.get_orders()

    if status_filter:
        orders = [o for o in orders if o.status.value == status_filter]

    return [
        OrderResponse(
            order_id=o.order_id,
            symbol=o.symbol,
            quantity=o.quantity,
            order_type=o.order_type.value,
            position_type=o.position_type.value,
            status=o.status.value,
            price=o.price,
            placed_at=o.placed_at or datetime.utcnow(),
        )
        for o in orders[:limit]
    ]


@router.get("/orders/{order_id}", response_model=OrderResponse)
async def get_order(
    order_id: str,
    context: TradingCtx,
) -> OrderResponse:
    """
    Get specific order by ID.

    :param order_id: Order ID.
    :type order_id: str
    :param context: Current user context.
    :type context: UserContext
    :returns: Order details.
    :rtype: OrderResponse
    :raises HTTPException: If order not found.
    """
    order = await context.broker_client.get_order(order_id)
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found",
        )

    return OrderResponse(
        order_id=order.order_id,
        symbol=order.symbol,
        quantity=order.quantity,
        order_type=order.order_type.value,
        position_type=order.position_type.value,
        status=order.status.value,
        price=order.price,
        placed_at=order.placed_at or datetime.utcnow(),
    )


@router.put("/orders/{order_id}", response_model=OrderResponse)
async def modify_order(
    order_id: str,
    request: ModifyOrderRequest,
    context: TradingCtx,
    event_bus: EventBus = Depends(get_event_bus),
) -> OrderResponse:
    """
    Modify an existing order.

    :param order_id: Order ID.
    :type order_id: str
    :param request: Modification details.
    :type request: ModifyOrderRequest
    :param context: Current user context.
    :type context: UserContext
    :param event_bus: Event bus.
    :type event_bus: EventBus
    :returns: Updated order.
    :rtype: OrderResponse
    """
    try:
        order = await context.broker_client.modify_order(
            order_id=order_id,
            quantity=request.quantity,
            price=request.price,
            trigger_price=request.trigger_price,
        )

        await event_bus.emit(
            Event(
                type=EventType.ORDER_MODIFIED,
                data={"order_id": order_id},
                user_id=context.user_id,
            )
        )

        return OrderResponse(
            order_id=order.order_id,
            symbol=order.symbol,
            quantity=order.quantity,
            order_type=order.order_type.value,
            position_type=order.position_type.value,
            status=order.status.value,
            price=order.price,
            placed_at=order.placed_at or datetime.utcnow(),
        )

    except Exception as e:
        logger.error(f"Order modification failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Order modification failed: {str(e)}",
        )


@router.delete("/orders/{order_id}", status_code=status.HTTP_204_NO_CONTENT)
async def cancel_order(
    order_id: str,
    context: TradingCtx,
    event_bus: EventBus = Depends(get_event_bus),
) -> None:
    """
    Cancel an order.

    :param order_id: Order ID.
    :type order_id: str
    :param context: Current user context.
    :type context: UserContext
    :param event_bus: Event bus.
    :type event_bus: EventBus
    """
    try:
        await context.broker_client.cancel_order(order_id)

        await event_bus.emit(
            Event(
                type=EventType.ORDER_CANCELLED,
                data={"order_id": order_id},
                user_id=context.user_id,
            )
        )

        logger.info(f"Order cancelled: {order_id}")

    except Exception as e:
        logger.error(f"Order cancellation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Order cancellation failed: {str(e)}",
        )


@router.get("/positions", response_model=List[PositionResponse])
async def get_positions(
    context: TradingCtx,
) -> List[PositionResponse]:
    """
    Get current positions.

    :param context: Current user context.
    :type context: UserContext
    :returns: List of positions.
    :rtype: List[PositionResponse]
    """
    positions = await context.broker_client.get_positions()

    return [
        PositionResponse(
            symbol=p.symbol,
            quantity=p.quantity,
            average_price=p.average_price,
            current_price=p.current_price,
            pnl=p.pnl,
            pnl_percent=p.pnl_percent,
            position_type=p.position_type.value,
        )
        for p in positions
    ]


@router.post("/positions/{symbol}/close", status_code=status.HTTP_204_NO_CONTENT)
async def close_position(
    symbol: str,
    context: TradingCtx,
    event_bus: EventBus = Depends(get_event_bus),
) -> None:
    """
    Close a position.

    :param symbol: Symbol to close.
    :type symbol: str
    :param context: Current user context.
    :type context: UserContext
    :param event_bus: Event bus.
    :type event_bus: EventBus
    """
    try:
        await context.broker_client.close_position(symbol)

        await event_bus.emit(
            Event(
                type=EventType.POSITION_CLOSED,
                data={"symbol": symbol},
                user_id=context.user_id,
            )
        )

        logger.info(f"Position closed: {symbol}")

    except Exception as e:
        logger.error(f"Position close failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Position close failed: {str(e)}",
        )


@router.get("/trades", response_model=List[TradeLogResponse])
async def get_trade_history(
    user_id: CurrentUser,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    symbol: Optional[str] = None,
    limit: int = Query(default=50, le=500),
) -> List[TradeLogResponse]:
    """
    Get trade history.

    :param user_id: Current user ID.
    :type user_id: str
    :param start_date: Start date filter.
    :type start_date: Optional[datetime]
    :param end_date: End date filter.
    :type end_date: Optional[datetime]
    :param symbol: Symbol filter.
    :type symbol: Optional[str]
    :param limit: Maximum trades to return.
    :type limit: int
    :returns: List of trades.
    :rtype: List[TradeLogResponse]
    """
    from src.database import get_database_manager
    from src.database.repositories import PostgresTradeLogRepository

    db = get_database_manager()
    trade_repo = PostgresTradeLogRepository(db.session_factory)

    trades = await trade_repo.get_by_user(
        user_id=user_id,
        start_date=start_date,
        end_date=end_date,
        symbol=symbol,
        limit=limit,
    )

    return [
        TradeLogResponse(
            id=str(t.id),
            symbol=t.symbol,
            quantity=t.quantity,
            entry_price=t.entry_price,
            exit_price=t.exit_price,
            pnl=t.pnl,
            rule_id=str(t.rule_id) if t.rule_id else None,
            entry_time=t.entry_time,
            exit_time=t.exit_time,
        )
        for t in trades
    ]


_user_engines: dict = {}


@router.get("/engine/status", response_model=EngineStatusResponse)
async def get_engine_status(user_id: CurrentUser) -> EngineStatusResponse:
    """
    Get trading engine status for current user.

    :param user_id: Current authenticated user.
    :returns: Engine status.
    """
    engine = _user_engines.get(user_id)

    if engine is None:
        return EngineStatusResponse(
            running=False,
            user_id=user_id,
            message="Engine not initialized. Start it with POST /trading/engine/start",
        )

    return EngineStatusResponse(
        running=engine.get("running", False),
        user_id=user_id,
        active_trades=engine.get("active_trades", 0),
        rules_loaded=engine.get("rules_loaded", 0),
        started_at=engine.get("started_at"),
    )


@router.post("/engine/start", response_model=EngineStatusResponse)
async def start_engine(
    context: TradingCtx,
    event_bus: EventBus = Depends(get_event_bus),
) -> EngineStatusResponse:
    """
    Start the trading engine for current user.

    Requires an active broker connection.

    :param context: Trading context with broker client.
    :param event_bus: Event bus for notifications.
    :returns: Engine status after starting.
    :raises HTTPException: If engine already running.
    """
    user_id = context.user_id

    if user_id in _user_engines and _user_engines[user_id].get("running"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Engine is already running",
        )

    _user_engines[user_id] = {
        "running": True,
        "active_trades": 0,
        "rules_loaded": 0,
        "started_at": datetime.now(),
        "broker_client": context.broker_client,
    }

    await event_bus.emit(
        Event(
            type=EventType.ENGINE_STARTED,
            data={"user_id": user_id},
        )
    )

    logger.info(f"Trading engine started for user {user_id}")

    return EngineStatusResponse(
        running=True,
        user_id=user_id,
        started_at=_user_engines[user_id]["started_at"],
        message="Engine started successfully",
    )


@router.post("/engine/stop", response_model=EngineStatusResponse)
async def stop_engine(
    user_id: CurrentUser,
    event_bus: EventBus = Depends(get_event_bus),
) -> EngineStatusResponse:
    """
    Stop the trading engine for current user.

    :param user_id: Current authenticated user.
    :param event_bus: Event bus for notifications.
    :returns: Engine status after stopping.
    :raises HTTPException: If engine not running.
    """
    if user_id not in _user_engines or not _user_engines[user_id].get("running"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Engine is not running",
        )

    _user_engines[user_id]["running"] = False

    await event_bus.emit(
        Event(
            type=EventType.ENGINE_STOPPED,
            data={"user_id": user_id},
        )
    )

    logger.info(f"Trading engine stopped for user {user_id}")

    return EngineStatusResponse(
        running=False,
        user_id=user_id,
        message="Engine stopped successfully",
    )
