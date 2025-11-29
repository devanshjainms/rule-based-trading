"""
Celery application configuration.

:copyright: (c) 2025
:license: MIT
"""

import os

from celery import Celery


REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")


celery_app = Celery(
    "trading_workers",
    broker=REDIS_URL,
    backend=REDIS_URL,
    include=[
        "src.workers.tasks",
    ],
)


celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    task_time_limit=300,
    task_soft_time_limit=240,
    worker_prefetch_multiplier=1,
    worker_concurrency=4,
    result_expires=3600,
    beat_schedule={
        "cleanup-expired-sessions": {
            "task": "src.workers.tasks.cleanup_expired_sessions",
            "schedule": 300.0,
        },
        "cleanup-old-trade-logs": {
            "task": "src.workers.tasks.cleanup_old_trade_logs",
            "schedule": 86400.0,
        },
        "sync-broker-positions": {
            "task": "src.workers.tasks.sync_broker_positions",
            "schedule": 60.0,
        },
        "process-pending-notifications": {
            "task": "src.workers.tasks.process_pending_notifications",
            "schedule": 30.0,
        },
        "health-check": {
            "task": "src.workers.tasks.health_check",
            "schedule": 60.0,
        },
    },
    task_routes={
        "src.workers.tasks.send_email": {"queue": "notifications"},
        "src.workers.tasks.send_sms": {"queue": "notifications"},
        "src.workers.tasks.process_rule_trigger": {"queue": "trading"},
        "src.workers.tasks.sync_broker_positions": {"queue": "trading"},
    },
)


def get_celery_app() -> Celery:
    """Get Celery application instance."""
    return celery_app
