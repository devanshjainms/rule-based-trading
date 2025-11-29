"""
Database package.

Provides SQLAlchemy models, connection management, and repository
implementations for PostgreSQL.

:copyright: (c) 2025
:license: MIT
"""

from src.database.connection import (
    Database,
    DatabaseConfig,
    configure_database,
    get_database,
    get_session,
)
from src.database.models import (
    Base,
    BrokerAccount,
    Notification,
    TimestampMixin,
    TradeLog,
    TradingRule,
    User,
    UserSessionDB,
)
from src.database.repositories import (
    PostgresBrokerAccountRepository,
    PostgresRulesRepository,
    PostgresSessionRepository,
    PostgresTradeLogRepository,
    PostgresUserRepository,
)


get_database_manager = get_database

__all__ = [
    "Database",
    "DatabaseConfig",
    "get_database",
    "get_database_manager",
    "configure_database",
    "get_session",
    "Base",
    "TimestampMixin",
    "User",
    "BrokerAccount",
    "UserSessionDB",
    "TradingRule",
    "TradeLog",
    "Notification",
    "PostgresUserRepository",
    "PostgresSessionRepository",
    "PostgresRulesRepository",
    "PostgresTradeLogRepository",
    "PostgresBrokerAccountRepository",
]
