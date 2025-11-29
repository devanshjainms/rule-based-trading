"""
SQLAlchemy database models.

This module defines all database tables using SQLAlchemy ORM.
Supports PostgreSQL with async operations.

:copyright: (c) 2025
:license: MIT
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import uuid4

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    JSON,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.ext.asyncio import AsyncAttrs
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(AsyncAttrs, DeclarativeBase):
    """Base class for all SQLAlchemy models."""


class TimestampMixin:
    """Mixin for created_at and updated_at timestamps."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )


class User(Base, TimestampMixin):
    """
    User account model.

    Stores user registration and profile information.
    One user can have multiple broker connections.

    :ivar id: Unique user identifier (UUID).
    :ivar email: User email address (unique).
    :ivar hashed_password: Bcrypt hashed password.
    :ivar full_name: User's full name.
    :ivar is_active: Whether user account is active.
    :ivar is_verified: Whether email is verified.
    :ivar settings: User preferences as JSON.
    """

    __tablename__ = "users"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid4())
    )
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    settings: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict)

    broker_accounts: Mapped[List["BrokerAccount"]] = relationship(
        "BrokerAccount", back_populates="user", cascade="all, delete-orphan"
    )
    sessions: Mapped[List["UserSessionDB"]] = relationship(
        "UserSessionDB", back_populates="user", cascade="all, delete-orphan"
    )
    trading_rules: Mapped[List["TradingRule"]] = relationship(
        "TradingRule", back_populates="user", cascade="all, delete-orphan"
    )
    trade_logs: Mapped[List["TradeLog"]] = relationship(
        "TradeLog", back_populates="user", cascade="all, delete-orphan"
    )

    __table_args__ = (Index("ix_users_email", "email"),)


class BrokerAccount(Base, TimestampMixin):
    """
    Broker connection model.

    Links a user to a broker account with credentials.

    :ivar id: Unique broker account ID.
    :ivar user_id: Foreign key to user.
    :ivar broker_id: Broker identifier (kite, webull, etc.).
    :ivar broker_user_id: User ID from broker.
    :ivar api_key: Broker API key.
    :ivar api_secret: Encrypted API secret.
    :ivar access_token: Current access token.
    :ivar refresh_token: Refresh token (if available).
    :ivar token_expires_at: Token expiration time.
    :ivar is_active: Whether connection is active.
    :ivar metadata: Additional broker-specific data.
    """

    __tablename__ = "broker_accounts"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid4())
    )
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    broker_id: Mapped[str] = mapped_column(String(50), nullable=False)
    broker_user_id: Mapped[str] = mapped_column(String(100), nullable=True)
    api_key: Mapped[str] = mapped_column(String(255), nullable=False)
    api_secret: Mapped[str] = mapped_column(String(255), nullable=True)
    access_token: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    refresh_token: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    token_expires_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime, nullable=True
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    metadata_: Mapped[Dict[str, Any]] = mapped_column("metadata", JSON, default=dict)

    user: Mapped["User"] = relationship("User", back_populates="broker_accounts")

    __table_args__ = (
        UniqueConstraint("user_id", "broker_id", name="uq_user_broker"),
        Index("ix_broker_accounts_user_id", "user_id"),
    )


class UserSessionDB(Base, TimestampMixin):
    """
    User session model (database-backed).

    Tracks active user sessions for audit and management.

    :ivar id: Session ID (UUID).
    :ivar user_id: Foreign key to user.
    :ivar broker_account_id: Associated broker account.
    :ivar ip_address: Client IP address.
    :ivar user_agent: Client user agent.
    :ivar expires_at: Session expiration.
    :ivar is_active: Whether session is active.
    """

    __tablename__ = "user_sessions"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid4())
    )
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    broker_account_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("broker_accounts.id", ondelete="SET NULL"), nullable=True
    )
    ip_address: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    last_activity: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )

    user: Mapped["User"] = relationship("User", back_populates="sessions")

    __table_args__ = (
        Index("ix_user_sessions_user_id", "user_id"),
        Index("ix_user_sessions_expires_at", "expires_at"),
    )


class TradingRule(Base, TimestampMixin):
    """
    Trading rule configuration model.

    Stores user-defined trading rules with conditions and actions.

    :ivar id: Rule ID.
    :ivar user_id: Foreign key to user.
    :ivar name: Rule name/identifier.
    :ivar description: Rule description.
    :ivar symbol: Trading symbol (e.g., RELIANCE, NIFTY).
    :ivar is_active: Whether rule is active.
    :ivar priority: Rule priority (lower = higher priority).
    :ivar conditions: List of conditions (stored as JSON).
    :ivar actions: List of actions (stored as JSON).
    :ivar symbol_pattern: Symbol matching pattern for exit rules.
    :ivar exchange: Exchange filter.
    :ivar position_type: LONG or SHORT.
    :ivar take_profit: Take profit configuration.
    :ivar stop_loss: Stop loss configuration.
    :ivar time_conditions: Time-based conditions.
    :ivar metadata: Additional rule metadata.
    :ivar trigger_count: Number of times rule was triggered.
    :ivar last_triggered: Last trigger timestamp.
    """

    __tablename__ = "trading_rules"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid4())
    )
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    symbol: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    priority: Mapped[int] = mapped_column(Integer, default=100)
    conditions: Mapped[List[Dict[str, Any]]] = mapped_column(JSON, default=list)
    actions: Mapped[List[Dict[str, Any]]] = mapped_column(JSON, default=list)
    symbol_pattern: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    exchange: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    position_type: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    take_profit: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict)
    stop_loss: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict)
    time_conditions: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict)
    metadata_: Mapped[Dict[str, Any]] = mapped_column("metadata", JSON, default=dict)
    trigger_count: Mapped[int] = mapped_column(Integer, default=0)
    last_triggered: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    user: Mapped["User"] = relationship("User", back_populates="trading_rules")

    __table_args__ = (
        Index("ix_trading_rules_user_id", "user_id"),
        Index("ix_trading_rules_user_active", "user_id", "is_active"),
    )


class TradeLog(Base):
    """
    Trade execution log model.

    Records all trade executions for audit and analysis.

    :ivar id: Log entry ID.
    :ivar user_id: Foreign key to user.
    :ivar broker_account_id: Broker account used.
    :ivar rule_id: Rule that triggered the trade (if any).
    :ivar symbol: Trading symbol.
    :ivar exchange: Exchange code.
    :ivar side: BUY or SELL.
    :ivar quantity: Trade quantity.
    :ivar price: Execution price.
    :ivar order_id: Broker order ID.
    :ivar order_type: Order type used.
    :ivar trigger_type: TP, SL, MANUAL, etc.
    :ivar trigger_price: Price that triggered exit.
    :ivar pnl: Profit/Loss amount.
    :ivar status: Execution status.
    :ivar error_message: Error message if failed.
    :ivar executed_at: Execution timestamp.
    :ivar metadata: Additional trade metadata.
    """

    __tablename__ = "trade_logs"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid4())
    )
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    broker_account_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("broker_accounts.id", ondelete="SET NULL"), nullable=True
    )
    rule_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("trading_rules.id", ondelete="SET NULL"), nullable=True
    )
    symbol: Mapped[str] = mapped_column(String(100), nullable=False)
    exchange: Mapped[str] = mapped_column(String(20), nullable=False)
    side: Mapped[str] = mapped_column(String(10), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    price: Mapped[float] = mapped_column(Float, nullable=False)
    order_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    order_type: Mapped[str] = mapped_column(String(20), nullable=False)
    trigger_type: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    trigger_price: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    pnl: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    executed_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
    metadata_: Mapped[Dict[str, Any]] = mapped_column("metadata", JSON, default=dict)

    user: Mapped["User"] = relationship("User", back_populates="trade_logs")

    __table_args__ = (
        Index("ix_trade_logs_user_id", "user_id"),
        Index("ix_trade_logs_executed_at", "executed_at"),
        Index("ix_trade_logs_symbol", "symbol", "exchange"),
    )


class Notification(Base):
    """
    Notification queue model.

    Stores notifications pending delivery.

    :ivar id: Notification ID.
    :ivar user_id: Target user.
    :ivar type: Notification type (email, push, sms).
    :ivar channel: Delivery channel.
    :ivar subject: Notification subject.
    :ivar body: Notification body.
    :ivar data: Additional notification data.
    :ivar status: Delivery status.
    :ivar attempts: Delivery attempts.
    :ivar scheduled_at: When to send.
    :ivar sent_at: When actually sent.
    """

    __tablename__ = "notifications"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid4())
    )
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    type: Mapped[str] = mapped_column(String(20), nullable=False)
    channel: Mapped[str] = mapped_column(String(20), nullable=False)
    subject: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    data: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict)
    status: Mapped[str] = mapped_column(String(20), default="pending")
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    scheduled_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
    sent_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )

    __table_args__ = (
        Index("ix_notifications_user_status", "user_id", "status"),
        Index("ix_notifications_scheduled", "scheduled_at", "status"),
    )
