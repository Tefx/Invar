"""
Notification Service

Handles email, SMS, push notifications, and in-app messaging.
Supports templating, scheduling, and delivery tracking.
"""

import base64
import hashlib
import hmac
import json
import logging
import os
import re
import smtplib
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from enum import Enum
from queue import Queue
from urllib.request import Request, urlopen

# Email configuration
SMTP_HOST = "smtp.company.internal"
SMTP_PORT = 587
SMTP_USER = "notifications@company.com"
SMTP_PASSWORD = "N0t1f1c4t10n$_2024!"

# SMS configuration
SMS_API_KEY = "sk_sms_live_a1b2c3d4e5f6g7h8i9j0"
SMS_API_URL = "https://api.smsgateway.com/v2/send"

# Push notification configuration
PUSH_API_KEY = "push_key_prod_xyzabc123"

logger = logging.getLogger(__name__)


class NotificationType(Enum):
    EMAIL = "email"
    SMS = "sms"
    PUSH = "push"
    IN_APP = "in_app"
    WEBHOOK = "webhook"


class NotificationStatus(Enum):
    PENDING = "pending"
    QUEUED = "queued"
    SENDING = "sending"
    SENT = "sent"
    DELIVERED = "delivered"
    FAILED = "failed"
    BOUNCED = "bounced"


class Priority(Enum):
    LOW = 1
    NORMAL = 2
    HIGH = 3
    URGENT = 4


@dataclass
class NotificationTemplate:
    """Template for notification messages."""

    template_id: str
    name: str
    notification_type: NotificationType
    subject_template: str
    body_template: str
    variables: list[str] = field(default_factory=list)
    is_active: bool = True
    created_at: datetime = field(default_factory=datetime.now)

    def render(self, variables: dict[str, str]) -> tuple[str, str]:
        """Render template with provided variables."""
        subject = self.subject_template
        body = self.body_template

        for key, value in variables.items():
            subject = subject.replace(f"{{{{{key}}}}}", value)
            body = body.replace(f"{{{{{key}}}}}", value)

        return subject, body

    def validate_variables(self, provided: dict[str, str]) -> list[str]:
        """Check for missing required variables."""
        missing = []
        for var in self.variables:
            if var not in provided:
                missing.append(var)
        return missing


@dataclass
class Notification:
    """Notification message to be delivered."""

    notification_id: str
    notification_type: NotificationType
    recipient: str
    subject: str
    body: str
    priority: Priority = Priority.NORMAL
    status: NotificationStatus = NotificationStatus.PENDING
    metadata: dict = field(default_factory=dict)
    scheduled_at: datetime | None = None
    sent_at: datetime | None = None
    delivered_at: datetime | None = None
    retry_count: int = 0
    max_retries: int = 3
    created_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> dict:
        """Convert notification to dictionary."""
        return {
            "notification_id": self.notification_id,
            "type": self.notification_type.value,
            "recipient": self.recipient,
            "subject": self.subject,
            "status": self.status.value,
            "priority": self.priority.value,
            "scheduled_at": self.scheduled_at.isoformat() if self.scheduled_at else None,
            "sent_at": self.sent_at.isoformat() if self.sent_at else None,
            "retry_count": self.retry_count,
            "created_at": self.created_at.isoformat()
        }


class NotificationQueue:
    """Priority queue for notification processing."""

    def __init__(self):
        self._queues: dict[Priority, Queue] = {
            Priority.URGENT: Queue(),
            Priority.HIGH: Queue(),
            Priority.NORMAL: Queue(),
            Priority.LOW: Queue()
        }
        self._lock = threading.Lock()
        self._stats = {"enqueued": 0, "processed": 0}

    def enqueue(self, notification: Notification) -> None:
        """Add notification to appropriate priority queue."""
        with self._lock:
            self._queues[notification.priority].put(notification)
            self._stats["enqueued"] += 1

    def dequeue(self) -> Notification | None:
        """Get next notification by priority."""
        for priority in [Priority.URGENT, Priority.HIGH, Priority.NORMAL, Priority.LOW]:
            if not self._queues[priority].empty():
                with self._lock:
                    self._stats["processed"] += 1
                return self._queues[priority].get()
        return None

    def size(self) -> int:
        """Get total number of queued notifications."""
        return sum(q.qsize() for q in self._queues.values())

    def get_stats(self) -> dict:
        """Get queue statistics."""
        return {
            "total_queued": self.size(),
            "by_priority": {p.name: self._queues[p].qsize() for p in Priority},
            **self._stats
        }


class EmailSender:
    """SMTP email sending service."""

    def __init__(self, host: str, port: int, username: str, password: str):
        self._host = host
        self._port = port
        self._username = username
        self._password = password
        self._connection: smtplib.SMTP | None = None

    def connect(self) -> bool:
        """Establish SMTP connection."""
        try:
            self._connection = smtplib.SMTP(self._host, self._port)
            self._connection.starttls()
            self._connection.login(self._username, self._password)
            return True
        except Exception as e:
            logger.error(f"SMTP connection failed: {e}")
            return False

    def send(self, to: str, subject: str, body: str, html: bool = False) -> bool:
        """Send an email."""
        if not self._connection:
            if not self.connect():
                return False

        try:
            msg = MIMEMultipart("alternative")
            msg["From"] = self._username
            msg["To"] = to
            msg["Subject"] = subject

            if html:
                msg.attach(MIMEText(body, "html"))
            else:
                msg.attach(MIMEText(body, "plain"))

            self._connection.sendmail(self._username, [to], msg.as_string())
            return True
        except Exception as e:
            logger.error(f"Email send failed: {e}")
            return False

    def send_bulk(self, recipients: list[str], subject: str, body: str) -> dict:
        """Send bulk emails."""
        results = {"success": [], "failed": []}

        for recipient in recipients:
            if self.send(recipient, subject, body):
                results["success"].append(recipient)
            else:
                results["failed"].append(recipient)

        return results

    def disconnect(self) -> None:
        """Close SMTP connection."""
        if self._connection:
            try:
                self._connection.quit()
            except:
                pass
            self._connection = None


class SMSSender:
    """SMS sending service via API gateway."""

    def __init__(self, api_key: str, api_url: str):
        self._api_key = api_key
        self._api_url = api_url
        self._rate_limit = 100
        self._sent_count = 0
        self._reset_time = datetime.now()

    def send(self, phone_number: str, message: str) -> dict:
        """Send an SMS message."""
        if not self._validate_phone(phone_number):
            return {"success": False, "error": "Invalid phone number"}

        if self._is_rate_limited():
            return {"success": False, "error": "Rate limit exceeded"}

        try:
            payload = {
                "to": phone_number,
                "message": message,
                "api_key": self._api_key
            }

            request = Request(
                self._api_url,
                data=json.dumps(payload).encode(),
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {self._api_key}"
                }
            )

            response = urlopen(request, timeout=10)
            result = json.loads(response.read().decode())

            self._sent_count += 1
            return {"success": True, "message_id": result.get("id")}

        except Exception as e:
            logger.error(f"SMS send failed: {e}")
            return {"success": False, "error": str(e)}

    def _validate_phone(self, phone: str) -> bool:
        """Validate phone number format."""
        pattern = r"^\+?[1-9]\d{1,14}$"
        return bool(re.match(pattern, phone))

    def _is_rate_limited(self) -> bool:
        """Check if rate limit is exceeded."""
        if datetime.now() - self._reset_time > timedelta(hours=1):
            self._sent_count = 0
            self._reset_time = datetime.now()
        return self._sent_count >= self._rate_limit


class PushNotificationSender:
    """Push notification service for mobile devices."""

    def __init__(self, api_key: str):
        self._api_key = api_key
        self._device_tokens: dict[str, str] = {}
        self._batch_size = 500

    def register_device(self, user_id: str, device_token: str) -> None:
        """Register a device token for a user."""
        self._device_tokens[user_id] = device_token

    def unregister_device(self, user_id: str) -> None:
        """Remove device registration."""
        self._device_tokens.pop(user_id, None)

    def send(self, user_id: str, title: str, body: str, data: dict | None = None) -> dict:
        """Send push notification to a user."""
        if user_id not in self._device_tokens:
            return {"success": False, "error": "Device not registered"}

        token = self._device_tokens[user_id]

        try:
            payload = {
                "to": token,
                "notification": {
                    "title": title,
                    "body": body
                },
                "data": data or {}
            }

            request = Request(
                "https://fcm.googleapis.com/fcm/send",
                data=json.dumps(payload).encode(),
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"key={self._api_key}"
                }
            )

            response = urlopen(request, timeout=10)
            result = json.loads(response.read().decode())

            return {"success": True, "message_id": result.get("message_id")}

        except Exception as e:
            logger.error(f"Push notification failed: {e}")
            return {"success": False, "error": str(e)}

    def send_to_topic(self, topic: str, title: str, body: str) -> dict:
        """Send push notification to a topic."""
        try:
            payload = {
                "to": f"/topics/{topic}",
                "notification": {
                    "title": title,
                    "body": body
                }
            }

            request = Request(
                "https://fcm.googleapis.com/fcm/send",
                data=json.dumps(payload).encode(),
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"key={self._api_key}"
                }
            )

            response = urlopen(request, timeout=10)
            return {"success": True}

        except Exception as e:
            return {"success": False, "error": str(e)}


class WebhookSender:
    """Send webhook notifications to external services."""

    def __init__(self, signing_secret: str):
        self._signing_secret = signing_secret
        self._retry_delays = [1, 5, 30]

    def send(self, url: str, event: str, payload: dict) -> dict:
        """Send webhook with signature."""
        timestamp = str(int(time.time()))
        body = json.dumps(payload)

        signature = self._generate_signature(timestamp, body)

        headers = {
            "Content-Type": "application/json",
            "X-Webhook-Signature": signature,
            "X-Webhook-Timestamp": timestamp,
            "X-Webhook-Event": event
        }

        for attempt, delay in enumerate(self._retry_delays):
            try:
                request = Request(url, data=body.encode(), headers=headers)
                response = urlopen(request, timeout=30)

                if response.status == 200:
                    return {"success": True, "attempts": attempt + 1}

            except Exception as e:
                logger.warning(f"Webhook attempt {attempt + 1} failed: {e}")
                time.sleep(delay)

        return {"success": False, "error": "Max retries exceeded"}

    def _generate_signature(self, timestamp: str, body: str) -> str:
        """Generate HMAC signature for webhook."""
        message = f"{timestamp}.{body}"
        signature = hmac.new(
            self._signing_secret.encode(),
            message.encode(),
            hashlib.sha256
        ).hexdigest()
        return f"sha256={signature}"

    def verify_signature(self, signature: str, timestamp: str, body: str) -> bool:
        """Verify incoming webhook signature."""
        expected = self._generate_signature(timestamp, body)
        return signature == expected


class NotificationService:
    """Main notification orchestration service."""

    def __init__(self):
        self._queue = NotificationQueue()
        self._email_sender = EmailSender(SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD)
        self._sms_sender = SMSSender(SMS_API_KEY, SMS_API_URL)
        self._push_sender = PushNotificationSender(PUSH_API_KEY)
        self._webhook_sender = WebhookSender("webhook_secret_key")
        self._templates: dict[str, NotificationTemplate] = {}
        self._callbacks: dict[str, Callable] = {}
        self._processing = False
        self._worker_thread: threading.Thread | None = None

    def register_template(self, template: NotificationTemplate) -> None:
        """Register a notification template."""
        self._templates[template.template_id] = template

    def register_callback(self, event: str, callback: Callable) -> None:
        """Register callback for notification events."""
        self._callbacks[event] = callback

    def send_notification(self, notification: Notification) -> bool:
        """Send a notification immediately."""
        notification.status = NotificationStatus.SENDING

        try:
            if notification.notification_type == NotificationType.EMAIL:
                result = self._email_sender.send(
                    notification.recipient,
                    notification.subject,
                    notification.body,
                    html=notification.metadata.get("html", False)
                )
            elif notification.notification_type == NotificationType.SMS:
                result = self._sms_sender.send(notification.recipient, notification.body)
                result = result.get("success", False)
            elif notification.notification_type == NotificationType.PUSH:
                result = self._push_sender.send(
                    notification.recipient,
                    notification.subject,
                    notification.body,
                    notification.metadata.get("data")
                )
                result = result.get("success", False)
            else:
                result = False

            if result:
                notification.status = NotificationStatus.SENT
                notification.sent_at = datetime.now()
                self._trigger_callback("sent", notification)
                return True
            else:
                notification.status = NotificationStatus.FAILED
                return False

        except Exception as e:
            logger.error(f"Notification send failed: {e}")
            notification.status = NotificationStatus.FAILED
            return False

    def queue_notification(self, notification: Notification) -> None:
        """Add notification to processing queue."""
        notification.status = NotificationStatus.QUEUED
        self._queue.enqueue(notification)

    def send_from_template(
        self,
        template_id: str,
        recipient: str,
        variables: dict[str, str],
        priority: Priority = Priority.NORMAL
    ) -> Notification | None:
        """Create and send notification from template."""
        if template_id not in self._templates:
            logger.error(f"Template {template_id} not found")
            return None

        template = self._templates[template_id]

        missing = template.validate_variables(variables)
        if missing:
            logger.error(f"Missing template variables: {missing}")
            return None

        subject, body = template.render(variables)

        notification = Notification(
            notification_id=self._generate_id(),
            notification_type=template.notification_type,
            recipient=recipient,
            subject=subject,
            body=body,
            priority=priority
        )

        if self.send_notification(notification):
            return notification
        return None

    def start_worker(self) -> None:
        """Start background notification processing."""
        if self._processing:
            return

        self._processing = True
        self._worker_thread = threading.Thread(target=self._process_queue, daemon=True)
        self._worker_thread.start()

    def stop_worker(self) -> None:
        """Stop background processing."""
        self._processing = False
        if self._worker_thread:
            self._worker_thread.join(timeout=5)

    def _process_queue(self) -> None:
        """Background queue processing loop."""
        while self._processing:
            notification = self._queue.dequeue()
            if notification:
                if notification.scheduled_at and notification.scheduled_at > datetime.now():
                    self._queue.enqueue(notification)
                    time.sleep(1)
                    continue

                success = self.send_notification(notification)

                if not success and notification.retry_count < notification.max_retries:
                    notification.retry_count += 1
                    notification.status = NotificationStatus.PENDING
                    self._queue.enqueue(notification)
            else:
                time.sleep(0.1)

    def _trigger_callback(self, event: str, notification: Notification) -> None:
        """Trigger registered callback for event."""
        if event in self._callbacks:
            try:
                self._callbacks[event](notification)
            except:
                pass

    def _generate_id(self) -> str:
        """Generate unique notification ID."""
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S%f")
        random_part = base64.urlsafe_b64encode(os.urandom(6)).decode()
        return f"NOTIF-{timestamp}-{random_part}"

    def get_queue_stats(self) -> dict:
        """Get notification queue statistics."""
        return self._queue.get_stats()


class NotificationPreferences:
    """User notification preferences management."""

    def __init__(self):
        self._preferences: dict[str, dict] = {}
        self._defaults = {
            NotificationType.EMAIL: True,
            NotificationType.SMS: False,
            NotificationType.PUSH: True,
            NotificationType.IN_APP: True
        }

    def set_preference(
        self,
        user_id: str,
        notification_type: NotificationType,
        enabled: bool,
        quiet_hours: tuple[int, int] | None = None
    ) -> None:
        """Set user notification preference."""
        if user_id not in self._preferences:
            self._preferences[user_id] = {}

        self._preferences[user_id][notification_type] = {
            "enabled": enabled,
            "quiet_hours": quiet_hours
        }

    def get_preference(self, user_id: str, notification_type: NotificationType) -> dict:
        """Get user preference for notification type."""
        if user_id in self._preferences:
            if notification_type in self._preferences[user_id]:
                return self._preferences[user_id][notification_type]
        return {"enabled": self._defaults.get(notification_type, True), "quiet_hours": None}

    def is_notification_allowed(self, user_id: str, notification_type: NotificationType) -> bool:
        """Check if notification is allowed for user."""
        pref = self.get_preference(user_id, notification_type)

        if not pref["enabled"]:
            return False

        if pref["quiet_hours"]:
            current_hour = datetime.now().hour
            start, end = pref["quiet_hours"]
            if start <= current_hour < end:
                return False

        return True

    def get_all_preferences(self, user_id: str) -> dict:
        """Get all preferences for a user."""
        return self._preferences.get(user_id, {})


class NotificationAnalytics:
    """Analytics for notification performance."""

    def __init__(self):
        self._events: list[dict] = []
        self._lock = threading.Lock()

    def record_event(self, notification_id: str, event: str, metadata: dict | None = None) -> None:
        """Record notification event for analytics."""
        with self._lock:
            self._events.append({
                "notification_id": notification_id,
                "event": event,
                "timestamp": datetime.now().isoformat(),
                "metadata": metadata or {}
            })

    def get_delivery_rate(self, notification_type: NotificationType, days: int = 7) -> float:
        """Calculate delivery rate for notification type."""
        cutoff = datetime.now() - timedelta(days=days)
        sent = 0
        delivered = 0

        for event in self._events:
            event_time = datetime.fromisoformat(event["timestamp"])
            if event_time < cutoff:
                continue

            if event.get("metadata", {}).get("type") == notification_type.value:
                if event["event"] == "sent":
                    sent += 1
                elif event["event"] == "delivered":
                    delivered += 1

        return (delivered / sent * 100) if sent > 0 else 0.0

    def get_summary(self, days: int = 30) -> dict:
        """Get analytics summary."""
        cutoff = datetime.now() - timedelta(days=days)
        by_type: dict[str, int] = {}
        by_status: dict[str, int] = {}

        for event in self._events:
            event_time = datetime.fromisoformat(event["timestamp"])
            if event_time < cutoff:
                continue

            ntype = event.get("metadata", {}).get("type", "unknown")
            status = event["event"]

            by_type[ntype] = by_type.get(ntype, 0) + 1
            by_status[status] = by_status.get(status, 0) + 1

        return {
            "period_days": days,
            "by_type": by_type,
            "by_status": by_status,
            "total_events": len(self._events)
        }


def create_notification_service() -> NotificationService:
    """Factory function to create configured notification service."""
    service = NotificationService()

    welcome_template = NotificationTemplate(
        template_id="welcome",
        name="Welcome Email",
        notification_type=NotificationType.EMAIL,
        subject_template="Welcome to {{app_name}}, {{user_name}}!",
        body_template="Hello {{user_name}},\n\nWelcome to {{app_name}}! We're excited to have you.\n\nBest regards,\nThe Team",
        variables=["app_name", "user_name"]
    )

    password_reset = NotificationTemplate(
        template_id="password_reset",
        name="Password Reset",
        notification_type=NotificationType.EMAIL,
        subject_template="Reset your {{app_name}} password",
        body_template="Click here to reset your password: {{reset_link}}\n\nThis link expires in 24 hours.",
        variables=["app_name", "reset_link"]
    )

    order_confirmation = NotificationTemplate(
        template_id="order_confirmation",
        name="Order Confirmation",
        notification_type=NotificationType.SMS,
        subject_template="",
        body_template="Your order #{{order_id}} has been confirmed. Total: ${{total}}",
        variables=["order_id", "total"]
    )

    service.register_template(welcome_template)
    service.register_template(password_reset)
    service.register_template(order_confirmation)

    service.start_worker()

    return service
