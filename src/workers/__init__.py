"""
Workers package.

Provides Celery background tasks for async processing.

:copyright: (c) 2025
:license: MIT
"""

from src.workers.celery_app import celery_app, get_celery_app
from src.workers.tasks import (
    cleanup_expired_sessions,
    cleanup_old_trade_logs,
    close_position_async,
    collect_metrics,
    health_check,
    process_pending_notifications,
    process_rule_trigger,
    send_alert_notification,
    send_email,
    sync_broker_positions,
)

__all__ = [
    "celery_app",
    "get_celery_app",
    "cleanup_expired_sessions",
    "cleanup_old_trade_logs",
    "process_rule_trigger",
    "sync_broker_positions",
    "close_position_async",
    "send_email",
    "process_pending_notifications",
    "send_alert_notification",
    "health_check",
    "collect_metrics",
]
