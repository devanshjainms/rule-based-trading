"""
PostgreSQL repository implementations.

Concrete implementations of repository interfaces using SQLAlchemy.

:copyright: (c) 2025
:license: MIT
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, TypeVar

from sqlalchemy import and_, delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.repositories import (
    BaseRepository,
    RulesRepository,
    SessionRepository,
    TradeLogRepository,
)
from src.database.models import (
    BrokerAccount,
    TradeLog,
    TradingRule,
    User,
    UserSessionDB,
)

logger = logging.getLogger(__name__)

T = TypeVar("T")


class PostgresUserRepository(BaseRepository[User]):
    """
    PostgreSQL implementation for User repository.

    :ivar session: Database session.
    """

    model_class = User

    def __init__(self, session: AsyncSession) -> None:
        """
        Initialize repository.

        :param session: Database session.
        :type session: AsyncSession
        """
        self.session = session

    async def get(self, id: str) -> Optional[User]:
        """
        Get user by ID.

        :param id: User ID.
        :type id: str
        :returns: User or None.
        :rtype: Optional[User]
        """
        result = await self.session.execute(select(User).where(User.id == id))
        return result.scalar_one_or_none()

    async def get_by_email(self, email: str) -> Optional[User]:
        """
        Get user by email.

        :param email: User email.
        :type email: str
        :returns: User or None.
        :rtype: Optional[User]
        """
        result = await self.session.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()

    async def get_all(self) -> List[User]:
        """
        Get all users.

        :returns: List of users.
        :rtype: List[User]
        """
        result = await self.session.execute(select(User))
        return list(result.scalars().all())

    async def find(self, **filters: Any) -> List[User]:
        """
        Find users by filters.

        :param filters: Filter conditions.
        :type filters: Any
        :returns: Matching users.
        :rtype: List[User]
        """
        query = select(User)
        for key, value in filters.items():
            if hasattr(User, key):
                query = query.where(getattr(User, key) == value)
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def create(self, entity: User) -> User:
        """
        Create a new user.

        :param entity: User to create.
        :type entity: User
        :returns: Created user.
        :rtype: User
        """
        self.session.add(entity)
        await self.session.flush()
        await self.session.refresh(entity)
        return entity

    async def update(self, id: str, entity: User) -> Optional[User]:
        """
        Update a user.

        :param id: User ID.
        :type id: str
        :param entity: Updated user data.
        :type entity: User
        :returns: Updated user or None.
        :rtype: Optional[User]
        """
        existing = await self.get(id)
        if not existing:
            return None

        for key, value in entity.__dict__.items():
            if not key.startswith("_") and hasattr(existing, key):
                setattr(existing, key, value)

        await self.session.flush()
        await self.session.refresh(existing)
        return existing

    async def delete(self, id: str) -> bool:
        """
        Delete a user.

        :param id: User ID.
        :type id: str
        :returns: True if deleted.
        :rtype: bool
        """
        result = await self.session.execute(delete(User).where(User.id == id))
        return result.rowcount > 0

    async def exists(self, id: str) -> bool:
        """
        Check if user exists.

        :param id: User ID.
        :type id: str
        :returns: True if exists.
        :rtype: bool
        """
        result = await self.session.execute(
            select(User.id).where(User.id == id).limit(1)
        )
        return result.scalar_one_or_none() is not None


class PostgresSessionRepository(SessionRepository):
    """
    PostgreSQL implementation for session repository.

    :ivar session: Database session.
    """

    def __init__(self, session: AsyncSession) -> None:
        """
        Initialize repository.

        :param session: Database session.
        :type session: AsyncSession
        """
        self.session = session

    async def get_session(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Get active session for user.

        :param user_id: User ID.
        :type user_id: str
        :returns: Session data or None.
        :rtype: Optional[Dict[str, Any]]
        """
        result = await self.session.execute(
            select(UserSessionDB)
            .where(
                and_(
                    UserSessionDB.user_id == user_id,
                    UserSessionDB.is_active == True,
                    UserSessionDB.expires_at > datetime.utcnow(),
                )
            )
            .order_by(UserSessionDB.created_at.desc())
            .limit(1)
        )
        session_db = result.scalar_one_or_none()
        if session_db:
            return {
                "session_id": session_db.id,
                "user_id": session_db.user_id,
                "broker_account_id": session_db.broker_account_id,
                "expires_at": session_db.expires_at.isoformat(),
                "last_activity": session_db.last_activity.isoformat(),
            }
        return None

    async def save_session(
        self,
        user_id: str,
        session_data: Dict[str, Any],
        ttl: Optional[int] = None,
    ) -> bool:
        """
        Save user session.

        :param user_id: User ID.
        :type user_id: str
        :param session_data: Session data.
        :type session_data: Dict[str, Any]
        :param ttl: Time to live in seconds.
        :type ttl: Optional[int]
        :returns: True if saved.
        :rtype: bool
        """
        from datetime import timedelta

        expires_at = datetime.utcnow() + timedelta(seconds=ttl or 86400)

        session_db = UserSessionDB(
            id=session_data.get("session_id"),
            user_id=user_id,
            broker_account_id=session_data.get("broker_account_id"),
            ip_address=session_data.get("ip_address"),
            user_agent=session_data.get("user_agent"),
            expires_at=expires_at,
            is_active=True,
        )
        self.session.add(session_db)
        await self.session.flush()
        return True

    async def delete_session(self, user_id: str) -> bool:
        """
        Delete user session.

        :param user_id: User ID.
        :type user_id: str
        :returns: True if deleted.
        :rtype: bool
        """
        result = await self.session.execute(
            update(UserSessionDB)
            .where(UserSessionDB.user_id == user_id)
            .values(is_active=False)
        )
        return result.rowcount > 0

    async def refresh_session(self, user_id: str, ttl: int) -> bool:
        """
        Refresh session TTL.

        :param user_id: User ID.
        :type user_id: str
        :param ttl: New TTL in seconds.
        :type ttl: int
        :returns: True if refreshed.
        :rtype: bool
        """
        from datetime import timedelta

        new_expires = datetime.utcnow() + timedelta(seconds=ttl)
        result = await self.session.execute(
            update(UserSessionDB)
            .where(
                and_(
                    UserSessionDB.user_id == user_id,
                    UserSessionDB.is_active == True,
                )
            )
            .values(expires_at=new_expires, last_activity=datetime.utcnow())
        )
        return result.rowcount > 0

    async def get_all_active_sessions(self) -> List[str]:
        """
        Get all active session user IDs.

        :returns: List of user IDs.
        :rtype: List[str]
        """
        result = await self.session.execute(
            select(UserSessionDB.user_id)
            .where(
                and_(
                    UserSessionDB.is_active == True,
                    UserSessionDB.expires_at > datetime.utcnow(),
                )
            )
            .distinct()
        )
        return [row[0] for row in result.fetchall()]


class PostgresRulesRepository(RulesRepository):
    """
    PostgreSQL implementation for rules repository.

    :ivar session: Database session.
    """

    def __init__(self, session: AsyncSession) -> None:
        """
        Initialize repository.

        :param session: Database session.
        :type session: AsyncSession
        """
        self.session = session

    async def get_rules(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Get all rules for user.

        :param user_id: User ID.
        :type user_id: str
        :returns: Rules configuration.
        :rtype: Optional[Dict[str, Any]]
        """
        result = await self.session.execute(
            select(TradingRule)
            .where(TradingRule.user_id == user_id)
            .order_by(TradingRule.priority)
        )
        rules = result.scalars().all()
        if not rules:
            return None

        return {
            "version": "2.0",
            "rules": [
                {
                    "id": r.id,
                    "name": r.name,
                    "description": r.description,
                    "is_active": r.is_active,
                    "priority": r.priority,
                    "symbol_pattern": r.symbol_pattern,
                    "exchange": r.exchange,
                    "position_type": r.position_type,
                    "take_profit": r.take_profit,
                    "stop_loss": r.stop_loss,
                    "time_conditions": r.time_conditions,
                }
                for r in rules
            ],
        }

    async def save_rules(self, user_id: str, rules: Dict[str, Any]) -> bool:
        """
        Save rules for user.

        :param user_id: User ID.
        :type user_id: str
        :param rules: Rules configuration.
        :type rules: Dict[str, Any]
        :returns: True if saved.
        :rtype: bool
        """

        await self.session.execute(
            delete(TradingRule).where(TradingRule.user_id == user_id)
        )

        for rule_data in rules.get("rules", []):
            rule = TradingRule(
                user_id=user_id,
                name=rule_data.get("name", "Unnamed Rule"),
                description=rule_data.get("description"),
                is_active=rule_data.get("is_active", True),
                priority=rule_data.get("priority", 100),
                symbol_pattern=rule_data.get("symbol_pattern"),
                exchange=rule_data.get("exchange"),
                position_type=rule_data.get("position_type"),
                take_profit=rule_data.get("take_profit", {}),
                stop_loss=rule_data.get("stop_loss", {}),
                time_conditions=rule_data.get("time_conditions", {}),
            )
            self.session.add(rule)

        await self.session.flush()
        return True

    async def delete_rules(self, user_id: str) -> bool:
        """
        Delete all rules for user.

        :param user_id: User ID.
        :type user_id: str
        :returns: True if deleted.
        :rtype: bool
        """
        result = await self.session.execute(
            delete(TradingRule).where(TradingRule.user_id == user_id)
        )
        return result.rowcount > 0

    async def get_rule_by_id(self, rule_id: str) -> Optional[TradingRule]:
        """
        Get a single rule by ID.

        :param rule_id: Rule ID.
        :type rule_id: str
        :returns: Trading rule or None.
        :rtype: Optional[TradingRule]
        """
        result = await self.session.execute(
            select(TradingRule).where(TradingRule.id == rule_id)
        )
        return result.scalar_one_or_none()

    async def get(self, rule_id: str) -> Optional[TradingRule]:
        """Alias for get_rule_by_id."""
        return await self.get_rule_by_id(rule_id)

    async def create(self, rule: TradingRule) -> TradingRule:
        """
        Create a new trading rule.

        :param rule: Trading rule to create.
        :type rule: TradingRule
        :returns: Created trading rule.
        :rtype: TradingRule
        """
        self.session.add(rule)
        await self.session.flush()
        await self.session.refresh(rule)
        return rule

    async def update(self, rule: TradingRule) -> TradingRule:
        """
        Update an existing trading rule.

        :param rule: Trading rule to update.
        :type rule: TradingRule
        :returns: Updated trading rule.
        :rtype: TradingRule
        """
        await self.session.flush()
        await self.session.refresh(rule)
        return rule

    async def delete(self, rule_id: str) -> bool:
        """
        Delete a trading rule by ID.

        :param rule_id: Rule ID.
        :type rule_id: str
        :returns: True if deleted.
        :rtype: bool
        """
        result = await self.session.execute(
            delete(TradingRule).where(TradingRule.id == rule_id)
        )
        return result.rowcount > 0

    async def get_all_by_user(self, user_id: str) -> List[TradingRule]:
        """
        Get all rules for a user.

        :param user_id: User ID.
        :type user_id: str
        :returns: List of trading rules.
        :rtype: List[TradingRule]
        """
        result = await self.session.execute(
            select(TradingRule)
            .where(TradingRule.user_id == user_id)
            .order_by(TradingRule.priority)
        )
        return list(result.scalars().all())

    async def get_by_user(
        self,
        user_id: str,
        is_active: Optional[bool] = None,
        symbol: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[TradingRule]:
        """
        Get rules for a user with filtering.

        :param user_id: User ID.
        :type user_id: str
        :param is_active: Filter by active status.
        :type is_active: Optional[bool]
        :param symbol: Filter by symbol.
        :type symbol: Optional[str]
        :param limit: Max results.
        :type limit: int
        :param offset: Pagination offset.
        :type offset: int
        :returns: List of trading rules.
        :rtype: List[TradingRule]
        """
        query = select(TradingRule).where(TradingRule.user_id == user_id)

        if is_active is not None:
            query = query.where(TradingRule.is_active == is_active)
        if symbol:
            query = query.where(TradingRule.symbol == symbol)

        query = query.order_by(TradingRule.priority).limit(limit).offset(offset)

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_executions(
        self,
        rule_id: str,
        limit: int = 50,
    ) -> List[Any]:
        """
        Get rule execution history.

        Note: Rule execution tracking is not yet implemented.
        This method returns an empty list for now.

        :param rule_id: Rule ID.
        :type rule_id: str
        :param limit: Maximum executions to return.
        :type limit: int
        :returns: List of rule executions.
        :rtype: List[Any]
        """
        return []


class PostgresTradeLogRepository(TradeLogRepository):
    """
    PostgreSQL implementation for trade log repository.

    :ivar session: Database session.
    """

    def __init__(self, session: AsyncSession) -> None:
        """
        Initialize repository.

        :param session: Database session.
        :type session: AsyncSession
        """
        self.session = session

    async def log_trade(
        self,
        user_id: str,
        trade_data: Dict[str, Any],
    ) -> str:
        """
        Log a trade execution.

        :param user_id: User ID.
        :type user_id: str
        :param trade_data: Trade data.
        :type trade_data: Dict[str, Any]
        :returns: Trade log ID.
        :rtype: str
        """
        trade_log = TradeLog(
            user_id=user_id,
            broker_account_id=trade_data.get("broker_account_id"),
            rule_id=trade_data.get("rule_id"),
            symbol=trade_data["symbol"],
            exchange=trade_data["exchange"],
            side=trade_data["side"],
            quantity=trade_data["quantity"],
            price=trade_data["price"],
            order_id=trade_data.get("order_id"),
            order_type=trade_data.get("order_type", "MARKET"),
            trigger_type=trade_data.get("trigger_type"),
            trigger_price=trade_data.get("trigger_price"),
            pnl=trade_data.get("pnl"),
            status=trade_data.get("status", "EXECUTED"),
            error_message=trade_data.get("error_message"),
            metadata_=trade_data.get("metadata", {}),
        )
        self.session.add(trade_log)
        await self.session.flush()
        return trade_log.id

    async def get_trade_history(
        self,
        user_id: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """
        Get trade history for user.

        :param user_id: User ID.
        :type user_id: str
        :param start_date: Start date filter.
        :type start_date: Optional[datetime]
        :param end_date: End date filter.
        :type end_date: Optional[datetime]
        :param limit: Max records.
        :type limit: int
        :returns: List of trade records.
        :rtype: List[Dict[str, Any]]
        """
        query = select(TradeLog).where(TradeLog.user_id == user_id)

        if start_date:
            query = query.where(TradeLog.executed_at >= start_date)
        if end_date:
            query = query.where(TradeLog.executed_at <= end_date)

        query = query.order_by(TradeLog.executed_at.desc()).limit(limit)

        result = await self.session.execute(query)
        trades = result.scalars().all()

        return [
            {
                "id": t.id,
                "symbol": t.symbol,
                "exchange": t.exchange,
                "side": t.side,
                "quantity": t.quantity,
                "price": t.price,
                "order_id": t.order_id,
                "order_type": t.order_type,
                "trigger_type": t.trigger_type,
                "trigger_price": t.trigger_price,
                "pnl": t.pnl,
                "status": t.status,
                "executed_at": t.executed_at.isoformat(),
            }
            for t in trades
        ]

    async def get_by_user(
        self,
        user_id: str,
        symbol: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[TradeLog]:
        """
        Get trades for user with filtering.

        :param user_id: User ID.
        :type user_id: str
        :param symbol: Filter by symbol.
        :type symbol: Optional[str]
        :param start_date: Start date filter.
        :type start_date: Optional[datetime]
        :param end_date: End date filter.
        :type end_date: Optional[datetime]
        :param limit: Max records.
        :type limit: int
        :param offset: Pagination offset.
        :type offset: int
        :returns: List of trade logs.
        :rtype: List[TradeLog]
        """
        query = select(TradeLog).where(TradeLog.user_id == user_id)

        if symbol:
            query = query.where(TradeLog.symbol == symbol)
        if start_date:
            query = query.where(TradeLog.executed_at >= start_date)
        if end_date:
            query = query.where(TradeLog.executed_at <= end_date)

        query = query.order_by(TradeLog.executed_at.desc()).limit(limit).offset(offset)

        result = await self.session.execute(query)
        return list(result.scalars().all())


class PostgresBrokerAccountRepository(BaseRepository[BrokerAccount]):
    """
    PostgreSQL implementation for broker account repository.

    :ivar session: Database session.
    """

    model_class = BrokerAccount

    def __init__(self, session: AsyncSession) -> None:
        """
        Initialize repository.

        :param session: Database session.
        :type session: AsyncSession
        """
        self.session = session

    async def get(self, id: str) -> Optional[BrokerAccount]:
        """
        Get broker account by ID.

        :param id: Account ID.
        :type id: str
        :returns: Broker account or None.
        :rtype: Optional[BrokerAccount]
        """
        result = await self.session.execute(
            select(BrokerAccount).where(BrokerAccount.id == id)
        )
        return result.scalar_one_or_none()

    async def get_by_user_and_broker(
        self, user_id: str, broker_id: str
    ) -> Optional[BrokerAccount]:
        """
        Get broker account for user and broker.

        :param user_id: User ID.
        :type user_id: str
        :param broker_id: Broker ID.
        :type broker_id: str
        :returns: Broker account or None.
        :rtype: Optional[BrokerAccount]
        """
        result = await self.session.execute(
            select(BrokerAccount).where(
                and_(
                    BrokerAccount.user_id == user_id,
                    BrokerAccount.broker_id == broker_id,
                )
            )
        )
        return result.scalar_one_or_none()

    async def get_all(self) -> List[BrokerAccount]:
        """
        Get all broker accounts.

        :returns: List of accounts.
        :rtype: List[BrokerAccount]
        """
        result = await self.session.execute(select(BrokerAccount))
        return list(result.scalars().all())

    async def find(self, **filters: Any) -> List[BrokerAccount]:
        """
        Find broker accounts by filters.

        :param filters: Filter conditions.
        :type filters: Any
        :returns: Matching accounts.
        :rtype: List[BrokerAccount]
        """
        query = select(BrokerAccount)
        for key, value in filters.items():
            if hasattr(BrokerAccount, key):
                query = query.where(getattr(BrokerAccount, key) == value)
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def create(self, entity: BrokerAccount) -> BrokerAccount:
        """
        Create broker account.

        :param entity: Account to create.
        :type entity: BrokerAccount
        :returns: Created account.
        :rtype: BrokerAccount
        """
        self.session.add(entity)
        await self.session.flush()
        await self.session.refresh(entity)
        return entity

    async def update(self, id: str, entity: BrokerAccount) -> Optional[BrokerAccount]:
        """
        Update broker account.

        :param id: Account ID.
        :type id: str
        :param entity: Updated data.
        :type entity: BrokerAccount
        :returns: Updated account or None.
        :rtype: Optional[BrokerAccount]
        """
        existing = await self.get(id)
        if not existing:
            return None

        for key, value in entity.__dict__.items():
            if not key.startswith("_") and hasattr(existing, key):
                setattr(existing, key, value)

        await self.session.flush()
        await self.session.refresh(existing)
        return existing

    async def update_tokens(
        self,
        id: str,
        access_token: str,
        refresh_token: Optional[str] = None,
        expires_at: Optional[datetime] = None,
    ) -> bool:
        """
        Update broker tokens.

        :param id: Account ID.
        :type id: str
        :param access_token: New access token.
        :type access_token: str
        :param refresh_token: New refresh token.
        :type refresh_token: Optional[str]
        :param expires_at: Token expiration.
        :type expires_at: Optional[datetime]
        :returns: True if updated.
        :rtype: bool
        """
        values = {"access_token": access_token}
        if refresh_token:
            values["refresh_token"] = refresh_token
        if expires_at:
            values["token_expires_at"] = expires_at

        result = await self.session.execute(
            update(BrokerAccount).where(BrokerAccount.id == id).values(**values)
        )
        return result.rowcount > 0

    async def delete(self, id: str) -> bool:
        """
        Delete broker account.

        :param id: Account ID.
        :type id: str
        :returns: True if deleted.
        :rtype: bool
        """
        result = await self.session.execute(
            delete(BrokerAccount).where(BrokerAccount.id == id)
        )
        return result.rowcount > 0

    async def exists(self, id: str) -> bool:
        """
        Check if account exists.

        :param id: Account ID.
        :type id: str
        :returns: True if exists.
        :rtype: bool
        """
        result = await self.session.execute(
            select(BrokerAccount.id).where(BrokerAccount.id == id).limit(1)
        )
        return result.scalar_one_or_none() is not None

    async def get_active_by_user(self, user_id: str) -> Optional[BrokerAccount]:
        """
        Get active broker account for user.

        :param user_id: User ID.
        :type user_id: str
        :returns: Active broker account or None.
        :rtype: Optional[BrokerAccount]
        """
        result = await self.session.execute(
            select(BrokerAccount).where(
                and_(
                    BrokerAccount.user_id == user_id,
                    BrokerAccount.is_active == True,
                )
            )
        )
        return result.scalar_one_or_none()

    async def get_all_by_user(self, user_id: str) -> List[BrokerAccount]:
        """
        Get all broker accounts for user.

        :param user_id: User ID.
        :type user_id: str
        :returns: List of broker accounts.
        :rtype: List[BrokerAccount]
        """
        result = await self.session.execute(
            select(BrokerAccount).where(BrokerAccount.user_id == user_id)
        )
        return list(result.scalars().all())

    async def deactivate(self, id: str) -> bool:
        """
        Deactivate broker account.

        :param id: Account ID.
        :type id: str
        :returns: True if deactivated.
        :rtype: bool
        """
        result = await self.session.execute(
            update(BrokerAccount)
            .where(BrokerAccount.id == id)
            .values(is_active=False, access_token=None, refresh_token=None)
        )
        return result.rowcount > 0

    async def create_or_update(
        self,
        user_id: str,
        broker_id: str,
        api_key: str,
        api_secret: str,
        access_token: Optional[str] = None,
        refresh_token: Optional[str] = None,
        token_expires_at: Optional[datetime] = None,
    ) -> BrokerAccount:
        """
        Create or update broker account for user.

        :param user_id: User ID.
        :param broker_id: Broker identifier.
        :param api_key: Encrypted API key.
        :param api_secret: Encrypted API secret.
        :param access_token: Encrypted access token.
        :param refresh_token: Encrypted refresh token.
        :param token_expires_at: Token expiration.
        :returns: Broker account.
        """
        existing = await self.get_by_user_and_broker(user_id, broker_id)

        if existing:
            existing.api_key = api_key
            existing.api_secret = api_secret
            existing.is_active = True
            if access_token:
                existing.access_token = access_token
            if refresh_token:
                existing.refresh_token = refresh_token
            if token_expires_at:
                existing.token_expires_at = token_expires_at
            await self.session.flush()
            await self.session.refresh(existing)
            return existing
        else:
            account = BrokerAccount(
                user_id=user_id,
                broker_id=broker_id,
                api_key=api_key,
                api_secret=api_secret,
                access_token=access_token,
                refresh_token=refresh_token,
                token_expires_at=token_expires_at,
                is_active=True,
            )
            self.session.add(account)
            await self.session.flush()
            await self.session.refresh(account)
            return account
