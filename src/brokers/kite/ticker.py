"""
WebSocket Ticker Client for Kite Connect.

This module provides real-time market data streaming using WebSocket
connection to Kite Connect's ticker service.

:copyright: (c) 2025
:license: MIT
"""

import json
import struct
import logging
import threading
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

import websocket

from ...config import get_config
from ...constants import (
    WEBSOCKET_ROOT_URI,
    WEBSOCKET_CONNECT_TIMEOUT,
    WEBSOCKET_RECONNECT_MAX_DELAY,
    WEBSOCKET_RECONNECT_MAX_TRIES,
    EXCHANGE_MAP,
    MODE_FULL,
    MODE_QUOTE,
    MODE_LTP,
    KITE_HEADER_VERSION,
)
from ...exceptions import WebSocketException

log = logging.getLogger(__name__)

__version__ = "1.0.0"
__title__ = "KiteAPI"


class KiteTickerClient:
    """
    WebSocket client for streaming market data from Kite Connect.

    This class provides real-time tick data streaming with automatic
    reconnection, mode switching, and subscription management.

    :param api_key: The API key issued by Zerodha.
    :type api_key: Optional[str]
    :param access_token: The access token obtained after login.
    :type access_token: Optional[str]
    :param debug: Enable debug logging.
    :type debug: bool
    :param root: Custom WebSocket URL.
    :type root: Optional[str]
    :param reconnect: Enable auto reconnection.
    :type reconnect: bool
    :param reconnect_max_tries: Maximum reconnection attempts.
    :type reconnect_max_tries: int
    :param reconnect_max_delay: Maximum delay between reconnections.
    :type reconnect_max_delay: int
    :param connect_timeout: Connection timeout in seconds.
    :type connect_timeout: int

    Example::

        from src.ticker import KiteTickerClient

        ticker = KiteTickerClient(
            api_key="your_api_key",
            access_token="your_access_token"
        )

        def on_ticks(ws, ticks):
            for tick in ticks:
                print(f"{tick['instrument_token']}: {tick['last_price']}")

        def on_connect(ws, response):
            ws.subscribe([738561, 5633])
            ws.set_mode(ws.MODE_FULL, [738561])

        ticker.on_ticks = on_ticks
        ticker.on_connect = on_connect

        ticker.connect()
    """

    MODE_FULL = MODE_FULL
    MODE_QUOTE = MODE_QUOTE
    MODE_LTP = MODE_LTP
    EXCHANGE_MAP = EXCHANGE_MAP
    _MESSAGE_SUBSCRIBE = "subscribe"
    _MESSAGE_UNSUBSCRIBE = "unsubscribe"
    _MESSAGE_SETMODE = "mode"

    def __init__(
        self,
        api_key: Optional[str] = None,
        access_token: Optional[str] = None,
        debug: bool = False,
        root: Optional[str] = None,
        reconnect: bool = True,
        reconnect_max_tries: int = WEBSOCKET_RECONNECT_MAX_TRIES,
        reconnect_max_delay: int = WEBSOCKET_RECONNECT_MAX_DELAY,
        connect_timeout: int = WEBSOCKET_CONNECT_TIMEOUT,
    ) -> None:
        """
        Initialize WebSocket ticker client.

        :param api_key: The API key. Loads from env if not provided.
        :type api_key: Optional[str]
        :param access_token: The access token. Loads from env if not provided.
        :type access_token: Optional[str]
        :param debug: Enable debug logging.
        :type debug: bool
        :param root: Custom WebSocket URL.
        :type root: Optional[str]
        :param reconnect: Enable auto reconnection.
        :type reconnect: bool
        :param reconnect_max_tries: Maximum reconnection attempts (max 300).
        :type reconnect_max_tries: int
        :param reconnect_max_delay: Maximum delay between reconnections (min 5s).
        :type reconnect_max_delay: int
        :param connect_timeout: Connection timeout in seconds.
        :type connect_timeout: int
        """
        config = get_config()

        self.api_key = api_key or config.api_key
        self.access_token = access_token or config.access_token
        self.debug = debug or config.debug
        self.root = root or config.websocket_url or WEBSOCKET_ROOT_URI
        self.reconnect = reconnect
        self.connect_timeout = connect_timeout
        self.reconnect_max_tries = min(reconnect_max_tries, 300)
        self.reconnect_max_delay = max(reconnect_max_delay, 5)
        self.socket_url = (
            f"{self.root}?api_key={self.api_key}" f"&access_token={self.access_token}"
        )
        self.ws: Optional[websocket.WebSocketApp] = None
        self._ws_thread: Optional[threading.Thread] = None
        self._is_connected = False
        self._is_first_connect = True
        self._reconnect_count = 0
        self.subscribed_tokens: Dict[int, str] = {}
        self.on_ticks: Optional[Callable] = None
        self.on_open: Optional[Callable] = None
        self.on_close: Optional[Callable] = None
        self.on_error: Optional[Callable] = None
        self.on_connect: Optional[Callable] = None
        self.on_message: Optional[Callable] = None
        self.on_reconnect: Optional[Callable] = None
        self.on_noreconnect: Optional[Callable] = None
        self.on_order_update: Optional[Callable] = None

        if self.debug:
            log.setLevel(logging.DEBUG)
            websocket.enableTrace(True)

    def _user_agent(self) -> str:
        """
        Get user agent string.

        :returns: User agent string for API requests.
        :rtype: str
        """
        return f"{__title__}-python/{__version__}"

    def connect(self, threaded: bool = False) -> None:
        """
        Establish WebSocket connection.

        :param threaded: Run in a separate thread.
        :type threaded: bool
        :returns: None
        :rtype: None

        Example::

            ticker.connect()

            ticker.connect(threaded=True)
        """
        if not self.api_key or not self.access_token:
            raise WebSocketException(
                "API key and access token are required for WebSocket connection"
            )
        self.ws = websocket.WebSocketApp(
            self.socket_url,
            on_open=self._on_open,
            on_message=self._on_message,
            on_error=self._on_error,
            on_close=self._on_close,
            header={
                "X-Kite-Version": KITE_HEADER_VERSION,
                "User-Agent": self._user_agent(),
            },
        )

        if threaded:
            self._ws_thread = threading.Thread(target=self._run_forever, daemon=True)
            self._ws_thread.start()
        else:
            self._run_forever()

    def _run_forever(self) -> None:
        """
        Run WebSocket with reconnection logic.

        Internal loop that handles connection and automatic reconnection
        with exponential backoff.

        :returns: None
        :rtype: None
        """
        while True:
            try:
                self.ws.run_forever(
                    ping_interval=30,
                    ping_timeout=10,
                )
            except Exception as e:
                log.error(f"WebSocket error: {e}")

            if not self.reconnect:
                break

            self._reconnect_count += 1

            if self._reconnect_count > self.reconnect_max_tries:
                log.error("Maximum reconnection attempts exceeded")
                if self.on_noreconnect:
                    self.on_noreconnect(self)
                break

            if self.on_reconnect:
                self.on_reconnect(self, self._reconnect_count)
            import time

            delay = min(2**self._reconnect_count, self.reconnect_max_delay)
            log.info(f"Reconnecting in {delay} seconds...")
            time.sleep(delay)

    def is_connected(self) -> bool:
        """
        Check if WebSocket is connected.

        :returns: True if connected, False otherwise.
        :rtype: bool
        """
        return self._is_connected

    def close(self, code: int = 1000, reason: str = "") -> None:
        """
        Close the WebSocket connection.

        :param code: WebSocket close code.
        :type code: int
        :param reason: Close reason.
        :type reason: str
        """
        self.reconnect = False
        if self.ws:
            self.ws.close(code, reason)

    def stop(self) -> None:
        """
        Stop the WebSocket connection and disable reconnection.

        Use this in the on_close callback to completely stop the client.

        :returns: None
        :rtype: None
        """
        self.reconnect = False
        self.close()

    def stop_retry(self) -> None:
        """
        Stop auto retry during reconnection.

        :returns: None
        :rtype: None
        """
        self.reconnect = False

    def subscribe(self, instrument_tokens: List[int]) -> bool:
        """
        Subscribe to instrument tokens for tick data.

        :param instrument_tokens: List of instrument tokens.
        :type instrument_tokens: List[int]
        :returns: True if subscription sent successfully.
        :rtype: bool

        Example::

            ticker.subscribe([738561, 5633])
        """
        try:
            self.ws.send(
                json.dumps({"a": self._MESSAGE_SUBSCRIBE, "v": instrument_tokens})
            )
            for token in instrument_tokens:
                self.subscribed_tokens[token] = self.MODE_QUOTE

            return True
        except Exception as e:
            log.error(f"Error subscribing: {e}")
            raise WebSocketException(f"Error subscribing: {e}")

    def unsubscribe(self, instrument_tokens: List[int]) -> bool:
        """
        Unsubscribe from instrument tokens.

        :param instrument_tokens: List of instrument tokens.
        :type instrument_tokens: List[int]
        :returns: True if unsubscription sent successfully.
        :rtype: bool

        Example::

            ticker.unsubscribe([738561])
        """
        try:
            self.ws.send(
                json.dumps({"a": self._MESSAGE_UNSUBSCRIBE, "v": instrument_tokens})
            )
            for token in instrument_tokens:
                self.subscribed_tokens.pop(token, None)

            return True
        except Exception as e:
            log.error(f"Error unsubscribing: {e}")
            raise WebSocketException(f"Error unsubscribing: {e}")

    def set_mode(self, mode: str, instrument_tokens: List[int]) -> bool:
        """
        Set streaming mode for instruments.

        :param mode: Streaming mode (MODE_LTP, MODE_QUOTE, MODE_FULL).
        :type mode: str
        :param instrument_tokens: List of instrument tokens.
        :type instrument_tokens: List[int]
        :returns: True if mode change sent successfully.
        :rtype: bool

        Example::

            ticker.set_mode(ticker.MODE_FULL, [738561])

            ticker.set_mode(ticker.MODE_LTP, [5633])
        """
        try:
            self.ws.send(
                json.dumps({"a": self._MESSAGE_SETMODE, "v": [mode, instrument_tokens]})
            )
            for token in instrument_tokens:
                self.subscribed_tokens[token] = mode

            return True
        except Exception as e:
            log.error(f"Error setting mode: {e}")
            raise WebSocketException(f"Error setting mode: {e}")

    def resubscribe(self) -> None:
        """
        Resubscribe to all currently subscribed tokens.

        Useful after reconnection to restore subscriptions.

        :returns: None
        :rtype: None
        """
        modes: Dict[str, List[int]] = {}

        for token, mode in self.subscribed_tokens.items():
            if mode not in modes:
                modes[mode] = []
            modes[mode].append(token)

        for mode, tokens in modes.items():
            if self.debug:
                log.debug(f"Resubscribing: mode={mode}, tokens={tokens}")
            self.subscribe(tokens)
            self.set_mode(mode, tokens)

    def _on_open(self, ws: websocket.WebSocket) -> None:
        """
        Handle WebSocket open event.

        :param ws: The WebSocket instance.
        :type ws: websocket.WebSocket
        :returns: None
        :rtype: None
        """
        self._is_connected = True
        self._reconnect_count = 0

        if self.debug:
            log.debug("WebSocket connected")
        if not self._is_first_connect:
            self.resubscribe()

        self._is_first_connect = False

        if self.on_open:
            self.on_open(self)

        if self.on_connect:
            self.on_connect(self, None)

    def _on_close(
        self, ws: websocket.WebSocket, close_code: int, close_reason: str
    ) -> None:
        """
        Handle WebSocket close event.

        :param ws: The WebSocket instance.
        :type ws: websocket.WebSocket
        :param close_code: The close status code.
        :type close_code: int
        :param close_reason: The close reason message.
        :type close_reason: str
        :returns: None
        :rtype: None
        """
        self._is_connected = False

        if self.debug:
            log.debug(f"WebSocket closed: {close_code} - {close_reason}")

        if self.on_close:
            self.on_close(self, close_code, close_reason)

    def _on_error(self, ws: websocket.WebSocket, error: Exception) -> None:
        """
        Handle WebSocket error event.

        :param ws: The WebSocket instance.
        :type ws: websocket.WebSocket
        :param error: The exception that occurred.
        :type error: Exception
        :returns: None
        :rtype: None
        """
        log.error(f"WebSocket error: {error}")

        if self.on_error:
            self.on_error(self, 0, str(error))

    def _on_message(self, ws: websocket.WebSocket, message: bytes) -> None:
        """
        Handle WebSocket message event.

        :param ws: The WebSocket instance.
        :type ws: websocket.WebSocket
        :param message: The received message bytes.
        :type message: bytes
        :returns: None
        :rtype: None
        """
        if self.on_message:
            self.on_message(self, message, isinstance(message, bytes))

        if isinstance(message, bytes) and len(message) > 4:
            ticks = self._parse_binary(message)
            if self.on_ticks and ticks:
                self.on_ticks(self, ticks)

        elif isinstance(message, str):
            self._parse_text_message(message)

    def _parse_text_message(self, payload: str) -> None:
        """
        Parse text message for order updates and errors.

        :param payload: The JSON payload string.
        :type payload: str
        :returns: None
        :rtype: None
        """
        try:
            data = json.loads(payload)
        except ValueError:
            return

        if self.on_order_update and data.get("type") == "order" and data.get("data"):
            self.on_order_update(self, data["data"])

        if data.get("type") == "error":
            if self.on_error:
                self.on_error(self, 0, data.get("data"))

    def _parse_binary(self, data: bytes) -> List[Dict[str, Any]]:
        """
        Parse binary tick data.

        :param data: Raw binary data from WebSocket.
        :type data: bytes
        :returns: List of parsed tick dictionaries.
        :rtype: List[Dict[str, Any]]
        """
        packets = self._split_packets(data)
        ticks = []

        for packet in packets:
            instrument_token = self._unpack_int(packet, 0, 4)
            segment = instrument_token & 0xFF

            if segment == self.EXCHANGE_MAP.get("cds", 3):
                divisor = 10000000.0
            elif segment == self.EXCHANGE_MAP.get("bcd", 6):
                divisor = 10000.0
            else:
                divisor = 100.0

            tradable = segment != self.EXCHANGE_MAP.get("indices", 9)

            tick = self._parse_packet(packet, instrument_token, divisor, tradable)
            if tick:
                ticks.append(tick)

        return ticks

    def _parse_packet(
        self,
        packet: bytes,
        instrument_token: int,
        divisor: float,
        tradable: bool,
    ) -> Optional[Dict[str, Any]]:
        """
        Parse individual tick packet based on length.

        :param packet: Raw packet bytes.
        :type packet: bytes
        :param instrument_token: Instrument token.
        :type instrument_token: int
        :param divisor: Price divisor for exchange.
        :type divisor: float
        :param tradable: Whether instrument is tradable.
        :type tradable: bool
        :returns: Parsed tick dictionary or None.
        :rtype: Optional[Dict[str, Any]]
        """
        length = len(packet)

        if length == 8:
            return {
                "tradable": tradable,
                "mode": self.MODE_LTP,
                "instrument_token": instrument_token,
                "last_price": self._unpack_int(packet, 4, 8) / divisor,
            }
        elif length in (28, 32):
            mode = self.MODE_QUOTE if length == 28 else self.MODE_FULL

            tick = {
                "tradable": tradable,
                "mode": mode,
                "instrument_token": instrument_token,
                "last_price": self._unpack_int(packet, 4, 8) / divisor,
                "ohlc": {
                    "high": self._unpack_int(packet, 8, 12) / divisor,
                    "low": self._unpack_int(packet, 12, 16) / divisor,
                    "open": self._unpack_int(packet, 16, 20) / divisor,
                    "close": self._unpack_int(packet, 20, 24) / divisor,
                },
            }

            close = tick["ohlc"]["close"]
            tick["change"] = (
                (tick["last_price"] - close) * 100 / close if close != 0 else 0
            )
            if length == 32:
                try:
                    tick["exchange_timestamp"] = datetime.fromtimestamp(
                        self._unpack_int(packet, 28, 32)
                    )
                except Exception:
                    tick["exchange_timestamp"] = None

            return tick

        elif length in (44, 184):
            mode = self.MODE_QUOTE if length == 44 else self.MODE_FULL

            tick = {
                "tradable": tradable,
                "mode": mode,
                "instrument_token": instrument_token,
                "last_price": self._unpack_int(packet, 4, 8) / divisor,
                "last_traded_quantity": self._unpack_int(packet, 8, 12),
                "average_traded_price": self._unpack_int(packet, 12, 16) / divisor,
                "volume_traded": self._unpack_int(packet, 16, 20),
                "total_buy_quantity": self._unpack_int(packet, 20, 24),
                "total_sell_quantity": self._unpack_int(packet, 24, 28),
                "ohlc": {
                    "open": self._unpack_int(packet, 28, 32) / divisor,
                    "high": self._unpack_int(packet, 32, 36) / divisor,
                    "low": self._unpack_int(packet, 36, 40) / divisor,
                    "close": self._unpack_int(packet, 40, 44) / divisor,
                },
            }

            close = tick["ohlc"]["close"]
            tick["change"] = (
                (tick["last_price"] - close) * 100 / close if close != 0 else 0
            )
            if length == 184:
                try:
                    tick["last_trade_time"] = datetime.fromtimestamp(
                        self._unpack_int(packet, 44, 48)
                    )
                except Exception:
                    tick["last_trade_time"] = None

                tick["oi"] = self._unpack_int(packet, 48, 52)
                tick["oi_day_high"] = self._unpack_int(packet, 52, 56)
                tick["oi_day_low"] = self._unpack_int(packet, 56, 60)

                try:
                    tick["exchange_timestamp"] = datetime.fromtimestamp(
                        self._unpack_int(packet, 60, 64)
                    )
                except Exception:
                    tick["exchange_timestamp"] = None
                depth = {"buy": [], "sell": []}
                for i, p in enumerate(range(64, len(packet), 12)):
                    side = "sell" if i >= 5 else "buy"
                    depth[side].append(
                        {
                            "quantity": self._unpack_int(packet, p, p + 4),
                            "price": self._unpack_int(packet, p + 4, p + 8) / divisor,
                            "orders": self._unpack_int(packet, p + 8, p + 10, "H"),
                        }
                    )

                tick["depth"] = depth

            return tick

        return None

    def _unpack_int(
        self,
        data: bytes,
        start: int,
        end: int,
        byte_format: str = "I",
    ) -> int:
        """
        Unpack binary data as unsigned integer.

        :param data: Binary data.
        :type data: bytes
        :param start: Start index.
        :type start: int
        :param end: End index.
        :type end: int
        :param byte_format: Struct format (I=4 bytes, H=2 bytes).
        :type byte_format: str
        :returns: Unpacked integer.
        :rtype: int
        """
        return struct.unpack(">" + byte_format, data[start:end])[0]

    def _split_packets(self, data: bytes) -> List[bytes]:
        """
        Split binary data into individual tick packets.

        :param data: Raw binary data.
        :type data: bytes
        :returns: List of packet bytes.
        :rtype: List[bytes]
        """
        if len(data) < 2:
            return []

        num_packets = self._unpack_int(data, 0, 2, "H")
        packets = []

        j = 2
        for _ in range(num_packets):
            packet_length = self._unpack_int(data, j, j + 2, "H")
            packets.append(data[j + 2 : j + 2 + packet_length])
            j = j + 2 + packet_length

        return packets
