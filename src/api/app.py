"""
FastAPI application factory and configuration.

:copyright: (c) 2025
:license: MIT
"""

import logging
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI

from src.api.middleware import setup_middleware
from src.api.routers import (
    auth_router,
    rules_router,
    trading_router,
    user_router,
    websocket_router,
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """
    Application lifespan handler.

    Manages startup and shutdown events.

    :param app: FastAPI application.
    :type app: FastAPI
    """

    logger.info("Starting application...")

    try:
        from src.database import get_database_manager

        db = get_database_manager()
        await db.connect()
        logger.info("Database connected")
    except Exception as e:
        logger.warning(f"Database not configured: {e}")

    try:
        from src.cache import get_redis_cache

        cache = get_redis_cache()
        await cache.connect()
        logger.info("Redis connected")
    except Exception as e:
        logger.warning(f"Redis not configured: {e}")

    from src.core.events import get_event_bus

    event_bus = get_event_bus()
    logger.info("Event bus initialized")

    yield

    logger.info("Shutting down application...")

    try:
        db = get_database_manager()
        await db.disconnect()
    except Exception:
        pass

    try:
        cache = get_redis_cache()
        await cache.disconnect()
    except Exception:
        pass


def create_app(
    title: str = "Trading API",
    description: str = "Rule-based automated trading system",
    version: str = "1.0.0",
    debug: bool = False,
) -> FastAPI:
    """
    Create FastAPI application.

    :param title: API title.
    :type title: str
    :param description: API description.
    :type description: str
    :param version: API version.
    :type version: str
    :param debug: Enable debug mode.
    :type debug: bool
    :returns: FastAPI application.
    :rtype: FastAPI
    """
    app = FastAPI(
        title=title,
        description=description,
        version=version,
        debug=debug,
        lifespan=lifespan,
        docs_url="/docs" if debug else None,
        redoc_url="/redoc" if debug else None,
    )

    setup_middleware(app)

    app.include_router(auth_router)
    app.include_router(user_router)
    app.include_router(trading_router)
    app.include_router(rules_router)
    app.include_router(websocket_router)

    @app.get("/health", tags=["Health"])
    async def health_check() -> dict:
        """Health check endpoint."""
        return {"status": "healthy", "version": version}

    @app.get("/ready", tags=["Health"])
    async def readiness_check() -> dict:
        """Readiness check endpoint."""
        checks = {
            "database": False,
            "cache": False,
        }

        try:
            from src.database import get_database_manager

            db = get_database_manager()
            checks["database"] = db.is_connected
        except Exception:
            pass

        try:
            from src.cache import get_redis_cache

            cache = get_redis_cache()
            checks["cache"] = cache.is_connected
        except Exception:
            pass

        ready = all(checks.values())
        return {
            "status": "ready" if ready else "not_ready",
            "checks": checks,
        }

    return app


app = create_app(debug=True)
