"""
Abstract base classes for broker adapters.

This module defines the interface that all broker implementations must follow.
By implementing BaseBroker, you can add support for any trading platform.

:copyright: (c) 2025
:license: MIT
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Optional, Any, Callable

from src.models import (
    Order,
    OrderResult,
    Position,
    Quote,
    Tick,
    Trade,
    UserProfile,
)


class BaseBroker(ABC):
    """
    Abstract base class for broker implementations.

    All broker adapters (Kite, Webull, Robinhood, etc.) must implement
    this interface to work with the trading engine.

    :cvar BROKER_NAME: Human-readable broker name.
    :cvar BROKER_ID: Unique broker identifier for config.

    Example::

        class MyBroker(BaseBroker):
            BROKER_NAME = "My Broker"
            BROKER_ID = "mybroker"

            def authenticate(self) -> bool:

                pass

            def get_positions(self) -> List[Position]:

                pass


    """

    BROKER_NAME: str = "Base Broker"
    BROKER_ID: str = "base"

    @abstractmethod
    def authenticate(self, **kwargs: Any) -> bool:
        """
        Authenticate with the broker.

        This method should handle the authentication flow for the broker,
        whether it's API key-based, OAuth, or other mechanism.

        :param kwargs: Broker-specific authentication parameters.
        :type kwargs: Any
        :returns: True if authentication successful, False otherwise.
        :rtype: bool
        :raises AuthenticationError: If authentication fails.
        """

    @abstractmethod
    def is_authenticated(self) -> bool:
        """
        Check if currently authenticated.

        :returns: True if authenticated and session is valid.
        :rtype: bool
        """

    @abstractmethod
    def get_profile(self) -> UserProfile:
        """
        Get user profile information.

        :returns: User profile with account details.
        :rtype: UserProfile
        :raises AuthenticationError: If not authenticated.
        """

    @abstractmethod
    def get_positions(self) -> List[Position]:
        """
        Get all open positions.

        :returns: List of current positions.
        :rtype: List[Position]
        :raises AuthenticationError: If not authenticated.
        :raises BrokerError: If API call fails.
        """

    @abstractmethod
    def get_orders(self) -> List[Dict[str, Any]]:
        """
        Get all orders for the day.

        :returns: List of orders with their details.
        :rtype: List[Dict[str, Any]]
        :raises AuthenticationError: If not authenticated.
        :raises BrokerError: If API call fails.
        """

    @abstractmethod
    def get_trades(self) -> List[Trade]:
        """
        Get all trades/fills for the day.

        :returns: List of executed trades.
        :rtype: List[Trade]
        :raises AuthenticationError: If not authenticated.
        :raises BrokerError: If API call fails.
        """

    @abstractmethod
    def place_order(self, order: Order) -> OrderResult:
        """
        Place a new order.

        :param order: Order details to place.
        :type order: Order
        :returns: Order result with order ID if successful.
        :rtype: OrderResult
        :raises AuthenticationError: If not authenticated.
        :raises OrderError: If order placement fails.
        """

    @abstractmethod
    def cancel_order(self, order_id: str) -> bool:
        """
        Cancel an existing order.

        :param order_id: The order ID to cancel.
        :type order_id: str
        :returns: True if cancellation successful.
        :rtype: bool
        :raises AuthenticationError: If not authenticated.
        :raises OrderError: If cancellation fails.
        """

    @abstractmethod
    def get_quote(self, symbol: str, exchange: str) -> Quote:
        """
        Get current quote for a symbol.

        :param symbol: Trading symbol.
        :type symbol: str
        :param exchange: Exchange code.
        :type exchange: str
        :returns: Current quote data.
        :rtype: Quote
        :raises AuthenticationError: If not authenticated.
        :raises SymbolError: If symbol not found.
        """

    @abstractmethod
    def get_ltp(self, symbols: List[str]) -> Dict[str, float]:
        """
        Get last traded price for multiple symbols.

        :param symbols: List of symbols in "EXCHANGE:SYMBOL" format.
        :type symbols: List[str]
        :returns: Dictionary mapping symbol to LTP.
        :rtype: Dict[str, float]
        :raises AuthenticationError: If not authenticated.
        """

    def get_instrument_token(self, symbol: str, exchange: str) -> Optional[str]:
        """
        Get broker-specific instrument token for a symbol.

        Override this method if the broker uses instrument tokens
        for WebSocket subscriptions.

        :param symbol: Trading symbol.
        :type symbol: str
        :param exchange: Exchange code.
        :type exchange: str
        :returns: Instrument token or None if not applicable.
        :rtype: Optional[str]
        """
        return None

    def close(self) -> None:
        """
        Clean up resources and close connections.

        Override this method to handle cleanup like closing
        HTTP sessions, cancelling pending requests, etc.
        """


class BaseTicker(ABC):
    """
    Abstract base class for real-time market data streaming.

    Broker adapters that support WebSocket streaming should implement
    this interface alongside BaseBroker.

    :cvar MODE_LTP: LTP-only mode (minimal data).
    :cvar MODE_QUOTE: Quote mode (bid/ask/volume).
    :cvar MODE_FULL: Full mode (all available data).
    """

    MODE_LTP: str = "ltp"
    MODE_QUOTE: str = "quote"
    MODE_FULL: str = "full"

    on_ticks: Optional[Callable[[Any, List[Tick]], None]] = None
    on_connect: Optional[Callable[[Any, Any], None]] = None
    on_close: Optional[Callable[[Any, int, str], None]] = None
    on_error: Optional[Callable[[Any, Exception], None]] = None
    on_reconnect: Optional[Callable[[Any, int], None]] = None

    @abstractmethod
    def connect(self, threaded: bool = False) -> None:
        """
        Establish WebSocket connection.

        :param threaded: Run in background thread if True.
        :type threaded: bool
        """

    @abstractmethod
    def close(self) -> None:
        """
        Close WebSocket connection.
        """

    @abstractmethod
    def is_connected(self) -> bool:
        """
        Check if WebSocket is connected.

        :returns: True if connected.
        :rtype: bool
        """

    @abstractmethod
    def subscribe(self, instrument_tokens: List[str]) -> None:
        """
        Subscribe to instruments for tick data.

        :param instrument_tokens: List of instrument tokens to subscribe.
        :type instrument_tokens: List[str]
        """

    @abstractmethod
    def unsubscribe(self, instrument_tokens: List[str]) -> None:
        """
        Unsubscribe from instruments.

        :param instrument_tokens: List of instrument tokens to unsubscribe.
        :type instrument_tokens: List[str]
        """

    @abstractmethod
    def set_mode(self, mode: str, instrument_tokens: List[str]) -> None:
        """
        Set subscription mode for instruments.

        :param mode: Subscription mode (MODE_LTP, MODE_QUOTE, MODE_FULL).
        :type mode: str
        :param instrument_tokens: List of instrument tokens.
        :type instrument_tokens: List[str]
        """

    def resubscribe(self) -> None:
        """
        Resubscribe to all previously subscribed instruments.

        Override this for custom reconnection handling.
        """
