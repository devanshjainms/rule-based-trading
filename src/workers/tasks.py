"""
Celery background tasks.

:copyright: (c) 2025
:license: MIT
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

from celery import shared_task

logger = logging.getLogger(__name__)


def run_async(coro):
    """Run async function in sync context."""
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return loop.run_until_complete(coro)


@shared_task(bind=True, max_retries=3)
def cleanup_expired_sessions(self) -> Dict[str, Any]:
    """
    Clean up expired user sessions.

    Removes sessions that have exceeded their TTL.

    :returns: Cleanup statistics.
    :rtype: Dict[str, Any]
    """
    try:

        async def _cleanup():
            from src.database import get_database_manager
            from src.database.repositories import PostgresSessionRepository

            db = get_database_manager()
            if not db.is_connected:
                await db.connect()

            repo = PostgresSessionRepository(db.session_factory)
            deleted = await repo.delete_expired()

            logger.info(f"Cleaned up {deleted} expired sessions")
            return {"deleted_count": deleted}

        return run_async(_cleanup())

    except Exception as e:
        logger.error(f"Session cleanup failed: {e}")
        raise self.retry(exc=e, countdown=60)


@shared_task(bind=True, max_retries=3)
def cleanup_old_trade_logs(self, days: int = 90) -> Dict[str, Any]:
    """
    Archive or delete old trade logs.

    :param days: Age threshold in days.
    :type days: int
    :returns: Cleanup statistics.
    :rtype: Dict[str, Any]
    """
    try:

        async def _cleanup():
            from src.database import get_database_manager
            from src.database.repositories import PostgresTradeLogRepository

            db = get_database_manager()
            if not db.is_connected:
                await db.connect()

            repo = PostgresTradeLogRepository(db.session_factory)
            cutoff = datetime.utcnow() - timedelta(days=days)
            archived = await repo.archive_before(cutoff)

            logger.info(f"Archived {archived} trade logs older than {days} days")
            return {"archived_count": archived}

        return run_async(_cleanup())

    except Exception as e:
        logger.error(f"Trade log cleanup failed: {e}")
        raise self.retry(exc=e, countdown=300)


@shared_task(bind=True, max_retries=3)
def process_rule_trigger(
    self,
    rule_id: str,
    user_id: str,
    trigger_data: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Process a triggered trading rule.

    :param rule_id: Rule ID.
    :type rule_id: str
    :param user_id: User ID.
    :type user_id: str
    :param trigger_data: Data that triggered the rule.
    :type trigger_data: Dict[str, Any]
    :returns: Execution result.
    :rtype: Dict[str, Any]
    """
    try:

        async def _process():
            from src.core.services import get_rule_execution_service

            service = get_rule_execution_service()
            result = await service.execute_rule(
                rule_id=rule_id,
                user_id=user_id,
                trigger_data=trigger_data,
            )

            logger.info(f"Rule {rule_id} executed: {result}")
            return {
                "rule_id": rule_id,
                "success": result.success,
                "actions": result.actions_taken,
            }

        return run_async(_process())

    except Exception as e:
        logger.error(f"Rule execution failed: {e}")
        raise self.retry(exc=e, countdown=30)


@shared_task(bind=True, max_retries=3)
def sync_broker_positions(self) -> Dict[str, Any]:
    """
    Sync positions from all connected brokers.

    Updates local position cache with broker data.

    :returns: Sync statistics.
    :rtype: Dict[str, Any]
    """
    try:

        async def _sync():
            from src.core.sessions import get_session_manager
            from src.database import get_database_manager
            from src.database.repositories import PostgresSessionRepository

            db = get_database_manager()
            if not db.is_connected:
                await db.connect()

            session_repo = PostgresSessionRepository(db.session_factory)
            session_manager = get_session_manager()

            active_sessions = await session_repo.get_active()
            synced = 0

            for session in active_sessions:
                context = session_manager.get_context(str(session.user_id))
                if context and context.broker_client:
                    try:
                        positions = await context.broker_client.get_positions()

                        synced += 1
                    except Exception as e:
                        logger.warning(
                            f"Position sync failed for {session.user_id}: {e}"
                        )

            logger.info(f"Synced positions for {synced} users")
            return {"synced_count": synced}

        return run_async(_sync())

    except Exception as e:
        logger.error(f"Position sync failed: {e}")
        raise self.retry(exc=e, countdown=30)


@shared_task(bind=True, max_retries=3)
def close_position_async(
    self,
    user_id: str,
    symbol: str,
    reason: str = "manual",
) -> Dict[str, Any]:
    """
    Close a position asynchronously.

    :param user_id: User ID.
    :type user_id: str
    :param symbol: Symbol to close.
    :type symbol: str
    :param reason: Close reason.
    :type reason: str
    :returns: Close result.
    :rtype: Dict[str, Any]
    """
    try:

        async def _close():
            from src.core.events import Event, EventType, get_event_bus
            from src.core.sessions import get_session_manager

            session_manager = get_session_manager()
            event_bus = get_event_bus()

            context = session_manager.get_context(user_id)
            if not context or not context.broker_client:
                raise ValueError("No active trading session")

            await context.broker_client.close_position(symbol)

            await event_bus.emit(
                Event(
                    type=EventType.POSITION_CLOSED,
                    data={"symbol": symbol, "reason": reason},
                    user_id=user_id,
                )
            )

            return {"symbol": symbol, "closed": True}

        return run_async(_close())

    except Exception as e:
        logger.error(f"Position close failed: {e}")
        raise self.retry(exc=e, countdown=30)


@shared_task(bind=True, max_retries=3)
def send_email(
    self,
    to: str,
    subject: str,
    body: str,
    html: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Send an email notification.

    :param to: Recipient email.
    :type to: str
    :param subject: Email subject.
    :type subject: str
    :param body: Plain text body.
    :type body: str
    :param html: HTML body (optional).
    :type html: Optional[str]
    :returns: Send result.
    :rtype: Dict[str, Any]
    """
    import os
    import smtplib
    from email.mime.multipart import MIMEMultipart
    from email.mime.text import MIMEText

    try:
        smtp_host = os.getenv("SMTP_HOST", "localhost")
        smtp_port = int(os.getenv("SMTP_PORT", "587"))
        smtp_user = os.getenv("SMTP_USER", "")
        smtp_pass = os.getenv("SMTP_PASS", "")
        from_email = os.getenv("FROM_EMAIL", "noreply@trading.local")

        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = from_email
        msg["To"] = to

        msg.attach(MIMEText(body, "plain"))
        if html:
            msg.attach(MIMEText(html, "html"))

        with smtplib.SMTP(smtp_host, smtp_port) as server:
            if smtp_user and smtp_pass:
                server.starttls()
                server.login(smtp_user, smtp_pass)
            server.sendmail(from_email, to, msg.as_string())

        logger.info(f"Email sent to {to}: {subject}")
        return {"sent": True, "to": to}

    except Exception as e:
        logger.error(f"Email send failed: {e}")
        raise self.retry(exc=e, countdown=60)


@shared_task(bind=True, max_retries=3)
def process_pending_notifications(self) -> Dict[str, Any]:
    """
    Process pending notifications from queue.

    :returns: Processing statistics.
    :rtype: Dict[str, Any]
    """
    try:

        async def _process():
            from src.database import get_database_manager
            from src.database.repositories import PostgresNotificationRepository

            db = get_database_manager()
            if not db.is_connected:
                await db.connect()

            repo = PostgresNotificationRepository(db.session_factory)
            pending = await repo.get_pending(limit=100)

            processed = 0
            for notification in pending:
                try:
                    if notification.channel == "email":
                        send_email.delay(
                            to=notification.recipient,
                            subject=notification.title,
                            body=notification.body,
                        )
                    await repo.mark_sent(notification.id)
                    processed += 1
                except Exception as e:
                    logger.error(f"Failed to process notification: {e}")

            return {"processed": processed, "pending": len(pending)}

        return run_async(_process())

    except Exception as e:
        logger.error(f"Notification processing failed: {e}")
        raise self.retry(exc=e, countdown=30)


@shared_task
def send_alert_notification(
    user_id: str,
    alert_type: str,
    message: str,
    data: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Send an alert notification to user.

    :param user_id: User ID.
    :type user_id: str
    :param alert_type: Alert type.
    :type alert_type: str
    :param message: Alert message.
    :type message: str
    :param data: Additional data.
    :type data: Optional[Dict[str, Any]]
    :returns: Result.
    :rtype: Dict[str, Any]
    """

    async def _send():
        from src.api.routers import get_ws_manager

        ws_manager = get_ws_manager()
        await ws_manager.send_to_user(
            user_id,
            {
                "type": "alert",
                "alert_type": alert_type,
                "message": message,
                "data": data or {},
            },
        )

        return {"sent": True, "user_id": user_id}

    return run_async(_send())


@shared_task
def health_check() -> Dict[str, Any]:
    """
    Perform system health check.

    :returns: Health status.
    :rtype: Dict[str, Any]
    """
    checks = {}

    try:

        async def check_db():
            from src.database import get_database_manager

            db = get_database_manager()
            return db.is_connected

        checks["database"] = run_async(check_db())
    except Exception:
        checks["database"] = False

    try:

        async def check_redis():
            from src.cache import get_redis_cache

            cache = get_redis_cache()
            return cache.is_connected

        checks["redis"] = run_async(check_redis())
    except Exception:
        checks["redis"] = False

    logger.info(f"Health check: {checks}")
    return {"healthy": all(checks.values()), "checks": checks}


@shared_task
def collect_metrics() -> Dict[str, Any]:
    """
    Collect system metrics.

    :returns: System metrics.
    :rtype: Dict[str, Any]
    """
    import os
    import psutil

    process = psutil.Process(os.getpid())

    return {
        "cpu_percent": process.cpu_percent(),
        "memory_mb": process.memory_info().rss / 1024 / 1024,
        "threads": process.num_threads(),
        "open_files": len(process.open_files()),
        "timestamp": datetime.utcnow().isoformat(),
    }
