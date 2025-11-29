"""
Database connection and session management.

This module handles database connection pooling, session creation,
and transaction management for async SQLAlchemy.

:copyright: (c) 2025
:license: MIT
"""

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Optional

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from dotenv import load_dotenv

from src.database.models import Base


load_dotenv()

logger = logging.getLogger(__name__)


class DatabaseConfig:
    """
    Database configuration.

    :ivar url: Database URL (postgresql+asyncpg://...).
    :ivar pool_size: Connection pool size.
    :ivar max_overflow: Max overflow connections.
    :ivar pool_timeout: Pool timeout in seconds.
    :ivar pool_recycle: Connection recycle time.
    :ivar echo: Echo SQL statements.
    """

    def __init__(
        self,
        url: str | None = None,
        pool_size: int = 5,
        max_overflow: int = 10,
        pool_timeout: int = 30,
        pool_recycle: int = 1800,
        echo: bool = False,
    ) -> None:
        """
        Initialize database configuration.

        Loads DATABASE_URL from environment if not provided.

        :param url: Database connection URL.
        :type url: str | None
        :param pool_size: Base pool size.
        :type pool_size: int
        :param max_overflow: Max additional connections.
        :type max_overflow: int
        :param pool_timeout: Pool wait timeout.
        :type pool_timeout: int
        :param pool_recycle: Connection recycle interval.
        :type pool_recycle: int
        :param echo: Log SQL statements.
        :type echo: bool
        """
        import os

        self.url = url or os.getenv(
            "DATABASE_URL", "postgresql+asyncpg://localhost:5432/trading"
        )
        self.pool_size = pool_size
        self.max_overflow = max_overflow
        self.pool_timeout = pool_timeout
        self.pool_recycle = pool_recycle
        self.echo = echo


class Database:
    """
    Database manager for async SQLAlchemy operations.

    Handles engine creation, session management, and lifecycle.

    Example::

        db = Database(config)
        await db.init()

        async with db.session() as session:
            result = await session.execute(select(User))
            users = result.scalars().all()

        await db.close()
    """

    def __init__(self, config: Optional[DatabaseConfig] = None) -> None:
        """
        Initialize database manager.

        :param config: Database configuration.
        :type config: Optional[DatabaseConfig]
        """
        self.config = config or DatabaseConfig()
        self._engine: Optional[AsyncEngine] = None
        self._session_factory: Optional[async_sessionmaker[AsyncSession]] = None

    @property
    def engine(self) -> AsyncEngine:
        """
        Get database engine.

        :returns: SQLAlchemy async engine.
        :rtype: AsyncEngine
        :raises RuntimeError: If database not initialized.
        """
        if self._engine is None:
            raise RuntimeError("Database not initialized. Call init() first.")
        return self._engine

    @property
    def session_factory(self) -> async_sessionmaker[AsyncSession]:
        """
        Get session factory.

        :returns: Async session maker.
        :rtype: async_sessionmaker[AsyncSession]
        :raises RuntimeError: If database not initialized.
        """
        if self._session_factory is None:
            raise RuntimeError("Database not initialized. Call init() first.")
        return self._session_factory

    async def init(self) -> None:
        """
        Initialize database connection.

        Creates engine and session factory.
        """
        logger.info(f"Initializing database connection")

        self._engine = create_async_engine(
            self.config.url,
            pool_size=self.config.pool_size,
            max_overflow=self.config.max_overflow,
            pool_timeout=self.config.pool_timeout,
            pool_recycle=self.config.pool_recycle,
            echo=self.config.echo,
        )

        self._session_factory = async_sessionmaker(
            bind=self._engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autocommit=False,
            autoflush=False,
        )

        logger.info("Database connection initialized")

    async def close(self) -> None:
        """Close database connection and cleanup."""
        if self._engine:
            await self._engine.dispose()
            self._engine = None
            self._session_factory = None
            logger.info("Database connection closed")

    async def connect(self) -> None:
        """Alias for init() - connects to database."""
        await self.init()

    async def disconnect(self) -> None:
        """Alias for close() - disconnects from database."""
        await self.close()

    async def create_tables(self) -> None:
        """
        Create all database tables.

        Should only be used for development/testing.
        Use migrations (Alembic) for production.
        """
        async with self._engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Database tables created")

    async def drop_tables(self) -> None:
        """
        Drop all database tables.

        WARNING: Destroys all data. Use only for testing.
        """
        async with self._engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
        logger.info("Database tables dropped")

    @asynccontextmanager
    async def session(self) -> AsyncGenerator[AsyncSession, None]:
        """
        Get a database session context manager.

        Automatically handles commit/rollback and session cleanup.

        :yields: Database session.
        :rtype: AsyncGenerator[AsyncSession, None]

        Example::

            async with db.session() as session:
                user = User(email="test@test.com")
                session.add(user)

        """
        if self._session_factory is None:
            raise RuntimeError("Database not initialized. Call init() first.")

        session = self._session_factory()
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

    def get_session(self) -> AsyncSession:
        """
        Get a new session (caller must manage lifecycle).

        :returns: New database session.
        :rtype: AsyncSession
        """
        if self._session_factory is None:
            raise RuntimeError("Database not initialized. Call init() first.")
        return self._session_factory()


_database: Optional[Database] = None


def get_database() -> Database:
    """
    Get global database instance.

    :returns: Database instance.
    :rtype: Database
    """
    global _database
    if _database is None:
        _database = Database()
    return _database


def configure_database(config: DatabaseConfig) -> Database:
    """
    Configure and return global database instance.

    :param config: Database configuration.
    :type config: DatabaseConfig
    :returns: Configured database instance.
    :rtype: Database
    """
    global _database
    _database = Database(config)
    return _database


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency for database sessions.

    :yields: Database session.
    :rtype: AsyncGenerator[AsyncSession, None]

    Example::

        @router.get("/users")
        async def get_users(session: AsyncSession = Depends(get_session)):
            result = await session.execute(select(User))
            return result.scalars().all()
    """
    db = get_database()
    async with db.session() as session:
        yield session
