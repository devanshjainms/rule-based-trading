"""
Kite Connect API Client.

This module provides the main client class for interacting with
the Zerodha Kite Connect REST API.

:copyright: (c) 2025
:license: MIT
"""

import json
import logging
from typing import Any, Callable, Dict, List, Optional, Union, cast
from datetime import datetime
from urllib.parse import urljoin

import requests
from requests.adapters import HTTPAdapter
import urllib3

from .config import Config, get_config
from .constants import (
    API_ROUTES,
    DEFAULT_ROOT_URI,
    DEFAULT_LOGIN_URI,
    DEFAULT_TIMEOUT,
    KITE_HEADER_VERSION,
    PRODUCT_MIS,
    PRODUCT_CNC,
    PRODUCT_NRML,
    PRODUCT_CO,
    ORDER_TYPE_MARKET,
    ORDER_TYPE_LIMIT,
    ORDER_TYPE_SL,
    ORDER_TYPE_SLM,
    VARIETY_REGULAR,
    VARIETY_AMO,
    VARIETY_CO,
    VARIETY_ICEBERG,
    VARIETY_AUCTION,
    TRANSACTION_TYPE_BUY,
    TRANSACTION_TYPE_SELL,
    VALIDITY_DAY,
    VALIDITY_IOC,
    VALIDITY_TTL,
    EXCHANGE_NSE,
    EXCHANGE_BSE,
    EXCHANGE_NFO,
    EXCHANGE_MCX,
    GTT_TYPE_OCO,
    GTT_TYPE_SINGLE,
)
from .exceptions import (
    KiteException,
    GeneralException,
    TokenException,
    InputException,
    DataException,
    NetworkException,
    get_exception_class,
)
from .utils import (
    generate_checksum,
    format_response,
    format_historical_data,
    parse_instruments_csv,
    parse_mf_instruments_csv,
    clean_none_values,
    format_datetime,
)

log = logging.getLogger(__name__)

__version__ = "1.0.0"
__title__ = "KiteAPI"


class KiteClient:
    """
    The Kite Connect API client class.

    This class provides methods to interact with all Kite Connect
    REST API endpoints for trading, portfolio management, and
    market data.

    In production, you may initialize a single instance of this
    class per ``api_key``.

    :param api_key: The API key issued by Zerodha.
    :type api_key: Optional[str]
    :param access_token: The access token obtained after login.
    :type access_token: Optional[str]
    :param root: Custom API root URL.
    :type root: Optional[str]
    :param debug: Enable debug logging.
    :type debug: bool
    :param timeout: Request timeout in seconds.
    :type timeout: int
    :param proxies: Proxy configuration dictionary.
    :type proxies: Optional[Dict]
    :param pool: Connection pool configuration.
    :type pool: Optional[Dict]
    :param disable_ssl: Disable SSL verification.
    :type disable_ssl: bool

    Example::

        from src.client import KiteClient

        client = KiteClient(api_key="your_api_key")

        print(client.login_url())

        client.set_access_token("your_access_token")

        order_id = client.place_order(
            tradingsymbol="INFY",
            exchange="NSE",
            transaction_type="BUY",
            quantity=1,
            product="CNC",
            order_type="MARKET"
        )
    """

    PRODUCT_MIS = PRODUCT_MIS
    PRODUCT_CNC = PRODUCT_CNC
    PRODUCT_NRML = PRODUCT_NRML
    PRODUCT_CO = PRODUCT_CO

    ORDER_TYPE_MARKET = ORDER_TYPE_MARKET
    ORDER_TYPE_LIMIT = ORDER_TYPE_LIMIT
    ORDER_TYPE_SL = ORDER_TYPE_SL
    ORDER_TYPE_SLM = ORDER_TYPE_SLM

    VARIETY_REGULAR = VARIETY_REGULAR
    VARIETY_AMO = VARIETY_AMO
    VARIETY_CO = VARIETY_CO
    VARIETY_ICEBERG = VARIETY_ICEBERG
    VARIETY_AUCTION = VARIETY_AUCTION

    TRANSACTION_TYPE_BUY = TRANSACTION_TYPE_BUY
    TRANSACTION_TYPE_SELL = TRANSACTION_TYPE_SELL

    VALIDITY_DAY = VALIDITY_DAY
    VALIDITY_IOC = VALIDITY_IOC
    VALIDITY_TTL = VALIDITY_TTL

    EXCHANGE_NSE = EXCHANGE_NSE
    EXCHANGE_BSE = EXCHANGE_BSE
    EXCHANGE_NFO = EXCHANGE_NFO
    EXCHANGE_MCX = EXCHANGE_MCX

    GTT_TYPE_OCO = GTT_TYPE_OCO
    GTT_TYPE_SINGLE = GTT_TYPE_SINGLE

    def __init__(
        self,
        api_key: Optional[str] = None,
        access_token: Optional[str] = None,
        root: Optional[str] = None,
        debug: bool = False,
        timeout: Optional[int] = None,
        proxies: Optional[Dict] = None,
        pool: Optional[Dict] = None,
        disable_ssl: bool = False,
    ) -> None:
        """
        Initialize a new Kite Connect client instance.

        :param api_key: The API key issued by Zerodha. If not provided,
            loads from environment variable KITE_API_KEY.
        :type api_key: Optional[str]
        :param access_token: The access token obtained after login flow.
            Pre-login, this will default to None.
        :type access_token: Optional[str]
        :param root: Custom API endpoint root. Unless you explicitly
            want to send API requests to a non-default endpoint, this
            can be ignored.
        :type root: Optional[str]
        :param debug: If set to True, will log requests and responses.
        :type debug: bool
        :param timeout: Request timeout in seconds. Defaults to 7 seconds.
        :type timeout: Optional[int]
        :param proxies: Proxy configuration for requests.
        :type proxies: Optional[Dict]
        :param pool: Connection pool configuration for HTTPAdapter.
        :type pool: Optional[Dict]
        :param disable_ssl: Disable SSL verification for custom root URLs.
        :type disable_ssl: bool
        """
        config = get_config()

        self.api_key = api_key or config.api_key
        self.access_token = access_token or config.access_token
        self.debug = debug or config.debug
        self.disable_ssl = disable_ssl or config.disable_ssl
        self.root = root or config.root_url or DEFAULT_ROOT_URI
        self.timeout = timeout or config.timeout or DEFAULT_TIMEOUT
        self.proxies = proxies or config.proxy or {}
        self.session_expiry_hook: Optional[Callable] = None
        self._routes = API_ROUTES
        self.reqsession = requests.Session()
        if pool:
            reqadapter = HTTPAdapter(**pool)
            self.reqsession.mount("https://", reqadapter)
        if self.disable_ssl:
            urllib3.disable_warnings()

        if self.debug:
            log.setLevel(logging.DEBUG)

    def set_session_expiry_hook(self, method: Callable) -> None:
        """
        Set a callback hook for session expiry errors.

        An ``access_token`` can become invalid for various reasons.
        This callback is triggered when a TokenException is raised,
        allowing you to handle re-authentication.

        :param method: Callback function to handle session expiry.
        :type method: Callable
        :raises TypeError: If method is not callable.

        Example::

            def on_session_expiry():
                print("Session expired, please login again")

            client.set_session_expiry_hook(on_session_expiry)
        """
        if not callable(method):
            raise TypeError("Invalid input type. Only functions are accepted.")
        self.session_expiry_hook = method

    def set_access_token(self, access_token: str) -> None:
        """
        Set the access token for authenticated requests.

        :param access_token: The access token obtained after login.
        :type access_token: str

        Example::

            client.set_access_token("your_access_token")
        """
        self.access_token = access_token

    def login_url(self) -> str:
        """
        Get the remote login URL for initiating the login flow.

        The user should be redirected to this URL to authenticate.

        :returns: The login URL.
        :rtype: str

        Example::

            url = client.login_url()
            print(f"Please visit: {url}")
        """
        return f"{DEFAULT_LOGIN_URI}?api_key={self.api_key}&v={KITE_HEADER_VERSION}"

    def generate_session(self, request_token: str, api_secret: str) -> Dict[str, Any]:
        """
        Generate user session by exchanging request_token for access_token.

        The access token is automatically set if session is retrieved
        successfully.

        :param request_token: Token obtained from login redirect URL.
        :type request_token: str
        :param api_secret: The API secret issued with the API key.
        :type api_secret: str
        :returns: Session data including access_token and user info.
        :rtype: Dict[str, Any]

        Example::

            data = client.generate_session(
                request_token="request_token_from_url",
                api_secret="your_api_secret"
            )
            print(f"Access token: {data['access_token']}")
        """
        checksum = generate_checksum(self.api_key, request_token, api_secret)

        resp = self._post(
            "api.token",
            params={
                "api_key": self.api_key,
                "request_token": request_token,
                "checksum": checksum,
            },
        )

        if "access_token" in resp:
            self.set_access_token(resp["access_token"])

        return format_response(resp)

    def invalidate_access_token(
        self, access_token: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Invalidate the access token (logout).

        :param access_token: Token to invalidate. Defaults to current token.
        :type access_token: Optional[str]
        :returns: API response.
        :rtype: Dict[str, Any]
        """
        access_token = access_token or self.access_token
        return self._delete(
            "api.token.invalidate",
            params={"api_key": self.api_key, "access_token": access_token},
        )

    def renew_access_token(self, refresh_token: str, api_secret: str) -> Dict[str, Any]:
        """
        Renew access token using refresh token.

        :param refresh_token: The refresh token from previous login.
        :type refresh_token: str
        :param api_secret: The API secret.
        :type api_secret: str
        :returns: New session data with access_token.
        :rtype: Dict[str, Any]
        """
        checksum = generate_checksum(self.api_key, refresh_token, api_secret)

        resp = self._post(
            "api.token.renew",
            params={
                "api_key": self.api_key,
                "refresh_token": refresh_token,
                "checksum": checksum,
            },
        )

        if "access_token" in resp:
            self.set_access_token(resp["access_token"])

        return resp

    def profile(self) -> Dict[str, Any]:
        """
        Get user profile details.

        :returns: User profile data.
        :rtype: Dict[str, Any]

        Example::

            profile = client.profile()
            print(f"User: {profile['user_name']}")
        """
        return self._get("user.profile")

    def margins(self, segment: Optional[str] = None) -> Dict[str, Any]:
        """
        Get account balance and margin details.

        :param segment: Trading segment (equity/commodity).
        :type segment: Optional[str]
        :returns: Margin details.
        :rtype: Dict[str, Any]

        Example::

            margins = client.margins()
            equity_margins = client.margins(segment="equity")
        """
        if segment:
            return self._get("user.margins.segment", url_args={"segment": segment})
        return self._get("user.margins")

    def place_order(
        self,
        variety: str,
        exchange: str,
        tradingsymbol: str,
        transaction_type: str,
        quantity: int,
        product: str,
        order_type: str,
        price: Optional[float] = None,
        validity: Optional[str] = None,
        validity_ttl: Optional[int] = None,
        disclosed_quantity: Optional[int] = None,
        trigger_price: Optional[float] = None,
        iceberg_legs: Optional[int] = None,
        iceberg_quantity: Optional[int] = None,
        auction_number: Optional[int] = None,
        tag: Optional[str] = None,
    ) -> str:
        """
        Place an order.

        :param variety: Order variety (regular, amo, co, iceberg, auction).
        :type variety: str
        :param exchange: Exchange name (NSE, BSE, NFO, etc.).
        :type exchange: str
        :param tradingsymbol: Trading symbol of the instrument.
        :type tradingsymbol: str
        :param transaction_type: BUY or SELL.
        :type transaction_type: str
        :param quantity: Order quantity.
        :type quantity: int
        :param product: Product type (MIS, CNC, NRML).
        :type product: str
        :param order_type: Order type (MARKET, LIMIT, SL, SL-M).
        :type order_type: str
        :param price: Price for LIMIT orders.
        :type price: Optional[float]
        :param validity: Order validity (DAY, IOC, TTL).
        :type validity: Optional[str]
        :param validity_ttl: TTL validity in minutes.
        :type validity_ttl: Optional[int]
        :param disclosed_quantity: Disclosed quantity.
        :type disclosed_quantity: Optional[int]
        :param trigger_price: Trigger price for SL orders.
        :type trigger_price: Optional[float]
        :param iceberg_legs: Number of iceberg legs.
        :type iceberg_legs: Optional[int]
        :param iceberg_quantity: Iceberg quantity per leg.
        :type iceberg_quantity: Optional[int]
        :param auction_number: Auction number.
        :type auction_number: Optional[int]
        :param tag: Optional order tag (max 20 chars).
        :type tag: Optional[str]
        :returns: Order ID.
        :rtype: str

        Example::

            order_id = client.place_order(
                variety=client.VARIETY_REGULAR,
                exchange=client.EXCHANGE_NSE,
                tradingsymbol="INFY",
                transaction_type=client.TRANSACTION_TYPE_BUY,
                quantity=1,
                product=client.PRODUCT_CNC,
                order_type=client.ORDER_TYPE_MARKET
            )
        """
        params = {
            "exchange": exchange,
            "tradingsymbol": tradingsymbol,
            "transaction_type": transaction_type,
            "quantity": quantity,
            "product": product,
            "order_type": order_type,
            "price": price,
            "validity": validity,
            "validity_ttl": validity_ttl,
            "disclosed_quantity": disclosed_quantity,
            "trigger_price": trigger_price,
            "iceberg_legs": iceberg_legs,
            "iceberg_quantity": iceberg_quantity,
            "auction_number": auction_number,
            "tag": tag,
        }

        params = clean_none_values(params)

        return self._post("order.place", url_args={"variety": variety}, params=params)[
            "order_id"
        ]

    def modify_order(
        self,
        variety: str,
        order_id: str,
        parent_order_id: Optional[str] = None,
        quantity: Optional[int] = None,
        price: Optional[float] = None,
        order_type: Optional[str] = None,
        trigger_price: Optional[float] = None,
        validity: Optional[str] = None,
        disclosed_quantity: Optional[int] = None,
    ) -> str:
        """
        Modify an open order.

        :param variety: Order variety.
        :type variety: str
        :param order_id: Order ID to modify.
        :type order_id: str
        :param parent_order_id: Parent order ID (for CO).
        :type parent_order_id: Optional[str]
        :param quantity: New quantity.
        :type quantity: Optional[int]
        :param price: New price.
        :type price: Optional[float]
        :param order_type: New order type.
        :type order_type: Optional[str]
        :param trigger_price: New trigger price.
        :type trigger_price: Optional[float]
        :param validity: New validity.
        :type validity: Optional[str]
        :param disclosed_quantity: New disclosed quantity.
        :type disclosed_quantity: Optional[int]
        :returns: Order ID.
        :rtype: str
        """
        params = {
            "parent_order_id": parent_order_id,
            "quantity": quantity,
            "price": price,
            "order_type": order_type,
            "trigger_price": trigger_price,
            "validity": validity,
            "disclosed_quantity": disclosed_quantity,
        }

        params = clean_none_values(params)

        return self._put(
            "order.modify",
            url_args={"variety": variety, "order_id": order_id},
            params=params,
        )["order_id"]

    def cancel_order(
        self,
        variety: str,
        order_id: str,
        parent_order_id: Optional[str] = None,
    ) -> str:
        """
        Cancel an order.

        :param variety: Order variety.
        :type variety: str
        :param order_id: Order ID to cancel.
        :type order_id: str
        :param parent_order_id: Parent order ID (for CO).
        :type parent_order_id: Optional[str]
        :returns: Order ID.
        :rtype: str
        """
        return self._delete(
            "order.cancel",
            url_args={"variety": variety, "order_id": order_id},
            params={"parent_order_id": parent_order_id},
        )["order_id"]

    def exit_order(
        self,
        variety: str,
        order_id: str,
        parent_order_id: Optional[str] = None,
    ) -> str:
        """
        Exit a CO order.

        :param variety: Order variety.
        :type variety: str
        :param order_id: Order ID to exit.
        :type order_id: str
        :param parent_order_id: Parent order ID.
        :type parent_order_id: Optional[str]
        :returns: Order ID.
        :rtype: str
        """
        return self.cancel_order(variety, order_id, parent_order_id)

    def orders(self) -> List[Dict[str, Any]]:
        """
        Get list of all orders for the day.

        :returns: List of order dictionaries.
        :rtype: List[Dict[str, Any]]

        Example::

            all_orders = client.orders()
            for order in all_orders:
                print(f"{order['order_id']}: {order['status']}")
        """
        return format_response(self._get("orders"))

    def order_history(self, order_id: str) -> List[Dict[str, Any]]:
        """
        Get history of an individual order.

        :param order_id: Order ID to get history for.
        :type order_id: str
        :returns: List of order state changes.
        :rtype: List[Dict[str, Any]]
        """
        return format_response(self._get("order.info", url_args={"order_id": order_id}))

    def trades(self) -> List[Dict[str, Any]]:
        """
        Get list of all trades for the day.

        :returns: List of trade dictionaries.
        :rtype: List[Dict[str, Any]]
        """
        return format_response(self._get("trades"))

    def order_trades(self, order_id: str) -> List[Dict[str, Any]]:
        """
        Get trades for a specific order.

        :param order_id: Order ID to get trades for.
        :type order_id: str
        :returns: List of trades for the order.
        :rtype: List[Dict[str, Any]]
        """
        return format_response(
            self._get("order.trades", url_args={"order_id": order_id})
        )

    def positions(self) -> Dict[str, Any]:
        """
        Get list of positions.

        :returns: Dictionary with 'net' and 'day' positions.
        :rtype: Dict[str, Any]

        Example::

            positions = client.positions()
            for pos in positions.get("net", []):
                print(f"{pos['tradingsymbol']}: {pos['quantity']}")
        """
        return self._get("portfolio.positions")

    def holdings(self) -> List[Dict[str, Any]]:
        """
        Get list of holdings (equity).

        :returns: List of holding dictionaries.
        :rtype: List[Dict[str, Any]]

        Example::

            holdings = client.holdings()
            for holding in holdings:
                print(f"{holding['tradingsymbol']}: {holding['quantity']}")
        """
        return self._get("portfolio.holdings")

    def get_auction_instruments(self) -> List[Dict[str, Any]]:
        """
        Get list of available auction instruments.

        :returns: List of auction instruments.
        :rtype: List[Dict[str, Any]]
        """
        return self._get("portfolio.holdings.auction")

    def convert_position(
        self,
        exchange: str,
        tradingsymbol: str,
        transaction_type: str,
        position_type: str,
        quantity: int,
        old_product: str,
        new_product: str,
    ) -> Dict[str, Any]:
        """
        Convert an open position's product type.

        :param exchange: Exchange name.
        :type exchange: str
        :param tradingsymbol: Trading symbol.
        :type tradingsymbol: str
        :param transaction_type: BUY or SELL.
        :type transaction_type: str
        :param position_type: Position type (day/overnight).
        :type position_type: str
        :param quantity: Quantity to convert.
        :type quantity: int
        :param old_product: Current product type.
        :type old_product: str
        :param new_product: Target product type.
        :type new_product: str
        :returns: Conversion result.
        :rtype: Dict[str, Any]
        """
        return self._put(
            "portfolio.positions.convert",
            params={
                "exchange": exchange,
                "tradingsymbol": tradingsymbol,
                "transaction_type": transaction_type,
                "position_type": position_type,
                "quantity": quantity,
                "old_product": old_product,
                "new_product": new_product,
            },
        )

    def instruments(self, exchange: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get list of tradable instruments.

        Note: Results can be large (several hundred KBs).

        :param exchange: Filter by exchange (optional).
        :type exchange: Optional[str]
        :returns: List of instrument dictionaries.
        :rtype: List[Dict[str, Any]]

        Example::

            all_instruments = client.instruments()

            nse_instruments = client.instruments(exchange="NSE")
        """
        if exchange:
            data = self._get("market.instruments", url_args={"exchange": exchange})
        else:
            data = self._get("market.instruments.all")

        return parse_instruments_csv(data)

    def quote(self, *instruments: str) -> Dict[str, Dict[str, Any]]:
        """
        Get quote for list of instruments.

        :param instruments: Instruments in format 'EXCHANGE:SYMBOL'.
        :type instruments: str
        :returns: Dictionary of quotes keyed by instrument.
        :rtype: Dict[str, Dict[str, Any]]

        Example::

            quotes = client.quote("NSE:INFY", "NSE:RELIANCE")
            print(quotes["NSE:INFY"]["last_price"])
        """
        ins = list(instruments)
        if len(instruments) > 0 and isinstance(instruments[0], list):
            ins = instruments[0]

        data = self._get("market.quote", params={"i": ins})
        return {key: format_response(data[key]) for key in data}

    def ohlc(self, *instruments: str) -> Dict[str, Dict[str, Any]]:
        """
        Get OHLC data for list of instruments.

        :param instruments: Instruments in format 'EXCHANGE:SYMBOL'.
        :type instruments: str
        :returns: Dictionary of OHLC data keyed by instrument.
        :rtype: Dict[str, Dict[str, Any]]
        """
        ins = list(instruments)
        if len(instruments) > 0 and isinstance(instruments[0], list):
            ins = instruments[0]

        return self._get("market.quote.ohlc", params={"i": ins})

    def ltp(self, *instruments: str) -> Dict[str, Dict[str, Any]]:
        """
        Get last traded price for list of instruments.

        :param instruments: Instruments in format 'EXCHANGE:SYMBOL'.
        :type instruments: str
        :returns: Dictionary of LTP data keyed by instrument.
        :rtype: Dict[str, Dict[str, Any]]

        Example::

            prices = client.ltp("NSE:INFY", "NSE:RELIANCE")
            print(prices["NSE:INFY"]["last_price"])
        """
        ins = list(instruments)
        if len(instruments) > 0 and isinstance(instruments[0], list):
            ins = instruments[0]

        return self._get("market.quote.ltp", params={"i": ins})

    def historical_data(
        self,
        instrument_token: int,
        from_date: Union[datetime, str],
        to_date: Union[datetime, str],
        interval: str,
        continuous: bool = False,
        oi: bool = False,
    ) -> List[Dict[str, Any]]:
        """
        Get historical candle data for an instrument.

        :param instrument_token: Instrument token.
        :type instrument_token: int
        :param from_date: Start date/datetime.
        :type from_date: Union[datetime, str]
        :param to_date: End date/datetime.
        :type to_date: Union[datetime, str]
        :param interval: Candle interval (minute, day, 5minute, etc.).
        :type interval: str
        :param continuous: Get continuous data for F&O.
        :type continuous: bool
        :param oi: Include open interest data.
        :type oi: bool
        :returns: List of candle data dictionaries.
        :rtype: List[Dict[str, Any]]

        Example::

            candles = client.historical_data(
                instrument_token=738561,
                from_date="2024-01-01",
                to_date="2024-01-15",
                interval="day"
            )
        """
        from_date_string = (
            format_datetime(from_date) if isinstance(from_date, datetime) else from_date
        )
        to_date_string = (
            format_datetime(to_date) if isinstance(to_date, datetime) else to_date
        )

        data = self._get(
            "market.historical",
            url_args={
                "instrument_token": instrument_token,
                "interval": interval,
            },
            params={
                "from": from_date_string,
                "to": to_date_string,
                "interval": interval,
                "continuous": 1 if continuous else 0,
                "oi": 1 if oi else 0,
            },
        )

        return format_historical_data(data)

    def trigger_range(self, transaction_type: str, *instruments: str) -> Dict[str, Any]:
        """
        Get trigger range for Cover Orders.

        :param transaction_type: BUY or SELL.
        :type transaction_type: str
        :param instruments: Instruments in format 'EXCHANGE:SYMBOL'.
        :type instruments: str
        :returns: Trigger range data.
        :rtype: Dict[str, Any]
        """
        ins = list(instruments)
        if len(instruments) > 0 and isinstance(instruments[0], list):
            ins = instruments[0]

        return self._get(
            "market.trigger_range",
            url_args={"transaction_type": transaction_type.lower()},
            params={"i": ins},
        )

    def get_gtts(self) -> List[Dict[str, Any]]:
        """
        Get list of GTT orders.

        :returns: List of GTT order dictionaries.
        :rtype: List[Dict[str, Any]]
        """
        return self._get("gtt")

    def get_gtt(self, trigger_id: int) -> Dict[str, Any]:
        """
        Get details of a specific GTT order.

        :param trigger_id: GTT trigger ID.
        :type trigger_id: int
        :returns: GTT order details.
        :rtype: Dict[str, Any]
        """
        return self._get("gtt.info", url_args={"trigger_id": trigger_id})

    def place_gtt(
        self,
        trigger_type: str,
        tradingsymbol: str,
        exchange: str,
        trigger_values: List[float],
        last_price: float,
        orders: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        Place a GTT order.

        :param trigger_type: GTT type (single/two-leg).
        :type trigger_type: str
        :param tradingsymbol: Trading symbol.
        :type tradingsymbol: str
        :param exchange: Exchange name.
        :type exchange: str
        :param trigger_values: List of trigger prices.
        :type trigger_values: List[float]
        :param last_price: Current last price.
        :type last_price: float
        :param orders: List of order dictionaries.
        :type orders: List[Dict[str, Any]]
        :returns: GTT placement response with trigger_id.
        :rtype: Dict[str, Any]

        Example::

            gtt = client.place_gtt(
                trigger_type=client.GTT_TYPE_SINGLE,
                tradingsymbol="INFY",
                exchange="NSE",
                trigger_values=[1500],
                last_price=1600,
                orders=[{
                    "transaction_type": "BUY",
                    "quantity": 1,
                    "order_type": "LIMIT",
                    "product": "CNC",
                    "price": 1500
                }]
            )
        """
        condition, gtt_orders = self._get_gtt_payload(
            trigger_type,
            tradingsymbol,
            exchange,
            trigger_values,
            last_price,
            orders,
        )

        return self._post(
            "gtt.place",
            params={
                "condition": json.dumps(condition),
                "orders": json.dumps(gtt_orders),
                "type": trigger_type,
            },
        )

    def modify_gtt(
        self,
        trigger_id: int,
        trigger_type: str,
        tradingsymbol: str,
        exchange: str,
        trigger_values: List[float],
        last_price: float,
        orders: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        Modify a GTT order.

        :param trigger_id: GTT trigger ID to modify.
        :type trigger_id: int
        :param trigger_type: GTT type.
        :type trigger_type: str
        :param tradingsymbol: Trading symbol.
        :type tradingsymbol: str
        :param exchange: Exchange name.
        :type exchange: str
        :param trigger_values: New trigger prices.
        :type trigger_values: List[float]
        :param last_price: Current last price.
        :type last_price: float
        :param orders: New order list.
        :type orders: List[Dict[str, Any]]
        :returns: Modification response.
        :rtype: Dict[str, Any]
        """
        condition, gtt_orders = self._get_gtt_payload(
            trigger_type,
            tradingsymbol,
            exchange,
            trigger_values,
            last_price,
            orders,
        )

        return self._put(
            "gtt.modify",
            url_args={"trigger_id": trigger_id},
            params={
                "condition": json.dumps(condition),
                "orders": json.dumps(gtt_orders),
                "type": trigger_type,
            },
        )

    def delete_gtt(self, trigger_id: int) -> Dict[str, Any]:
        """
        Delete a GTT order.

        :param trigger_id: GTT trigger ID to delete.
        :type trigger_id: int
        :returns: Deletion response.
        :rtype: Dict[str, Any]
        """
        return self._delete("gtt.delete", url_args={"trigger_id": trigger_id})

    def _get_gtt_payload(
        self,
        trigger_type: str,
        tradingsymbol: str,
        exchange: str,
        trigger_values: List[float],
        last_price: float,
        orders: List[Dict[str, Any]],
    ) -> tuple:
        """
        Build GTT payload for API request.

        :param trigger_type: GTT type.
        :param tradingsymbol: Trading symbol.
        :param exchange: Exchange name.
        :param trigger_values: Trigger prices.
        :param last_price: Last price.
        :param orders: Order list.
        :returns: Tuple of (condition, orders) dictionaries.
        :raises InputException: If inputs are invalid.
        """
        if not isinstance(trigger_values, list):
            raise InputException("Invalid type for trigger_values")

        if trigger_type == GTT_TYPE_SINGLE and len(trigger_values) != 1:
            raise InputException("Invalid trigger_values for single leg order type")
        elif trigger_type == GTT_TYPE_OCO and len(trigger_values) != 2:
            raise InputException("Invalid trigger_values for OCO order type")

        condition = {
            "exchange": exchange,
            "tradingsymbol": tradingsymbol,
            "trigger_values": trigger_values,
            "last_price": last_price,
        }

        gtt_orders = []
        required_fields = [
            "transaction_type",
            "quantity",
            "order_type",
            "product",
            "price",
        ]

        for order in orders:
            for field in required_fields:
                if field not in order:
                    raise InputException(f"'{field}' missing in orders")

            gtt_orders.append(
                {
                    "exchange": exchange,
                    "tradingsymbol": tradingsymbol,
                    "transaction_type": order["transaction_type"],
                    "quantity": int(order["quantity"]),
                    "order_type": order["order_type"],
                    "product": order["product"],
                    "price": float(order["price"]),
                }
            )

        return condition, gtt_orders

    def order_margins(self, params: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Calculate margins for a list of orders.

        :param params: List of order parameter dictionaries.
        :type params: List[Dict[str, Any]]
        :returns: List of margin requirement details.
        :rtype: List[Dict[str, Any]]
        """
        return self._post("order.margins", params=params, is_json=True)

    def basket_order_margins(
        self,
        params: List[Dict[str, Any]],
        consider_positions: bool = True,
        mode: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Calculate total margins for basket of orders.

        :param params: List of order parameter dictionaries.
        :type params: List[Dict[str, Any]]
        :param consider_positions: Consider existing positions.
        :type consider_positions: bool
        :param mode: Response mode (compact for totals only).
        :type mode: Optional[str]
        :returns: Basket margin details.
        :rtype: Dict[str, Any]
        """
        return self._post(
            "order.margins.basket",
            params=params,
            is_json=True,
            query_params={
                "consider_positions": consider_positions,
                "mode": mode,
            },
        )

    def get_virtual_contract_note(
        self, params: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Get virtual contract note with charges.

        :param params: List of order parameter dictionaries.
        :type params: List[Dict[str, Any]]
        :returns: Contract note with charges.
        :rtype: List[Dict[str, Any]]
        """
        return self._post("order.contract_note", params=params, is_json=True)

    def mf_orders(
        self, order_id: Optional[str] = None
    ) -> Union[Dict[str, Any], List[Dict[str, Any]]]:
        """
        Get mutual fund orders.

        :param order_id: Specific order ID (optional).
        :type order_id: Optional[str]
        :returns: Order details or list of orders.
        :rtype: Union[Dict[str, Any], List[Dict[str, Any]]]
        """
        if order_id:
            return format_response(
                self._get("mf.order.info", url_args={"order_id": order_id})
            )
        return format_response(self._get("mf.orders"))

    def place_mf_order(
        self,
        tradingsymbol: str,
        transaction_type: str,
        quantity: Optional[int] = None,
        amount: Optional[float] = None,
        tag: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Place a mutual fund order.

        :param tradingsymbol: MF trading symbol.
        :type tradingsymbol: str
        :param transaction_type: BUY or SELL.
        :type transaction_type: str
        :param quantity: Number of units (for SELL).
        :type quantity: Optional[int]
        :param amount: Amount to invest (for BUY).
        :type amount: Optional[float]
        :param tag: Order tag.
        :type tag: Optional[str]
        :returns: Order placement response.
        :rtype: Dict[str, Any]
        """
        return self._post(
            "mf.order.place",
            params={
                "tradingsymbol": tradingsymbol,
                "transaction_type": transaction_type,
                "quantity": quantity,
                "amount": amount,
                "tag": tag,
            },
        )

    def cancel_mf_order(self, order_id: str) -> Dict[str, Any]:
        """
        Cancel a mutual fund order.

        :param order_id: Order ID to cancel.
        :type order_id: str
        :returns: Cancellation response.
        :rtype: Dict[str, Any]
        """
        return self._delete("mf.order.cancel", url_args={"order_id": order_id})

    def mf_sips(
        self, sip_id: Optional[str] = None
    ) -> Union[Dict[str, Any], List[Dict[str, Any]]]:
        """
        Get mutual fund SIPs.

        :param sip_id: Specific SIP ID (optional).
        :type sip_id: Optional[str]
        :returns: SIP details or list of SIPs.
        :rtype: Union[Dict[str, Any], List[Dict[str, Any]]]
        """
        if sip_id:
            return format_response(
                self._get("mf.sip.info", url_args={"sip_id": sip_id})
            )
        return format_response(self._get("mf.sips"))

    def place_mf_sip(
        self,
        tradingsymbol: str,
        amount: float,
        instalments: int,
        frequency: str,
        initial_amount: Optional[float] = None,
        instalment_day: Optional[int] = None,
        tag: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Place a mutual fund SIP.

        :param tradingsymbol: MF trading symbol.
        :type tradingsymbol: str
        :param amount: SIP amount.
        :type amount: float
        :param instalments: Number of instalments.
        :type instalments: int
        :param frequency: SIP frequency (weekly/monthly/quarterly).
        :type frequency: str
        :param initial_amount: Initial lump sum amount.
        :type initial_amount: Optional[float]
        :param instalment_day: Day of instalment (1-28).
        :type instalment_day: Optional[int]
        :param tag: SIP tag.
        :type tag: Optional[str]
        :returns: SIP placement response.
        :rtype: Dict[str, Any]
        """
        return self._post(
            "mf.sip.place",
            params={
                "tradingsymbol": tradingsymbol,
                "amount": amount,
                "initial_amount": initial_amount,
                "instalments": instalments,
                "frequency": frequency,
                "instalment_day": instalment_day,
                "tag": tag,
            },
        )

    def modify_mf_sip(
        self,
        sip_id: str,
        amount: Optional[float] = None,
        status: Optional[str] = None,
        instalments: Optional[int] = None,
        frequency: Optional[str] = None,
        instalment_day: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Modify a mutual fund SIP.

        :param sip_id: SIP ID to modify.
        :type sip_id: str
        :param amount: New amount.
        :type amount: Optional[float]
        :param status: New status.
        :type status: Optional[str]
        :param instalments: New instalment count.
        :type instalments: Optional[int]
        :param frequency: New frequency.
        :type frequency: Optional[str]
        :param instalment_day: New instalment day.
        :type instalment_day: Optional[int]
        :returns: Modification response.
        :rtype: Dict[str, Any]
        """
        return self._put(
            "mf.sip.modify",
            url_args={"sip_id": sip_id},
            params={
                "amount": amount,
                "status": status,
                "instalments": instalments,
                "frequency": frequency,
                "instalment_day": instalment_day,
            },
        )

    def cancel_mf_sip(self, sip_id: str) -> Dict[str, Any]:
        """
        Cancel a mutual fund SIP.

        :param sip_id: SIP ID to cancel.
        :type sip_id: str
        :returns: Cancellation response.
        :rtype: Dict[str, Any]
        """
        return self._delete("mf.sip.cancel", url_args={"sip_id": sip_id})

    def mf_holdings(self) -> List[Dict[str, Any]]:
        """
        Get mutual fund holdings.

        :returns: List of MF holdings.
        :rtype: List[Dict[str, Any]]
        """
        return self._get("mf.holdings")

    def mf_instruments(self) -> List[Dict[str, Any]]:
        """
        Get list of mutual fund instruments.

        :returns: List of MF instruments.
        :rtype: List[Dict[str, Any]]
        """
        return parse_mf_instruments_csv(self._get("mf.instruments"))

    def _user_agent(self) -> str:
        """Get user agent string for requests."""
        return f"{__title__}-python/{__version__}"

    def _get(
        self,
        route: str,
        url_args: Optional[Dict] = None,
        params: Optional[Dict] = None,
        is_json: bool = False,
    ) -> Any:
        """Send GET request."""
        return self._request(
            route, "GET", url_args=url_args, params=params, is_json=is_json
        )

    def _post(
        self,
        route: str,
        url_args: Optional[Dict] = None,
        params: Optional[Union[Dict, List]] = None,
        is_json: bool = False,
        query_params: Optional[Dict] = None,
    ) -> Any:
        """Send POST request."""
        return self._request(
            route,
            "POST",
            url_args=url_args,
            params=params,
            is_json=is_json,
            query_params=query_params,
        )

    def _put(
        self,
        route: str,
        url_args: Optional[Dict] = None,
        params: Optional[Dict] = None,
        is_json: bool = False,
        query_params: Optional[Dict] = None,
    ) -> Any:
        """Send PUT request."""
        return self._request(
            route,
            "PUT",
            url_args=url_args,
            params=params,
            is_json=is_json,
            query_params=query_params,
        )

    def _delete(
        self,
        route: str,
        url_args: Optional[Dict] = None,
        params: Optional[Dict] = None,
        is_json: bool = False,
    ) -> Any:
        """Send DELETE request."""
        return self._request(
            route, "DELETE", url_args=url_args, params=params, is_json=is_json
        )

    def _request(
        self,
        route: str,
        method: str,
        url_args: Optional[Dict] = None,
        params: Optional[Dict] = None,
        is_json: bool = False,
        query_params: Optional[Dict] = None,
    ) -> Any:
        """
        Make an HTTP request to the API.

        :param route: API route key.
        :param method: HTTP method.
        :param url_args: URL template arguments.
        :param params: Request parameters.
        :param is_json: Send params as JSON body.
        :param query_params: URL query parameters.
        :returns: API response data.
        :raises KiteException: On API errors.
        """
        if url_args:
            uri = self._routes[route].format(**url_args)
        else:
            uri = self._routes[route]

        url = urljoin(self.root, uri)
        headers = {
            "X-Kite-Version": KITE_HEADER_VERSION,
            "User-Agent": self._user_agent(),
        }

        if self.api_key and self.access_token:
            auth_header = f"{self.api_key}:{self.access_token}"
            headers["Authorization"] = f"token {auth_header}"

        if self.debug:
            log.debug(f"Request: {method} {url} params={params} headers={headers}")
        if method in ["GET", "DELETE"]:
            query_params = params

        try:
            response = self.reqsession.request(
                method,
                url,
                json=params if (method in ["POST", "PUT"] and is_json) else None,
                data=params if (method in ["POST", "PUT"] and not is_json) else None,
                params=query_params,
                headers=headers,
                verify=not self.disable_ssl,
                allow_redirects=True,
                timeout=self.timeout,
                proxies=self.proxies,
            )
        except Exception as e:
            raise NetworkException(f"Network error: {str(e)}")

        if self.debug:
            log.debug(f"Response: {response.status_code} {response.content[:500]}")
        if "json" in response.headers.get("content-type", ""):
            try:
                data = response.json()
            except ValueError:
                raise DataException(f"Couldn't parse JSON response: {response.content}")
            if data.get("status") == "error" or data.get("error_type"):
                if (
                    self.session_expiry_hook
                    and response.status_code == 403
                    and data.get("error_type") == "TokenException"
                ):
                    self.session_expiry_hook()

                exc_class = get_exception_class(
                    data.get("error_type", "GeneralException")
                )
                raise exc_class(
                    data.get("message", "Unknown error"),
                    code=response.status_code,
                )

            return data.get("data")

        elif "csv" in response.headers.get("content-type", ""):
            return response.content

        else:
            raise DataException(
                f"Unknown Content-Type: {response.headers.get('content-type')}"
            )
