"""
Abstract repository interfaces for data persistence.

This module defines the interfaces for data access, enabling
swappable storage backends (file, Redis, PostgreSQL, etc.).

:copyright: (c) 2025
:license: MIT
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Generic, List, Optional, TypeVar
from datetime import datetime

from pydantic import BaseModel


T = TypeVar("T", bound=BaseModel)


class BaseRepository(ABC, Generic[T]):
    """
    Abstract base repository for CRUD operations.

    All data repositories must implement this interface to provide
    consistent data access patterns across different storage backends.

    :cvar model_class: The Pydantic model class this repository manages.

    Example::

        class UserRepository(BaseRepository[User]):
            model_class = User

            def get(self, id: str) -> Optional[User]:

                pass
    """

    model_class: type

    @abstractmethod
    async def get(self, id: str) -> Optional[T]:
        """
        Get a single entity by ID.

        :param id: Unique identifier.
        :type id: str
        :returns: Entity if found, None otherwise.
        :rtype: Optional[T]
        """

    @abstractmethod
    async def get_all(self) -> List[T]:
        """
        Get all entities.

        :returns: List of all entities.
        :rtype: List[T]
        """

    @abstractmethod
    async def find(self, **filters: Any) -> List[T]:
        """
        Find entities matching filters.

        :param filters: Key-value filters to match.
        :type filters: Any
        :returns: List of matching entities.
        :rtype: List[T]
        """

    @abstractmethod
    async def create(self, entity: T) -> T:
        """
        Create a new entity.

        :param entity: Entity to create.
        :type entity: T
        :returns: Created entity with ID.
        :rtype: T
        """

    @abstractmethod
    async def update(self, id: str, entity: T) -> Optional[T]:
        """
        Update an existing entity.

        :param id: Entity ID to update.
        :type id: str
        :param entity: Updated entity data.
        :type entity: T
        :returns: Updated entity or None if not found.
        :rtype: Optional[T]
        """

    @abstractmethod
    async def delete(self, id: str) -> bool:
        """
        Delete an entity.

        :param id: Entity ID to delete.
        :type id: str
        :returns: True if deleted, False if not found.
        :rtype: bool
        """

    @abstractmethod
    async def exists(self, id: str) -> bool:
        """
        Check if entity exists.

        :param id: Entity ID to check.
        :type id: str
        :returns: True if exists.
        :rtype: bool
        """


class SessionRepository(ABC):
    """
    Abstract repository for user session management.

    Handles storage and retrieval of user sessions, tokens,
    and authentication state.

    Example::

        class RedisSessionRepository(SessionRepository):
            def __init__(self, redis_client):
                self.redis = redis_client

            async def get_session(self, user_id: str) -> Optional[Dict]:
                return await self.redis.hgetall(f"session:{user_id}")
    """

    @abstractmethod
    async def get_session(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Get session data for a user.

        :param user_id: User identifier.
        :type user_id: str
        :returns: Session data or None.
        :rtype: Optional[Dict[str, Any]]
        """

    @abstractmethod
    async def save_session(
        self,
        user_id: str,
        session_data: Dict[str, Any],
        ttl: Optional[int] = None,
    ) -> bool:
        """
        Save session data.

        :param user_id: User identifier.
        :type user_id: str
        :param session_data: Session data to store.
        :type session_data: Dict[str, Any]
        :param ttl: Time-to-live in seconds.
        :type ttl: Optional[int]
        :returns: True if saved successfully.
        :rtype: bool
        """

    @abstractmethod
    async def delete_session(self, user_id: str) -> bool:
        """
        Delete a user session.

        :param user_id: User identifier.
        :type user_id: str
        :returns: True if deleted.
        :rtype: bool
        """

    @abstractmethod
    async def refresh_session(self, user_id: str, ttl: int) -> bool:
        """
        Extend session TTL.

        :param user_id: User identifier.
        :type user_id: str
        :param ttl: New TTL in seconds.
        :type ttl: int
        :returns: True if refreshed.
        :rtype: bool
        """

    @abstractmethod
    async def get_all_active_sessions(self) -> List[str]:
        """
        Get all active session user IDs.

        :returns: List of user IDs with active sessions.
        :rtype: List[str]
        """


class RulesRepository(ABC):
    """
    Abstract repository for trading rules persistence.

    Manages storage of user-specific trading rules and configurations.
    """

    @abstractmethod
    async def get_rules(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Get trading rules for a user.

        :param user_id: User identifier.
        :type user_id: str
        :returns: Rules configuration or None.
        :rtype: Optional[Dict[str, Any]]
        """

    @abstractmethod
    async def save_rules(self, user_id: str, rules: Dict[str, Any]) -> bool:
        """
        Save trading rules for a user.

        :param user_id: User identifier.
        :type user_id: str
        :param rules: Rules configuration.
        :type rules: Dict[str, Any]
        :returns: True if saved.
        :rtype: bool
        """

    @abstractmethod
    async def delete_rules(self, user_id: str) -> bool:
        """
        Delete trading rules for a user.

        :param user_id: User identifier.
        :type user_id: str
        :returns: True if deleted.
        :rtype: bool
        """


class TradeLogRepository(ABC):
    """
    Abstract repository for trade execution logs.

    Stores historical trade data for auditing and analysis.
    """

    @abstractmethod
    async def log_trade(
        self,
        user_id: str,
        trade_data: Dict[str, Any],
    ) -> str:
        """
        Log a trade execution.

        :param user_id: User identifier.
        :type user_id: str
        :param trade_data: Trade execution details.
        :type trade_data: Dict[str, Any]
        :returns: Trade log ID.
        :rtype: str
        """

    @abstractmethod
    async def get_trade_history(
        self,
        user_id: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """
        Get trade history for a user.

        :param user_id: User identifier.
        :type user_id: str
        :param start_date: Filter start date.
        :type start_date: Optional[datetime]
        :param end_date: Filter end date.
        :type end_date: Optional[datetime]
        :param limit: Maximum records to return.
        :type limit: int
        :returns: List of trade records.
        :rtype: List[Dict[str, Any]]
        """
