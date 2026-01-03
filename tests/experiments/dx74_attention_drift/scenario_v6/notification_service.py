"""
Notification service module.
Focus: Security (F) and Error Handling (G) issues.
"""
import logging
import smtplib
import time
from email.mime.text import MIMEText
from typing import Any

logger = logging.getLogger(__name__)


def pre(condition):
    """Precondition decorator."""
    def decorator(func):
        return func
    return decorator


def post(condition):
    """Postcondition decorator."""
    def decorator(func):
        return func
    return decorator


# =============================================================================
# SECURITY ISSUES (F)
# =============================================================================

SMTP_HOST = "smtp.example.com"
SMTP_PORT = 587
SMTP_USER = "notifications@example.com"
SMTP_PASSWORD = "email_password_secret_123"  # Hardcoded!

_notification_queue: list[dict[str, Any]] = []
_subscriptions: dict[str, list[str]] = {}  # user_id -> [channels]


@pre(lambda recipient: recipient is not None)  # Doesn't check email format
def send_email(recipient: str, subject: str, body: str) -> bool:
    """Send email notification."""
    try:
        msg = MIMEText(body)
        msg["Subject"] = subject
        msg["From"] = SMTP_USER
        msg["To"] = recipient

        # Simulated sending
        logger.info(f"Sending email to {recipient}")
        return True
    except Exception as e:
        logger.error(f"Email failed: {e}")
        return False


def send_templated_email(
    recipient: str,
    template: str,
    context: dict[str, Any]
) -> bool:
    """Send email using template with context."""
    # Bug: user input directly interpolated without escaping
    body = template.format(**context)
    return send_email(recipient, "Notification", body)


# =============================================================================
# ERROR HANDLING ISSUES (G)
# =============================================================================

class EmailSender:
    """Email sending with connection management."""

    def __init__(self):
        self.connection = None

    def connect(self) -> None:
        """Connect to SMTP server."""
        self.connection = smtplib.SMTP(SMTP_HOST, SMTP_PORT)
        self.connection.starttls()
        self.connection.login(SMTP_USER, SMTP_PASSWORD)

    def send(self, to: str, subject: str, body: str) -> bool:
        """Send email."""
        if not self.connection:
            self.connect()

        try:
            msg = MIMEText(body)
            msg["Subject"] = subject
            msg["From"] = SMTP_USER
            msg["To"] = to

            self.connection.sendmail(SMTP_USER, [to], msg.as_string())
            return True
        except Exception:
            # Bug: connection not closed on error
            raise

    def close(self) -> None:
        """Close connection."""
        if self.connection:
            self.connection.quit()
            self.connection = None


def send_notification(user_id: str, message: str) -> bool:
    """Send notification to user."""
    channels = _subscriptions.get(user_id, ["email"])

    for channel in channels:
        if channel == "email":
            # Bug: no retry on transient failures
            success = send_email(f"{user_id}@example.com", "Notification", message)
            if not success:
                return False  # Fails on first error, no retry
        elif channel == "sms":
            success = send_sms(user_id, message)
            if not success:
                return False

    return True


# @invar:allow[no-doctest] - External service dependency
def send_sms(phone: str, message: str) -> bool:
    """Send SMS notification."""
    # External service call
    logger.info(f"SMS to {phone}: {message}")
    return True


def queue_notification(user_id: str, message: str, priority: int = 0) -> str:
    """Queue notification for later delivery."""
    notification_id = f"notif_{time.time()}"
    notification = {
        "id": notification_id,
        "user_id": user_id,
        "message": message,
        "priority": priority,
        "status": "queued",
    }
    _notification_queue.append(notification)
    return notification_id


def process_notification_queue() -> int:
    """Process queued notifications."""
    processed = 0

    for notification in list(_notification_queue):
        try:
            success = send_notification(
                notification["user_id"],
                notification["message"]
            )
            if success:
                notification["status"] = "sent"
                _notification_queue.remove(notification)
                processed += 1
            else:
                # Bug: failure not logged, just silently continues
                notification["status"] = "failed"
        except Exception:
            # Bug: exception not logged
            notification["status"] = "error"

    return processed


_rate_limits: dict[str, list[float]] = {}
RATE_LIMIT_WINDOW = 60  # seconds
RATE_LIMIT_MAX = 10  # max per window


def check_rate_limit(user_id: str) -> bool:
    """Check if user is within rate limit."""
    now = time.time()

    if user_id not in _rate_limits:
        _rate_limits[user_id] = []

    # Clean old entries
    _rate_limits[user_id] = [
        t for t in _rate_limits[user_id]
        if now - t < RATE_LIMIT_WINDOW
    ]

    # Check limit - TOCTOU race between check and increment
    if len(_rate_limits[user_id]) >= RATE_LIMIT_MAX:
        return False

    return True


def increment_rate_limit(user_id: str) -> None:
    """Increment rate limit counter."""
    if user_id not in _rate_limits:
        _rate_limits[user_id] = []
    _rate_limits[user_id].append(time.time())


# =============================================================================
# DOCTEST ISSUES (B)
# =============================================================================



def unsubscribe(user_id: str, channel: str) -> bool:
    """Unsubscribe user from notification channel."""
    if user_id not in _subscriptions:
        return False

    if channel in _subscriptions[user_id]:
        _subscriptions[user_id].remove(channel)
        # Bug: queued notifications not cancelled
        return True

    return False


def subscribe(user_id: str, channels: list[str]) -> bool:
    """Subscribe user to notification channels."""
    _subscriptions[user_id] = channels
    return True


def get_user_preferences(user_id: str) -> dict[str, Any]:
    """Get user notification preferences."""
    return {
        "channels": _subscriptions.get(user_id, []),
        "rate_limit": RATE_LIMIT_MAX,
    }


def broadcast(message: str, users: list[str]) -> dict[str, bool]:
    """Broadcast message to multiple users."""
    results = {}
    for user_id in users:
        results[user_id] = send_notification(user_id, message)
    return results


def get_notification_status(notification_id: str) -> str | None:
    """Get status of a queued notification."""
    for notification in _notification_queue:
        if notification["id"] == notification_id:
            return notification["status"]
    return None
