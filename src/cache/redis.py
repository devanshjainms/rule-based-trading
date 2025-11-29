"""
Redis cache implementations.

Provides Redis-backed session storage and caching for high-performance
session lookups and real-time data caching.

:copyright: (c) 2025
:license: MIT
"""

import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

import redis.asyncio as redis
from redis.asyncio import Redis

from src.core.repositories import SessionRepository

logger = logging.getLogger(__name__)


class RedisConfig:
    """
    Redis configuration.

    :ivar host: Redis host.
    :ivar port: Redis port.
    :ivar db: Redis database number.
    :ivar password: Redis password.
    :ivar ssl: Use SSL connection.
    :ivar prefix: Key prefix for namespacing.
    :ivar default_ttl: Default TTL in seconds.
    """

    def __init__(
        self,
        host: str = "localhost",
        port: int = 6379,
        db: int = 0,
        password: Optional[str] = None,
        ssl: bool = False,
        prefix: str = "trading:",
        default_ttl: int = 86400,
    ) -> None:
        """
        Initialize Redis configuration.

        :param host: Redis server host.
        :type host: str
        :param port: Redis server port.
        :type port: int
        :param db: Database number.
        :type db: int
        :param password: Authentication password.
        :type password: Optional[str]
        :param ssl: Enable SSL.
        :type ssl: bool
        :param prefix: Key prefix.
        :type prefix: str
        :param default_ttl: Default expiration.
        :type default_ttl: int
        """
        self.host = host
        self.port = port
        self.db = db
        self.password = password
        self.ssl = ssl
        self.prefix = prefix
        self.default_ttl = default_ttl

    @property
    def url(self) -> str:
        """
        Get Redis connection URL.

        :returns: Redis URL.
        :rtype: str
        """
        scheme = "rediss" if self.ssl else "redis"
        auth = f":{self.password}@" if self.password else ""
        return f"{scheme}://{auth}{self.host}:{self.port}/{self.db}"


class RedisCache:
    """
    Redis cache manager.

    Provides async Redis operations with automatic serialization.

    Example::

        cache = RedisCache(config)
        await cache.init()

        await cache.set("key", {"data": "value"}, ttl=3600)
        data = await cache.get("key")

        await cache.close()
    """

    def __init__(self, config: Optional[RedisConfig] = None) -> None:
        """
        Initialize cache manager.

        :param config: Redis configuration.
        :type config: Optional[RedisConfig]
        """
        self.config = config or RedisConfig()
        self._client: Optional[Redis] = None

    @property
    def client(self) -> Redis:
        """
        Get Redis client.

        :returns: Redis client.
        :rtype: Redis
        :raises RuntimeError: If not initialized.
        """
        if self._client is None:
            raise RuntimeError("Redis not initialized. Call init() first.")
        return self._client

    async def init(self) -> None:
        """Initialize Redis connection."""
        logger.info(f"Connecting to Redis at {self.config.host}:{self.config.port}")
        self._client = redis.from_url(
            self.config.url,
            encoding="utf-8",
            decode_responses=True,
        )

        await self._client.ping()
        logger.info("Redis connection established")

    async def close(self) -> None:
        """Close Redis connection."""
        if self._client:
            await self._client.close()
            self._client = None
            logger.info("Redis connection closed")

    async def connect(self) -> None:
        """Alias for init() - connects to Redis."""
        await self.init()

    async def disconnect(self) -> None:
        """Alias for close() - disconnects from Redis."""
        await self.close()

    def _key(self, key: str) -> str:
        """
        Prefix key with namespace.

        :param key: Base key.
        :type key: str
        :returns: Prefixed key.
        :rtype: str
        """
        return f"{self.config.prefix}{key}"

    async def get(self, key: str) -> Optional[Any]:
        """
        Get value from cache.

        :param key: Cache key.
        :type key: str
        :returns: Cached value or None.
        :rtype: Optional[Any]
        """
        value = await self.client.get(self._key(key))
        if value:
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                return value
        return None

    async def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None,
    ) -> bool:
        """
        Set value in cache.

        :param key: Cache key.
        :type key: str
        :param value: Value to cache.
        :type value: Any
        :param ttl: Time to live in seconds.
        :type ttl: Optional[int]
        :returns: True if set.
        :rtype: bool
        """
        serialized = json.dumps(value) if not isinstance(value, str) else value
        ttl = ttl or self.config.default_ttl
        await self.client.setex(self._key(key), ttl, serialized)
        return True

    async def delete(self, key: str) -> bool:
        """
        Delete from cache.

        :param key: Cache key.
        :type key: str
        :returns: True if deleted.
        :rtype: bool
        """
        result = await self.client.delete(self._key(key))
        return result > 0

    async def exists(self, key: str) -> bool:
        """
        Check if key exists.

        :param key: Cache key.
        :type key: str
        :returns: True if exists.
        :rtype: bool
        """
        return await self.client.exists(self._key(key)) > 0

    async def expire(self, key: str, ttl: int) -> bool:
        """
        Set key expiration.

        :param key: Cache key.
        :type key: str
        :param ttl: New TTL in seconds.
        :type ttl: int
        :returns: True if set.
        :rtype: bool
        """
        return await self.client.expire(self._key(key), ttl)

    async def hget(self, key: str, field: str) -> Optional[str]:
        """
        Get hash field.

        :param key: Hash key.
        :type key: str
        :param field: Field name.
        :type field: str
        :returns: Field value or None.
        :rtype: Optional[str]
        """
        return await self.client.hget(self._key(key), field)

    async def hset(self, key: str, field: str, value: str) -> bool:
        """
        Set hash field.

        :param key: Hash key.
        :type key: str
        :param field: Field name.
        :type field: str
        :param value: Field value.
        :type value: str
        :returns: True if set.
        :rtype: bool
        """
        await self.client.hset(self._key(key), field, value)
        return True

    async def hgetall(self, key: str) -> Dict[str, str]:
        """
        Get all hash fields.

        :param key: Hash key.
        :type key: str
        :returns: Hash as dict.
        :rtype: Dict[str, str]
        """
        return await self.client.hgetall(self._key(key))

    async def hmset(self, key: str, mapping: Dict[str, str]) -> bool:
        """
        Set multiple hash fields.

        :param key: Hash key.
        :type key: str
        :param mapping: Field-value mapping.
        :type mapping: Dict[str, str]
        :returns: True if set.
        :rtype: bool
        """
        if mapping:
            await self.client.hset(self._key(key), mapping=mapping)
        return True

    async def keys(self, pattern: str = "*") -> List[str]:
        """
        Find keys matching pattern.

        :param pattern: Key pattern.
        :type pattern: str
        :returns: Matching keys.
        :rtype: List[str]
        """
        full_pattern = self._key(pattern)
        keys = await self.client.keys(full_pattern)
        prefix_len = len(self.config.prefix)
        return [k[prefix_len:] for k in keys]

    async def publish(self, channel: str, message: Any) -> int:
        """
        Publish message to channel.

        :param channel: Channel name.
        :type channel: str
        :param message: Message to publish.
        :type message: Any
        :returns: Number of subscribers.
        :rtype: int
        """
        serialized = json.dumps(message) if not isinstance(message, str) else message
        return await self.client.publish(self._key(channel), serialized)


class RedisSessionRepository(SessionRepository):
    """
    Redis-backed session repository.

    Provides fast session lookups and automatic expiration.

    Example::

        repo = RedisSessionRepository(cache)
        await repo.save_session("user123", {"token": "xyz"}, ttl=3600)
        session = await repo.get_session("user123")
    """

    def __init__(self, cache: RedisCache) -> None:
        """
        Initialize repository.

        :param cache: Redis cache instance.
        :type cache: RedisCache
        """
        self.cache = cache
        self._session_prefix = "session:"
        self._active_sessions_key = "active_sessions"

    def _session_key(self, user_id: str) -> str:
        """Get session key for user."""
        return f"{self._session_prefix}{user_id}"

    async def get_session(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Get session for user.

        :param user_id: User ID.
        :type user_id: str
        :returns: Session data or None.
        :rtype: Optional[Dict[str, Any]]
        """
        data = await self.cache.hgetall(self._session_key(user_id))
        if not data:
            return None

        session = {}
        for key, value in data.items():
            try:
                session[key] = json.loads(value)
            except (json.JSONDecodeError, TypeError):
                session[key] = value

        return session

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
        :param ttl: TTL in seconds.
        :type ttl: Optional[int]
        :returns: True if saved.
        :rtype: bool
        """
        key = self._session_key(user_id)
        ttl = ttl or self.cache.config.default_ttl

        mapping = {}
        for k, v in session_data.items():
            if isinstance(v, (dict, list)):
                mapping[k] = json.dumps(v)
            elif isinstance(v, datetime):
                mapping[k] = v.isoformat()
            else:
                mapping[k] = str(v)

        await self.cache.hmset(key, mapping)
        await self.cache.expire(key, ttl)

        await self.cache.client.sadd(
            self.cache._key(self._active_sessions_key), user_id
        )

        return True

    async def delete_session(self, user_id: str) -> bool:
        """
        Delete user session.

        :param user_id: User ID.
        :type user_id: str
        :returns: True if deleted.
        :rtype: bool
        """
        deleted = await self.cache.delete(self._session_key(user_id))

        await self.cache.client.srem(
            self.cache._key(self._active_sessions_key), user_id
        )

        return deleted

    async def refresh_session(self, user_id: str, ttl: int) -> bool:
        """
        Refresh session TTL.

        :param user_id: User ID.
        :type user_id: str
        :param ttl: New TTL.
        :type ttl: int
        :returns: True if refreshed.
        :rtype: bool
        """
        key = self._session_key(user_id)
        if await self.cache.exists(key):
            await self.cache.expire(key, ttl)

            await self.cache.hset(key, "last_activity", datetime.utcnow().isoformat())
            return True
        return False

    async def get_all_active_sessions(self) -> List[str]:
        """
        Get all active session user IDs.

        :returns: List of user IDs.
        :rtype: List[str]
        """
        members = await self.cache.client.smembers(
            self.cache._key(self._active_sessions_key)
        )

        active = []
        for user_id in members:
            if await self.cache.exists(self._session_key(user_id)):
                active.append(user_id)
            else:

                await self.cache.client.srem(
                    self.cache._key(self._active_sessions_key), user_id
                )

        return active

    async def get_session_field(self, user_id: str, field: str) -> Optional[str]:
        """
        Get specific session field.

        :param user_id: User ID.
        :type user_id: str
        :param field: Field name.
        :type field: str
        :returns: Field value or None.
        :rtype: Optional[str]
        """
        return await self.cache.hget(self._session_key(user_id), field)

    async def set_session_field(self, user_id: str, field: str, value: Any) -> bool:
        """
        Set specific session field.

        :param user_id: User ID.
        :type user_id: str
        :param field: Field name.
        :type field: str
        :param value: Field value.
        :type value: Any
        :returns: True if set.
        :rtype: bool
        """
        serialized = (
            json.dumps(value) if isinstance(value, (dict, list)) else str(value)
        )
        return await self.cache.hset(self._session_key(user_id), field, serialized)


class RedisPriceCache:
    """
    Redis cache for real-time price data.

    Caches tick data with short TTL for fast lookups.

    Example::

        price_cache = RedisPriceCache(cache)
        await price_cache.set_price(12345, 1500.50)
        price = await price_cache.get_price(12345)
    """

    def __init__(self, cache: RedisCache, ttl: int = 5) -> None:
        """
        Initialize price cache.

        :param cache: Redis cache.
        :type cache: RedisCache
        :param ttl: Price TTL in seconds.
        :type ttl: int
        """
        self.cache = cache
        self.ttl = ttl
        self._prefix = "price:"

    async def get_price(self, instrument_token: int) -> Optional[float]:
        """
        Get cached price.

        :param instrument_token: Instrument token.
        :type instrument_token: int
        :returns: Price or None.
        :rtype: Optional[float]
        """
        value = await self.cache.get(f"{self._prefix}{instrument_token}")
        return float(value) if value else None

    async def set_price(self, instrument_token: int, price: float) -> bool:
        """
        Cache price.

        :param instrument_token: Instrument token.
        :type instrument_token: int
        :param price: Price value.
        :type price: float
        :returns: True if cached.
        :rtype: bool
        """
        return await self.cache.set(
            f"{self._prefix}{instrument_token}", price, ttl=self.ttl
        )

    async def get_prices(self, tokens: List[int]) -> Dict[int, float]:
        """
        Get multiple prices.

        :param tokens: List of instrument tokens.
        :type tokens: List[int]
        :returns: Token to price mapping.
        :rtype: Dict[int, float]
        """
        pipe = self.cache.client.pipeline()
        for token in tokens:
            pipe.get(self.cache._key(f"{self._prefix}{token}"))

        results = await pipe.execute()
        return {
            token: float(price)
            for token, price in zip(tokens, results)
            if price is not None
        }

    async def set_prices(self, prices: Dict[int, float]) -> bool:
        """
        Cache multiple prices.

        :param prices: Token to price mapping.
        :type prices: Dict[int, float]
        :returns: True if cached.
        :rtype: bool
        """
        pipe = self.cache.client.pipeline()
        for token, price in prices.items():
            key = self.cache._key(f"{self._prefix}{token}")
            pipe.setex(key, self.ttl, str(price))

        await pipe.execute()
        return True


_redis_cache: Optional[RedisCache] = None


def get_redis_cache() -> RedisCache:
    """
    Get global Redis cache instance.

    :returns: Redis cache.
    :rtype: RedisCache
    """
    global _redis_cache
    if _redis_cache is None:
        _redis_cache = RedisCache()
    return _redis_cache


def configure_redis(config: RedisConfig) -> RedisCache:
    """
    Configure global Redis cache.

    :param config: Redis configuration.
    :type config: RedisConfig
    :returns: Configured cache.
    :rtype: RedisCache
    """
    global _redis_cache
    _redis_cache = RedisCache(config)
    return _redis_cache
