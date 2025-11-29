"""
WebSocket API router.

Provides real-time market data and notification streams.

:copyright: (c) 2025
:license: MIT
"""

import asyncio
import logging
from typing import Dict, Optional, Set

from fastapi import APIRouter, Depends, Query, WebSocket, WebSocketDisconnect, status

from src.auth import JWTManager, get_jwt_manager
from src.core.events import Event, EventBus, EventType, get_event_bus

logger = logging.getLogger(__name__)

router = APIRouter(tags=["WebSocket"])


class WebSocketManager:
    """
    Manages WebSocket connections for real-time updates.

    Supports multiple connection types:
    - User connections (notifications, order updates)
    - Market data connections (price feeds)
    """

    def __init__(self) -> None:
        """Initialize WebSocket manager."""

        self._user_connections: Dict[str, Set[WebSocket]] = {}

        self._market_connections: Dict[str, Set[WebSocket]] = {}

        self._all_connections: Set[WebSocket] = set()
        self._lock = asyncio.Lock()

    async def connect_user(self, websocket: WebSocket, user_id: str) -> None:
        """
        Connect a user WebSocket.

        :param websocket: WebSocket connection.
        :type websocket: WebSocket
        :param user_id: User ID.
        :type user_id: str
        """
        await websocket.accept()
        async with self._lock:
            if user_id not in self._user_connections:
                self._user_connections[user_id] = set()
            self._user_connections[user_id].add(websocket)
            self._all_connections.add(websocket)
        logger.info(f"WebSocket connected for user: {user_id}")

    async def connect_market(self, websocket: WebSocket, symbol: str) -> None:
        """
        Connect a market data WebSocket.

        :param websocket: WebSocket connection.
        :type websocket: WebSocket
        :param symbol: Symbol to subscribe to.
        :type symbol: str
        """
        await websocket.accept()
        async with self._lock:
            if symbol not in self._market_connections:
                self._market_connections[symbol] = set()
            self._market_connections[symbol].add(websocket)
            self._all_connections.add(websocket)
        logger.info(f"Market WebSocket connected for: {symbol}")

    async def disconnect(self, websocket: WebSocket) -> None:
        """
        Disconnect a WebSocket.

        :param websocket: WebSocket connection.
        :type websocket: WebSocket
        """
        async with self._lock:

            for user_id in list(self._user_connections.keys()):
                self._user_connections[user_id].discard(websocket)
                if not self._user_connections[user_id]:
                    del self._user_connections[user_id]

            for symbol in list(self._market_connections.keys()):
                self._market_connections[symbol].discard(websocket)
                if not self._market_connections[symbol]:
                    del self._market_connections[symbol]

            self._all_connections.discard(websocket)

    async def send_to_user(self, user_id: str, message: dict) -> None:
        """
        Send message to all connections for a user.

        :param user_id: User ID.
        :type user_id: str
        :param message: Message to send.
        :type message: dict
        """
        if user_id not in self._user_connections:
            return

        dead_connections = set()
        for websocket in self._user_connections[user_id]:
            try:
                await websocket.send_json(message)
            except Exception:
                dead_connections.add(websocket)

        for ws in dead_connections:
            await self.disconnect(ws)

    async def send_to_symbol(self, symbol: str, message: dict) -> None:
        """
        Send message to all subscribers of a symbol.

        :param symbol: Symbol.
        :type symbol: str
        :param message: Message to send.
        :type message: dict
        """
        if symbol not in self._market_connections:
            return

        dead_connections = set()
        for websocket in self._market_connections[symbol]:
            try:
                await websocket.send_json(message)
            except Exception:
                dead_connections.add(websocket)

        for ws in dead_connections:
            await self.disconnect(ws)

    async def broadcast(self, message: dict) -> None:
        """
        Broadcast message to all connections.

        :param message: Message to send.
        :type message: dict
        """
        dead_connections = set()
        for websocket in self._all_connections:
            try:
                await websocket.send_json(message)
            except Exception:
                dead_connections.add(websocket)

        for ws in dead_connections:
            await self.disconnect(ws)

    @property
    def user_count(self) -> int:
        """Get number of connected users."""
        return len(self._user_connections)

    @property
    def connection_count(self) -> int:
        """Get total number of connections."""
        return len(self._all_connections)


_ws_manager: Optional[WebSocketManager] = None


def get_ws_manager() -> WebSocketManager:
    """Get WebSocket manager instance."""
    global _ws_manager
    if _ws_manager is None:
        _ws_manager = WebSocketManager()
    return _ws_manager


async def authenticate_websocket(
    websocket: WebSocket,
    token: Optional[str],
    jwt_manager: JWTManager,
) -> Optional[str]:
    """
    Authenticate WebSocket connection.

    :param websocket: WebSocket connection.
    :type websocket: WebSocket
    :param token: Bearer token.
    :type token: Optional[str]
    :param jwt_manager: JWT manager.
    :type jwt_manager: JWTManager
    :returns: User ID if authenticated, None otherwise.
    :rtype: Optional[str]
    """
    if not token:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return None

    payload = jwt_manager.verify_token(token)
    if not payload:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return None

    return payload.sub


@router.websocket("/ws/user")
async def user_websocket(
    websocket: WebSocket,
    token: str = Query(..., description="Bearer token"),
    jwt_manager: JWTManager = Depends(get_jwt_manager),
    event_bus: EventBus = Depends(get_event_bus),
) -> None:
    """
    WebSocket endpoint for user notifications.

    Receives real-time updates for:
    - Order status changes
    - Rule triggers
    - Position updates
    - System notifications

    :param websocket: WebSocket connection.
    :type websocket: WebSocket
    :param token: Bearer token.
    :type token: str
    :param jwt_manager: JWT manager.
    :type jwt_manager: JWTManager
    :param event_bus: Event bus.
    :type event_bus: EventBus
    """
    user_id = await authenticate_websocket(websocket, token, jwt_manager)
    if not user_id:
        return

    ws_manager = get_ws_manager()
    await ws_manager.connect_user(websocket, user_id)

    async def send_event(event: Event) -> None:
        if event.user_id == user_id:
            await ws_manager.send_to_user(
                user_id,
                {
                    "type": event.type.value,
                    "data": event.data,
                    "timestamp": event.timestamp.isoformat(),
                },
            )

    subscriptions = [
        EventType.ORDER_PLACED,
        EventType.ORDER_EXECUTED,
        EventType.ORDER_CANCELLED,
        EventType.ORDER_REJECTED,
        EventType.RULE_TRIGGERED,
        EventType.POSITION_OPENED,
        EventType.POSITION_CLOSED,
        EventType.ALERT_TRIGGERED,
    ]

    for event_type in subscriptions:
        event_bus.subscribe(event_type, send_event)

    try:

        while True:
            data = await websocket.receive_json()

            if data.get("type") == "ping":
                await websocket.send_json({"type": "pong"})

            elif data.get("type") == "subscribe":

                pass

    except WebSocketDisconnect:
        logger.info(f"User WebSocket disconnected: {user_id}")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    finally:

        for event_type in subscriptions:
            event_bus.unsubscribe(event_type, send_event)
        await ws_manager.disconnect(websocket)


@router.websocket("/ws/market/{symbol}")
async def market_websocket(
    websocket: WebSocket,
    symbol: str,
    token: str = Query(..., description="Bearer token"),
    jwt_manager: JWTManager = Depends(get_jwt_manager),
) -> None:
    """
    WebSocket endpoint for market data.

    Streams real-time price updates for a symbol.

    :param websocket: WebSocket connection.
    :type websocket: WebSocket
    :param symbol: Symbol to subscribe to.
    :type symbol: str
    :param token: Bearer token.
    :type token: str
    :param jwt_manager: JWT manager.
    :type jwt_manager: JWTManager
    """
    user_id = await authenticate_websocket(websocket, token, jwt_manager)
    if not user_id:
        return

    ws_manager = get_ws_manager()
    await ws_manager.connect_market(websocket, symbol.upper())

    try:
        while True:
            data = await websocket.receive_json()

            if data.get("type") == "ping":
                await websocket.send_json({"type": "pong"})

    except WebSocketDisconnect:
        logger.info(f"Market WebSocket disconnected: {symbol}")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    finally:
        await ws_manager.disconnect(websocket)


class MarketDataBroadcaster:
    """Broadcasts market data to WebSocket subscribers."""

    def __init__(self, ws_manager: WebSocketManager) -> None:
        """
        Initialize broadcaster.

        :param ws_manager: WebSocket manager.
        :type ws_manager: WebSocketManager
        """
        self._ws_manager = ws_manager

    async def broadcast_price(
        self,
        symbol: str,
        price: float,
        volume: Optional[int] = None,
        change: Optional[float] = None,
    ) -> None:
        """
        Broadcast price update.

        :param symbol: Symbol.
        :type symbol: str
        :param price: Current price.
        :type price: float
        :param volume: Volume.
        :type volume: Optional[int]
        :param change: Price change.
        :type change: Optional[float]
        """
        await self._ws_manager.send_to_symbol(
            symbol.upper(),
            {
                "type": "price",
                "symbol": symbol.upper(),
                "price": price,
                "volume": volume,
                "change": change,
            },
        )

    async def broadcast_trade(
        self,
        symbol: str,
        price: float,
        quantity: int,
        side: str,
    ) -> None:
        """
        Broadcast trade.

        :param symbol: Symbol.
        :type symbol: str
        :param price: Trade price.
        :type price: float
        :param quantity: Trade quantity.
        :type quantity: int
        :param side: Trade side (buy/sell).
        :type side: str
        """
        await self._ws_manager.send_to_symbol(
            symbol.upper(),
            {
                "type": "trade",
                "symbol": symbol.upper(),
                "price": price,
                "quantity": quantity,
                "side": side,
            },
        )


def get_market_broadcaster() -> MarketDataBroadcaster:
    """Get market data broadcaster."""
    return MarketDataBroadcaster(get_ws_manager())
