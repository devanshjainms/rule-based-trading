"""
Configuration module for Kite Connect API.

This module handles loading environment variables and configuration
settings from .env file using python-dotenv.

:copyright: (c) 2025
:license: MIT
"""

import os
from typing import Optional
from dotenv import load_dotenv

load_dotenv()


class Config:
    """
    Configuration class for Kite Connect API settings.

    This class loads configuration from environment variables and provides
    default values where appropriate. All sensitive credentials should be
    stored in a .env file.

    :ivar api_key: The API key issued by Zerodha for Kite Connect.
    :ivar api_secret: The API secret issued by Zerodha for Kite Connect.
    :ivar access_token: The access token obtained after authentication.
    :ivar request_token: The request token obtained from login redirect.
    :ivar root_url: The base URL for Kite Connect API.
    :ivar websocket_url: The WebSocket URL for live data streaming.
    :ivar debug: Enable debug mode for verbose logging.
    :ivar timeout: Request timeout in seconds.
    """

    def __init__(self) -> None:
        """
        Initialize the Config class by loading environment variables.

        Loads all configuration from environment variables with sensible
        defaults for non-sensitive settings.
        """
        self.api_key: str = os.getenv("KITE_API_KEY", "")
        self.api_secret: str = os.getenv("KITE_API_SECRET", "")
        self.access_token: Optional[str] = os.getenv("KITE_ACCESS_TOKEN")
        self.request_token: Optional[str] = os.getenv("KITE_REQUEST_TOKEN")
        self.root_url: str = os.getenv("KITE_ROOT_URL", "https://api.kite.trade")
        self.login_url: str = os.getenv(
            "KITE_LOGIN_URL", "https://kite.zerodha.com/connect/login"
        )
        self.websocket_url: str = os.getenv("KITE_WEBSOCKET_URL", "wss://ws.kite.trade")
        self.debug: bool = os.getenv("KITE_DEBUG", "false").lower() == "true"
        self.timeout: int = int(os.getenv("KITE_TIMEOUT", "7"))
        self.disable_ssl: bool = (
            os.getenv("KITE_DISABLE_SSL", "false").lower() == "true"
        )
        self.ws_reconnect: bool = (
            os.getenv("KITE_WS_RECONNECT", "true").lower() == "true"
        )
        self.ws_reconnect_max_tries: int = int(
            os.getenv("KITE_WS_RECONNECT_MAX_TRIES", "50")
        )
        self.ws_reconnect_max_delay: int = int(
            os.getenv("KITE_WS_RECONNECT_MAX_DELAY", "60")
        )
        self.ws_connect_timeout: int = int(os.getenv("KITE_WS_CONNECT_TIMEOUT", "30"))
        self.proxy_host: Optional[str] = os.getenv("KITE_PROXY_HOST")
        proxy_port_str = os.getenv("KITE_PROXY_PORT")
        self.proxy_port: Optional[int] = int(proxy_port_str) if proxy_port_str else None

    @property
    def proxy(self) -> Optional[dict]:
        """
        Get proxy configuration as a dictionary.

        :returns: Dictionary with proxy settings or None if not configured.
        :rtype: Optional[dict]
        """
        if self.proxy_host and self.proxy_port:
            return {
                "http": f"http://{self.proxy_host}:{self.proxy_port}",
                "https": f"http://{self.proxy_host}:{self.proxy_port}",
            }
        return None

    def is_configured(self) -> bool:
        """
        Check if the minimum required configuration is present.

        :returns: True if API key is configured, False otherwise.
        :rtype: bool
        """
        return bool(self.api_key)

    def is_authenticated(self) -> bool:
        """
        Check if authentication credentials are present.

        :returns: True if both API key and access token are configured.
        :rtype: bool
        """
        return bool(self.api_key and self.access_token)

    def __repr__(self) -> str:
        """
        Return string representation of Config.

        :returns: String representation with masked sensitive values.
        :rtype: str
        """
        return (
            f"Config("
            f"api_key={'***' if self.api_key else 'Not Set'}, "
            f"access_token={'***' if self.access_token else 'Not Set'}, "
            f"root_url={self.root_url}, "
            f"debug={self.debug})"
        )


config = Config()


def get_config() -> Config:
    """
    Get the global configuration instance.

    :returns: The global Config instance.
    :rtype: Config
    """
    return config


def reload_config() -> Config:
    """
    Reload configuration from environment variables.

    This is useful when environment variables have been updated
    and you need to refresh the configuration.

    :returns: A new Config instance with reloaded values.
    :rtype: Config
    """
    global config
    load_dotenv(override=True)
    config = Config()
    return config
