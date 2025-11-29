"""
Utility functions for Kite Connect API client.

This module provides helper functions for data parsing, formatting,
and common operations used throughout the trading framework.

:copyright: (c) 2025
:license: MIT
"""

import csv
import hashlib
import logging
from io import StringIO
from datetime import datetime, date
from typing import Any, Dict, List, Optional, Union

import dateutil.parser

log = logging.getLogger(__name__)


def generate_checksum(api_key: str, token: str, api_secret: str) -> str:
    """
    Generate SHA256 checksum for authentication.

    Used during session generation and token renewal to create
    a secure checksum from API credentials.

    :param api_key: The API key issued by Zerodha.
    :type api_key: str
    :param token: The request token or refresh token.
    :type token: str
    :param api_secret: The API secret issued by Zerodha.
    :type api_secret: str
    :returns: The SHA256 checksum as a hex string.
    :rtype: str

    Example::

        checksum = generate_checksum(api_key, request_token, api_secret)
    """
    data = api_key + token + api_secret
    return hashlib.sha256(data.encode("utf-8")).hexdigest()


def parse_datetime(value: Optional[str]) -> Optional[datetime]:
    """
    Parse a datetime string to a datetime object.

    Handles various datetime formats commonly used in Kite Connect API.

    :param value: The datetime string to parse.
    :type value: Optional[str]
    :returns: Parsed datetime object or None if parsing fails.
    :rtype: Optional[datetime]

    Example::

        dt = parse_datetime("2024-01-15 09:15:00")
    """
    if not value:
        return None

    try:
        if isinstance(value, str) and len(value) == 19:
            return dateutil.parser.parse(value)
        elif isinstance(value, str):
            return dateutil.parser.parse(value)
        return value
    except (ValueError, TypeError) as e:
        log.debug(f"Failed to parse datetime '{value}': {e}")
        return None


def parse_date(value: Optional[str]) -> Optional[date]:
    """
    Parse a date string to a date object.

    :param value: The date string to parse (YYYY-MM-DD format).
    :type value: Optional[str]
    :returns: Parsed date object or None if parsing fails.
    :rtype: Optional[date]

    Example::

        d = parse_date("2024-01-15")
    """
    if not value:
        return None

    try:
        if isinstance(value, str) and len(value) == 10:
            return dateutil.parser.parse(value).date()
        elif isinstance(value, str):
            return dateutil.parser.parse(value).date()
        return value
    except (ValueError, TypeError) as e:
        log.debug(f"Failed to parse date '{value}': {e}")
        return None


def format_datetime(dt: Optional[datetime]) -> Optional[str]:
    """
    Format a datetime object to string for API requests.

    :param dt: The datetime object to format.
    :type dt: Optional[datetime]
    :returns: Formatted datetime string or None.
    :rtype: Optional[str]

    Example::

        date_str = format_datetime(datetime.now())
    """
    if dt is None:
        return None

    if isinstance(dt, datetime):
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    return str(dt)


def format_date(d: Optional[date]) -> Optional[str]:
    """
    Format a date object to string for API requests.

    :param d: The date object to format.
    :type d: Optional[date]
    :returns: Formatted date string or None.
    :rtype: Optional[str]

    Example::

        date_str = format_date(date.today())
    """
    if d is None:
        return None

    if isinstance(d, (date, datetime)):
        return d.strftime("%Y-%m-%d")
    return str(d)


def parse_instruments_csv(
    data: Union[str, bytes, bytearray, memoryview],
) -> List[Dict[str, Any]]:
    """
    Parse instruments CSV data from the API.

    :param data: CSV data as string or bytes.
    :type data: Union[str, bytes]
    :returns: List of instrument dictionaries.
    :rtype: List[Dict[str, Any]]

    Example::

        instruments = parse_instruments_csv(csv_data)
        for inst in instruments:
            print(inst["tradingsymbol"], inst["instrument_token"])
    """
    if isinstance(data, (bytes, bytearray, memoryview)):
        data = bytes(data).decode("utf-8").strip()

    records = []
    reader = csv.DictReader(StringIO(data))

    for row in reader:
        row["instrument_token"] = int(row.get("instrument_token", 0))
        row["exchange_token"] = int(row.get("exchange_token", 0))
        row["last_price"] = float(row.get("last_price", 0))
        row["strike"] = float(row.get("strike", 0))
        row["tick_size"] = float(row.get("tick_size", 0))
        row["lot_size"] = int(row.get("lot_size", 1))
        expiry = row.get("expiry", "")
        if expiry and len(expiry) == 10:
            row["expiry"] = parse_date(expiry)
        else:
            row["expiry"] = None

        records.append(row)

    return records


def parse_mf_instruments_csv(
    data: Union[str, bytes, bytearray, memoryview],
) -> List[Dict[str, Any]]:
    """
    Parse mutual fund instruments CSV data from the API.

    :param data: CSV data as string or bytes.
    :type data: Union[str, bytes]
    :returns: List of mutual fund instrument dictionaries.
    :rtype: List[Dict[str, Any]]

    Example::

        mf_instruments = parse_mf_instruments_csv(csv_data)
    """
    if isinstance(data, (bytes, bytearray, memoryview)):
        data = bytes(data).decode("utf-8").strip()

    records = []
    reader = csv.DictReader(StringIO(data))

    for row in reader:
        row["minimum_purchase_amount"] = float(row.get("minimum_purchase_amount", 0))
        row["purchase_amount_multiplier"] = float(
            row.get("purchase_amount_multiplier", 0)
        )
        row["minimum_additional_purchase_amount"] = float(
            row.get("minimum_additional_purchase_amount", 0)
        )
        row["minimum_redemption_quantity"] = float(
            row.get("minimum_redemption_quantity", 0)
        )
        row["redemption_quantity_multiplier"] = float(
            row.get("redemption_quantity_multiplier", 0)
        )
        row["purchase_allowed"] = bool(int(row.get("purchase_allowed", 0)))
        row["redemption_allowed"] = bool(int(row.get("redemption_allowed", 0)))
        row["last_price"] = float(row.get("last_price", 0))
        last_price_date = row.get("last_price_date", "")
        if last_price_date and len(last_price_date) == 10:
            row["last_price_date"] = parse_date(last_price_date)
        else:
            row["last_price_date"] = None

        records.append(row)

    return records


def format_historical_data(data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Format historical candle data from API response.

    :param data: Raw API response with candles data.
    :type data: Dict[str, Any]
    :returns: List of formatted candle dictionaries.
    :rtype: List[Dict[str, Any]]

    Example::

        candles = format_historical_data(api_response)
        for candle in candles:
            print(candle["date"], candle["close"])
    """
    records = []
    candles = data.get("candles", [])

    for candle in candles:
        record = {
            "date": parse_datetime(candle[0]),
            "open": candle[1],
            "high": candle[2],
            "low": candle[3],
            "close": candle[4],
            "volume": candle[5],
        }
        if len(candle) == 7:
            record["oi"] = candle[6]

        records.append(record)

    return records


def format_response(data: Union[Dict, List]) -> Union[Dict, List]:
    """
    Format API response by parsing datetime fields.

    :param data: Raw API response data.
    :type data: Union[Dict, List]
    :returns: Formatted data with parsed datetime fields.
    :rtype: Union[Dict, List]
    """
    datetime_fields = [
        "order_timestamp",
        "exchange_timestamp",
        "created",
        "last_instalment",
        "fill_timestamp",
        "timestamp",
        "last_trade_time",
    ]

    if isinstance(data, list):
        items = data
    elif isinstance(data, dict):
        items = [data]
    else:
        return data

    for item in items:
        if not isinstance(item, dict):
            continue

        for field in datetime_fields:
            value = item.get(field)
            if value and isinstance(value, str) and len(value) == 19:
                item[field] = parse_datetime(value)

    return items[0] if isinstance(data, dict) else items


def clean_none_values(params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Remove None values from a dictionary.

    Useful for cleaning up API request parameters.

    :param params: Dictionary with potential None values.
    :type params: Dict[str, Any]
    :returns: Dictionary with None values removed.
    :rtype: Dict[str, Any]

    Example::

        params = {"price": 100, "trigger": None}
        clean = clean_none_values(params)
    """
    return {k: v for k, v in params.items() if v is not None}


def validate_instrument_token(token: int) -> bool:
    """
    Validate an instrument token.

    :param token: The instrument token to validate.
    :type token: int
    :returns: True if valid, False otherwise.
    :rtype: bool
    """
    return isinstance(token, int) and token > 0


def get_exchange_from_token(token: int) -> str:
    """
    Extract exchange segment from instrument token.

    The last byte of the instrument token contains the exchange segment.

    :param token: The instrument token.
    :type token: int
    :returns: Exchange segment identifier.
    :rtype: str

    Example::

        segment = get_exchange_from_token(738561)
    """
    segment_map = {
        1: "NSE",
        2: "NFO",
        3: "CDS",
        4: "BSE",
        5: "BFO",
        6: "BCD",
        7: "MCX",
        8: "MCXSX",
        9: "INDICES",
    }
    segment = token & 0xFF
    return segment_map.get(segment, "UNKNOWN")


def calculate_lot_value(last_price: float, lot_size: int, quantity: int = 1) -> float:
    """
    Calculate the total value for a given lot.

    :param last_price: Last traded price.
    :type last_price: float
    :param lot_size: Lot size of the instrument.
    :type lot_size: int
    :param quantity: Number of lots (default: 1).
    :type quantity: int
    :returns: Total value.
    :rtype: float

    Example::

        value = calculate_lot_value(18500.0, 50, 2)
    """
    return last_price * lot_size * quantity


def format_price(price: float, tick_size: float = 0.05) -> float:
    """
    Round price to the nearest valid tick size.

    :param price: The price to format.
    :type price: float
    :param tick_size: The minimum tick size (default: 0.05).
    :type tick_size: float
    :returns: Price rounded to valid tick.
    :rtype: float

    Example::

        formatted = format_price(100.123, 0.05)
    """
    if tick_size == 0:
        return price
    return round(round(price / tick_size) * tick_size, 2)


def setup_logging(
    level: int = logging.INFO,
    format_string: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
) -> None:
    """
    Set up logging configuration for the framework.

    :param level: Logging level (default: INFO).
    :type level: int
    :param format_string: Log format string.
    :type format_string: str

    Example::

        setup_logging(level=logging.DEBUG)
    """
    logging.basicConfig(level=level, format=format_string)
