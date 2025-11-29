"""
Custom exceptions for Kite Connect API client.

This module defines all custom exception classes used throughout the
trading framework for handling various error conditions.

:copyright: (c) 2025
:license: MIT
"""


class KiteException(Exception):
    """
    Base exception class for all Kite Connect related errors.

    Every specific Kite client exception is a subclass of this
    and exposes two instance variables: ``code`` (HTTP error code)
    and ``message`` (error text).

    :param message: The error message describing the exception.
    :type message: str
    :param code: The HTTP status code associated with the error.
    :type code: int

    :ivar message: The error message.
    :ivar code: The HTTP status code.

    Example::

        try:
            pass
        except KiteException as e:
            print(f"Error {e.code}: {e.message}")
    """

    def __init__(self, message: str, code: int = 500) -> None:
        """
        Initialize the KiteException.

        :param message: The error message.
        :type message: str
        :param code: The HTTP status code (default: 500).
        :type code: int
        """
        super(KiteException, self).__init__(message)
        self.message = message
        self.code = code

    def __str__(self) -> str:
        """
        Return string representation of the exception.

        :returns: Formatted error message with code.
        :rtype: str
        """
        return f"[{self.code}] {self.message}"

    def __repr__(self) -> str:
        """
        Return detailed representation of the exception.

        :returns: Detailed string representation.
        :rtype: str
        """
        return f"{self.__class__.__name__}(message='{self.message}', code={self.code})"


class GeneralException(KiteException):
    """
    An unclassified, general error.

    This exception is raised when an error occurs that doesn't
    fit into any specific category. Default code is 500.

    :param message: The error message describing the exception.
    :type message: str
    :param code: The HTTP status code (default: 500).
    :type code: int
    """

    def __init__(self, message: str, code: int = 500) -> None:
        """
        Initialize the GeneralException.

        :param message: The error message.
        :type message: str
        :param code: The HTTP status code (default: 500).
        :type code: int
        """
        super(GeneralException, self).__init__(message, code)


class TokenException(KiteException):
    """
    Exception for token and authentication related errors.

    This exception is raised when there are issues with access tokens,
    session expiry, or authentication failures. Default code is 403.

    :param message: The error message describing the exception.
    :type message: str
    :param code: The HTTP status code (default: 403).
    :type code: int

    Example::

        try:
            client.profile()
        except TokenException:
            print("Please login again")
    """

    def __init__(self, message: str, code: int = 403) -> None:
        """
        Initialize the TokenException.

        :param message: The error message.
        :type message: str
        :param code: The HTTP status code (default: 403).
        :type code: int
        """
        super(TokenException, self).__init__(message, code)


class PermissionException(KiteException):
    """
    Exception for permission denied errors.

    This exception is raised when the user doesn't have permission
    to perform a specific operation. Default code is 403.

    :param message: The error message describing the exception.
    :type message: str
    :param code: The HTTP status code (default: 403).
    :type code: int
    """

    def __init__(self, message: str, code: int = 403) -> None:
        """
        Initialize the PermissionException.

        :param message: The error message.
        :type message: str
        :param code: The HTTP status code (default: 403).
        :type code: int
        """
        super(PermissionException, self).__init__(message, code)


class OrderException(KiteException):
    """
    Exception for order placement and manipulation errors.

    This exception is raised when there are issues with placing,
    modifying, or cancelling orders. Default code is 500.

    :param message: The error message describing the exception.
    :type message: str
    :param code: The HTTP status code (default: 500).
    :type code: int

    Example::

        try:
            client.place_order(...)
        except OrderException as e:
            print(f"Order failed: {e.message}")
    """

    def __init__(self, message: str, code: int = 500) -> None:
        """
        Initialize the OrderException.

        :param message: The error message.
        :type message: str
        :param code: The HTTP status code (default: 500).
        :type code: int
        """
        super(OrderException, self).__init__(message, code)


class InputException(KiteException):
    """
    Exception for user input errors.

    This exception is raised when there are missing or invalid
    parameters in the request. Default code is 400.

    :param message: The error message describing the exception.
    :type message: str
    :param code: The HTTP status code (default: 400).
    :type code: int

    Example::

        try:
            client.place_order(quantity=-1)
        except InputException as e:
            print(f"Invalid input: {e.message}")
    """

    def __init__(self, message: str, code: int = 400) -> None:
        """
        Initialize the InputException.

        :param message: The error message.
        :type message: str
        :param code: The HTTP status code (default: 400).
        :type code: int
        """
        super(InputException, self).__init__(message, code)


class DataException(KiteException):
    """
    Exception for bad responses from the Order Management System.

    This exception is raised when there's an issue with the backend
    OMS response. Default code is 502.

    :param message: The error message describing the exception.
    :type message: str
    :param code: The HTTP status code (default: 502).
    :type code: int
    """

    def __init__(self, message: str, code: int = 502) -> None:
        """
        Initialize the DataException.

        :param message: The error message.
        :type message: str
        :param code: The HTTP status code (default: 502).
        :type code: int
        """
        super(DataException, self).__init__(message, code)


class NetworkException(KiteException):
    """
    Exception for network issues between client and OMS.

    This exception is raised when there's a network connectivity
    issue. Default code is 503.

    :param message: The error message describing the exception.
    :type message: str
    :param code: The HTTP status code (default: 503).
    :type code: int

    Example::

        try:
            client.orders()
        except NetworkException:
            print("Network error, please check your connection")
    """

    def __init__(self, message: str, code: int = 503) -> None:
        """
        Initialize the NetworkException.

        :param message: The error message.
        :type message: str
        :param code: The HTTP status code (default: 503).
        :type code: int
        """
        super(NetworkException, self).__init__(message, code)


class WebSocketException(KiteException):
    """
    Exception for WebSocket connection and streaming errors.

    This exception is raised when there are issues with the
    WebSocket connection for live data streaming.

    :param message: The error message describing the exception.
    :type message: str
    :param code: The WebSocket close code (default: 1006).
    :type code: int
    """

    def __init__(self, message: str, code: int = 1006) -> None:
        """
        Initialize the WebSocketException.

        :param message: The error message.
        :type message: str
        :param code: The WebSocket close code (default: 1006).
        :type code: int
        """
        super(WebSocketException, self).__init__(message, code)


EXCEPTION_MAP = {
    "GeneralException": GeneralException,
    "TokenException": TokenException,
    "PermissionException": PermissionException,
    "OrderException": OrderException,
    "InputException": InputException,
    "DataException": DataException,
    "NetworkException": NetworkException,
}


def get_exception_class(error_type: str) -> type:
    """
    Get the appropriate exception class for a given error type.

    :param error_type: The error type string from API response.
    :type error_type: str
    :returns: The corresponding exception class.
    :rtype: type

    Example::

        exc_class = get_exception_class("TokenException")
        raise exc_class("Token expired")
    """
    return EXCEPTION_MAP.get(error_type, GeneralException)


class OAuthError(Exception):
    """
    OAuth authentication error.

    Raised when OAuth flow fails due to invalid credentials,
    expired tokens, or provider errors.

    :param message: Error description.
    :param provider: OAuth provider name (e.g., 'kite').
    :param error_code: Provider-specific error code.
    """

    def __init__(
        self,
        message: str,
        provider: str = "unknown",
        error_code: str = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.provider = provider
        self.error_code = error_code

    def __str__(self) -> str:
        if self.error_code:
            return f"[{self.provider}:{self.error_code}] {self.message}"
        return f"[{self.provider}] {self.message}"


class BrokerNotConnectedError(Exception):
    """
    Raised when user attempts trading without an active broker connection.

    :param user_id: The user ID that lacks a broker connection.
    :param broker: The broker type (e.g., 'kite').
    """

    def __init__(self, user_id: str, broker: str = None) -> None:
        self.user_id = user_id
        self.broker = broker
        message = f"No active broker connection for user {user_id}"
        if broker:
            message += f" (broker: {broker})"
        super().__init__(message)


class RuleValidationError(Exception):
    """
    Raised when a trading rule fails validation.

    :param rule_id: The rule ID that failed validation.
    :param errors: List of validation error messages.
    """

    def __init__(self, rule_id: str, errors: list) -> None:
        self.rule_id = rule_id
        self.errors = errors
        message = f"Rule '{rule_id}' validation failed: {', '.join(errors)}"
        super().__init__(message)


class EngineError(Exception):
    """
    Raised when the trading engine encounters an error.

    :param message: Error description.
    :param user_id: The user whose engine failed (if applicable).
    """

    def __init__(self, message: str, user_id: str = None) -> None:
        self.user_id = user_id
        super().__init__(message)
