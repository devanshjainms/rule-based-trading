"""
Per-user broker client factory.

Creates broker clients with user-specific credentials from the database.

:copyright: (c) 2025
:license: MIT
"""

import logging
from datetime import datetime
from typing import Dict, Optional

from src.database import get_database_manager
from src.database.models import BrokerAccount
from src.database.repositories import PostgresBrokerAccountRepository
from src.utils.encryption import decrypt_credential

logger = logging.getLogger(__name__)


class BrokerClientFactory:
    """
    Factory for creating per-user broker clients.

    Manages a cache of active broker clients for performance.

    Example::

        factory = BrokerClientFactory()
        client = await factory.get_client(user_id="user123")
        positions = client.positions()
    """

    def __init__(self) -> None:
        """Initialize the factory."""

        self._clients: Dict[str, any] = {}

        self._accounts: Dict[str, BrokerAccount] = {}

    async def get_client(
        self,
        user_id: str,
        broker_type: str = "kite",
    ) -> Optional[any]:
        """
        Get or create broker client for user.

        :param user_id: User ID.
        :type user_id: str
        :param broker_type: Broker type (default: kite).
        :type broker_type: str
        :returns: Broker client or None if not configured.
        :rtype: Optional[any]
        """
        cache_key = f"{user_id}:{broker_type}"

        if cache_key in self._clients:
            account = self._accounts.get(cache_key)
            if account and self._is_token_valid(account):
                return self._clients[cache_key]

        account = await self._get_broker_account(user_id, broker_type)
        if not account:
            logger.warning(
                f"No broker account found for user {user_id}, broker {broker_type}"
            )
            return None

        if not self._is_token_valid(account):
            logger.warning(f"Broker token expired for user {user_id}")
            return None

        client = await self._create_client(account, broker_type)
        if client:
            self._clients[cache_key] = client
            self._accounts[cache_key] = account

        return client

    async def _get_broker_account(
        self,
        user_id: str,
        broker_type: str,
    ) -> Optional[BrokerAccount]:
        """
        Get broker account from database.

        :param user_id: User ID.
        :param broker_type: Broker type.
        :returns: Broker account or None.
        """
        db = get_database_manager()
        async with db.session() as session:
            repo = PostgresBrokerAccountRepository(session)
            return await repo.get_by_user_and_broker(user_id, broker_type)

    def _is_token_valid(self, account: BrokerAccount) -> bool:
        """
        Check if broker token is still valid.

        :param account: Broker account.
        :returns: True if token is valid.
        """
        if not account.access_token:
            return False

        if account.token_expires_at:

            return datetime.utcnow() < account.token_expires_at

        return True

    async def _create_client(
        self,
        account: BrokerAccount,
        broker_type: str,
    ) -> Optional[any]:
        """
        Create broker client from account credentials.

        :param account: Broker account with encrypted credentials.
        :param broker_type: Broker type.
        :returns: Broker client.
        """
        try:

            api_key = decrypt_credential(account.api_key)
            access_token = decrypt_credential(account.access_token)

            if broker_type == "kite":
                from src.brokers.kite.client import KiteClient

                client = KiteClient(
                    api_key=api_key,
                    access_token=access_token,
                )
                logger.info(f"Created Kite client for user {account.user_id}")
                return client

            logger.error(f"Unknown broker type: {broker_type}")
            return None

        except Exception as e:
            logger.error(f"Failed to create broker client: {e}")
            return None

    def invalidate_client(self, user_id: str, broker_type: str = "kite") -> None:
        """
        Invalidate cached client for user.

        Call this when credentials are updated or token is refreshed.

        :param user_id: User ID.
        :param broker_type: Broker type.
        """
        cache_key = f"{user_id}:{broker_type}"
        self._clients.pop(cache_key, None)
        self._accounts.pop(cache_key, None)
        logger.info(f"Invalidated broker client cache for user {user_id}")

    def clear_cache(self) -> None:
        """Clear all cached clients."""
        self._clients.clear()
        self._accounts.clear()
        logger.info("Cleared all broker client cache")


_broker_factory: Optional[BrokerClientFactory] = None


def get_broker_factory() -> BrokerClientFactory:
    """
    Get global broker client factory.

    :returns: Broker client factory instance.
    :rtype: BrokerClientFactory
    """
    global _broker_factory
    if _broker_factory is None:
        _broker_factory = BrokerClientFactory()
    return _broker_factory


async def get_user_broker_client(
    user_id: str,
    broker_type: str = "kite",
) -> Optional[any]:
    """
    Convenience function to get broker client for user.

    :param user_id: User ID.
    :param broker_type: Broker type.
    :returns: Broker client or None.
    """
    factory = get_broker_factory()
    return await factory.get_client(user_id, broker_type)
