"""
FastAPI application middleware.

Provides request logging, error handling, and user context.

:copyright: (c) 2025
:license: MIT
"""

import logging
import time
import uuid
from typing import Callable

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware for logging all requests.

    Logs request method, path, duration, and status code.
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process request and log details.

        :param request: HTTP request.
        :type request: Request
        :param call_next: Next middleware.
        :type call_next: Callable
        :returns: HTTP response.
        :rtype: Response
        """

        request_id = str(uuid.uuid4())[:8]
        request.state.request_id = request_id

        start_time = time.perf_counter()

        logger.info(
            f"[{request_id}] {request.method} {request.url.path} "
            f"from {request.client.host if request.client else 'unknown'}"
        )

        try:
            response = await call_next(request)
        except Exception as e:
            logger.error(f"[{request_id}] Request failed: {e}")
            raise

        duration = time.perf_counter() - start_time

        logger.info(f"[{request_id}] {response.status_code} in {duration:.3f}s")

        response.headers["X-Request-ID"] = request_id
        response.headers["X-Response-Time"] = f"{duration:.3f}s"

        return response


class ErrorHandlingMiddleware(BaseHTTPMiddleware):
    """
    Middleware for handling unhandled exceptions.

    Converts exceptions to JSON responses.
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process request and handle errors.

        :param request: HTTP request.
        :type request: Request
        :param call_next: Next middleware.
        :type call_next: Callable
        :returns: HTTP response.
        :rtype: Response
        """
        try:
            return await call_next(request)
        except Exception as e:
            request_id = getattr(request.state, "request_id", "unknown")
            logger.exception(f"[{request_id}] Unhandled exception: {e}")

            return JSONResponse(
                status_code=500,
                content={
                    "error": "Internal server error",
                    "request_id": request_id,
                },
            )


def setup_cors(app: FastAPI, origins: list[str] | None = None) -> None:
    """
    Configure CORS middleware.

    :param app: FastAPI application.
    :type app: FastAPI
    :param origins: Allowed origins.
    :type origins: list[str] | None
    """
    if origins is None:
        origins = [
            "http://localhost:3000",
            "http://localhost:8000",
            "http://127.0.0.1:3000",
            "http://127.0.0.1:8000",
        ]

    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )


def setup_middleware(app: FastAPI) -> None:
    """
    Configure all middleware.

    :param app: FastAPI application.
    :type app: FastAPI
    """

    app.add_middleware(ErrorHandlingMiddleware)
    app.add_middleware(RequestLoggingMiddleware)
    setup_cors(app)
