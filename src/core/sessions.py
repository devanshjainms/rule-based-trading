"""
User session management for multi-tenant trading.

This module handles user sessions, authentication state,
and per-user broker connections.

:copyright: (c) 2025
:license: MIT
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from uuid import uuid4

from pydantic import BaseModel, Field

from src.brokers.base import BaseBroker, BaseTicker
from src.core.events import Event, EventBus, EventType, get_event_bus
from src.models import UserProfile

logger = logging.getLogger(__name__)


class UserSession(BaseModel):
    """
    User session model.

    Represents an active user session with broker credentials
    and connection state.

    :ivar session_id: Unique session identifier.
    :ivar user_id: User identifier from broker.
    :ivar broker_id: Broker identifier (kite, webull, etc.).
    :ivar access_token: Current access token.
    :ivar refresh_token: Refresh token (if available).
    :ivar created_at: Session creation timestamp.
    :ivar expires_at: Session expiration timestamp.
    :ivar last_activity: Last activity timestamp.
    :ivar metadata: Additional session metadata.
    """

    session_id: str = Field(default_factory=lambda: str(uuid4()))
    user_id: str
    broker_id: str
    access_token: str
    refresh_token: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = None
    last_activity: datetime = Field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = Field(default_factory=dict)

    @property
    def is_expired(self) -> bool:
        """
        Check if session has expired.

        :returns: True if session is expired.
        :rtype: bool
        """
        if self.expires_at is None:
            return False
        return datetime.utcnow() > self.expires_at

    def touch(self) -> None:
        """Update last activity timestamp."""
        self.last_activity = datetime.utcnow()


@dataclass
class UserContext:
    """
    Runtime context for an active user.

    Contains broker client, ticker, and trading engine
    instances for a specific user session.

    :ivar session: User session data.
    :ivar broker: Broker client instance.
    :ivar ticker: Ticker client instance (optional).
    :ivar profile: User profile from broker.
    :ivar is_active: Whether context is active.
    :ivar _tasks: Background tasks for this user.
    """

    session: UserSession
    broker: BaseBroker
    ticker: Optional[BaseTicker] = None
    profile: Optional[UserProfile] = None
    is_active: bool = True
    _tasks: List[asyncio.Task] = field(default_factory=list)

    @property
    def user_id(self) -> str:
        """Get user ID from session."""
        return self.session.user_id

    @property
    def session_id(self) -> str:
        """Get session ID."""
        return self.session.session_id

    async def start_ticker(self) -> bool:
        """
        Start ticker for real-time data.

        :returns: True if ticker started successfully.
        :rtype: bool
        """
        if self.ticker:
            try:
                self.ticker.connect()
                return True
            except Exception as e:
                logger.error(f"Failed to start ticker for {self.user_id}: {e}")
        return False

    async def stop_ticker(self) -> None:
        """Stop ticker connection."""
        if self.ticker:
            try:
                self.ticker.close()
            except Exception as e:
                logger.error(f"Error stopping ticker for {self.user_id}: {e}")

    def add_task(self, task: asyncio.Task) -> None:
        """
        Add a background task to this context.

        :param task: Asyncio task to track.
        :type task: asyncio.Task
        """
        self._tasks.append(task)

    async def cancel_tasks(self) -> None:
        """Cancel all background tasks."""
        for task in self._tasks:
            if not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
        self._tasks.clear()

    async def cleanup(self) -> None:
        """Clean up user context resources."""
        self.is_active = False
        await self.cancel_tasks()
        await self.stop_ticker()


class SessionManager:
    """
    Manages user sessions and contexts.

    Handles creating, retrieving, and cleaning up user sessions.
    Supports multiple concurrent users with isolated contexts.

    Example::

        manager = SessionManager()


        context = await manager.create_session(
            user_id="user123",
            broker_id="kite",
            access_token="token_xyz",
            broker_factory=lambda: KiteClient(...)
        )


        ctx = manager.get_context("user123")


        await manager.end_session("user123")
    """

    def __init__(
        self,
        event_bus: Optional[EventBus] = None,
        session_ttl: int = 86400,
    ) -> None:
        """
        Initialize session manager.

        :param event_bus: Event bus for publishing session events.
        :type event_bus: Optional[EventBus]
        :param session_ttl: Default session TTL in seconds.
        :type session_ttl: int
        """
        self._sessions: Dict[str, UserSession] = {}
        self._contexts: Dict[str, UserContext] = {}
        self._event_bus = event_bus or get_event_bus()
        self._session_ttl = session_ttl
        self._cleanup_task: Optional[asyncio.Task] = None

    @property
    def active_sessions(self) -> List[str]:
        """
        Get list of active session user IDs.

        :returns: List of user IDs with active sessions.
        :rtype: List[str]
        """
        return list(self._sessions.keys())

    @property
    def session_count(self) -> int:
        """
        Get count of active sessions.

        :returns: Number of active sessions.
        :rtype: int
        """
        return len(self._sessions)

    async def create_session(
        self,
        user_id: str,
        broker_id: str,
        access_token: str,
        broker: BaseBroker,
        ticker: Optional[BaseTicker] = None,
        refresh_token: Optional[str] = None,
        expires_at: Optional[datetime] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> UserContext:
        """
        Create a new user session.

        :param user_id: User identifier.
        :type user_id: str
        :param broker_id: Broker identifier.
        :type broker_id: str
        :param access_token: Access token from broker.
        :type access_token: str
        :param broker: Initialized broker client.
        :type broker: BaseBroker
        :param ticker: Optional ticker client.
        :type ticker: Optional[BaseTicker]
        :param refresh_token: Optional refresh token.
        :type refresh_token: Optional[str]
        :param expires_at: Session expiration time.
        :type expires_at: Optional[datetime]
        :param metadata: Additional session metadata.
        :type metadata: Optional[Dict[str, Any]]
        :returns: User context for the session.
        :rtype: UserContext
        """

        if user_id in self._sessions:
            await self.end_session(user_id)

        session = UserSession(
            user_id=user_id,
            broker_id=broker_id,
            access_token=access_token,
            refresh_token=refresh_token,
            expires_at=expires_at
            or datetime.utcnow() + timedelta(seconds=self._session_ttl),
            metadata=metadata or {},
        )

        context = UserContext(
            session=session,
            broker=broker,
            ticker=ticker,
        )

        try:
            context.profile = broker.get_profile()
        except Exception as e:
            logger.warning(f"Could not fetch profile for {user_id}: {e}")

        self._sessions[user_id] = session
        self._contexts[user_id] = context

        await self._event_bus.publish(
            Event(
                type=EventType.SESSION_STARTED,
                user_id=user_id,
                data={
                    "session_id": session.session_id,
                    "broker_id": broker_id,
                },
            )
        )

        logger.info(f"Session created for user {user_id}")
        return context

    def get_session(self, user_id: str) -> Optional[UserSession]:
        """
        Get session for a user.

        :param user_id: User identifier.
        :type user_id: str
        :returns: User session or None.
        :rtype: Optional[UserSession]
        """
        return self._sessions.get(user_id)

    def get_context(self, user_id: str) -> Optional[UserContext]:
        """
        Get context for a user.

        :param user_id: User identifier.
        :type user_id: str
        :returns: User context or None.
        :rtype: Optional[UserContext]
        """
        context = self._contexts.get(user_id)
        if context:
            context.session.touch()
        return context

    def has_session(self, user_id: str) -> bool:
        """
        Check if user has active session.

        :param user_id: User identifier.
        :type user_id: str
        :returns: True if session exists.
        :rtype: bool
        """
        return user_id in self._sessions

    async def end_session(self, user_id: str) -> bool:
        """
        End a user session.

        :param user_id: User identifier.
        :type user_id: str
        :returns: True if session was ended.
        :rtype: bool
        """
        if user_id not in self._sessions:
            return False

        context = self._contexts.get(user_id)
        if context:
            await context.cleanup()

        session = self._sessions.pop(user_id, None)
        self._contexts.pop(user_id, None)
        self._event_bus.remove_user_handlers(user_id)

        await self._event_bus.publish(
            Event(
                type=EventType.SESSION_EXPIRED,
                user_id=user_id,
                data={
                    "session_id": session.session_id if session else None,
                    "reason": "ended",
                },
            )
        )

        logger.info(f"Session ended for user {user_id}")
        return True

    async def refresh_session(
        self,
        user_id: str,
        new_access_token: str,
        new_refresh_token: Optional[str] = None,
        new_expires_at: Optional[datetime] = None,
    ) -> bool:
        """
        Refresh session tokens.

        :param user_id: User identifier.
        :type user_id: str
        :param new_access_token: New access token.
        :type new_access_token: str
        :param new_refresh_token: New refresh token.
        :type new_refresh_token: Optional[str]
        :param new_expires_at: New expiration time.
        :type new_expires_at: Optional[datetime]
        :returns: True if refreshed successfully.
        :rtype: bool
        """
        session = self._sessions.get(user_id)
        if not session:
            return False

        session.access_token = new_access_token
        if new_refresh_token:
            session.refresh_token = new_refresh_token
        if new_expires_at:
            session.expires_at = new_expires_at
        else:
            session.expires_at = datetime.utcnow() + timedelta(
                seconds=self._session_ttl
            )

        session.touch()
        return True

    async def cleanup_expired(self) -> int:
        """
        Clean up expired sessions.

        :returns: Number of sessions cleaned up.
        :rtype: int
        """
        expired = [
            user_id for user_id, session in self._sessions.items() if session.is_expired
        ]

        for user_id in expired:
            await self.end_session(user_id)

        if expired:
            logger.info(f"Cleaned up {len(expired)} expired sessions")

        return len(expired)

    async def start_cleanup_task(self, interval: int = 300) -> None:
        """
        Start periodic cleanup task.

        :param interval: Cleanup interval in seconds.
        :type interval: int
        """
        if self._cleanup_task:
            return

        async def cleanup_loop():
            while True:
                await asyncio.sleep(interval)
                await self.cleanup_expired()

        self._cleanup_task = asyncio.create_task(cleanup_loop())

    async def stop_cleanup_task(self) -> None:
        """Stop cleanup task."""
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
            self._cleanup_task = None

    async def shutdown(self) -> None:
        """Shutdown session manager and all sessions."""
        await self.stop_cleanup_task()

        for user_id in list(self._sessions.keys()):
            await self.end_session(user_id)

        logger.info("Session manager shut down")


_session_manager: Optional[SessionManager] = None


def get_session_manager() -> SessionManager:
    """
    Get the global session manager instance.

    :returns: Global SessionManager instance.
    :rtype: SessionManager
    """
    global _session_manager
    if _session_manager is None:
        _session_manager = SessionManager()
    return _session_manager
