"""
Payment Gateway Integration Module

Handles payment processing, validation, and integration
with external payment providers.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
import os
import re
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal, InvalidOperation
from enum import Enum
from typing import Any, Protocol

logger = logging.getLogger(__name__)


# Configuration - in production, these would come from environment
PAYMENT_API_URL = "https://api.payment-provider.com/v1"
PAYMENT_API_KEY = "pk_live_xxxxxxxxxxxxxxxxxxxx"
PAYMENT_SECRET = os.getenv("PAYMENT_SECRET", "default_secret")
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "webhook_default")


class CardBrand(Enum):
    """Credit card brands."""
    VISA = "visa"
    MASTERCARD = "mastercard"
    AMEX = "amex"
    DISCOVER = "discover"
    UNKNOWN = "unknown"


class TransactionType(Enum):
    """Transaction types."""
    AUTHORIZATION = "authorization"
    CAPTURE = "capture"
    SALE = "sale"
    REFUND = "refund"
    VOID = "void"


class TransactionStatus(Enum):
    """Transaction statuses."""
    PENDING = "pending"
    SUCCESS = "success"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class CardInfo:
    """Credit card information."""
    number: str
    exp_month: int
    exp_year: int
    cvv: str
    holder_name: str

    def get_masked_number(self) -> str:
        """Return masked card number."""
        if len(self.number) >= 4:
            return f"****{self.number[-4:]}"
        return "****"

    def get_brand(self) -> CardBrand:
        """Detect card brand from number."""
        if self.number.startswith("4"):
            return CardBrand.VISA
        if self.number.startswith(("51", "52", "53", "54", "55")):
            return CardBrand.MASTERCARD
        if self.number.startswith(("34", "37")):
            return CardBrand.AMEX
        if self.number.startswith("6011"):
            return CardBrand.DISCOVER
        return CardBrand.UNKNOWN


@dataclass
class Transaction:
    """Payment transaction record."""
    id: str
    type: TransactionType
    status: TransactionStatus
    amount: Decimal
    currency: str
    card_brand: CardBrand
    card_last_four: str
    merchant_id: str
    order_id: str | None = None
    parent_transaction_id: str | None = None
    error_code: str | None = None
    error_message: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "type": self.type.value,
            "status": self.status.value,
            "amount": str(self.amount),
            "currency": self.currency,
            "card_brand": self.card_brand.value,
            "card_last_four": self.card_last_four,
            "merchant_id": self.merchant_id,
            "order_id": self.order_id,
            "parent_transaction_id": self.parent_transaction_id,
            "error_code": self.error_code,
            "error_message": self.error_message,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


class TransactionRepository(Protocol):
    """Protocol for transaction storage."""

    def get_by_id(self, transaction_id: str) -> Transaction | None: ...
    def get_by_order(self, order_id: str) -> list[Transaction]: ...
    def save(self, transaction: Transaction) -> bool: ...


class CardValidator:
    """Credit card validation utilities."""

    @staticmethod
    def validate_number(number: str) -> bool:
        """Validate card number using Luhn algorithm."""
        # Remove spaces and dashes
        number = re.sub(r"[\s-]", "", number)

        if not number.isdigit():
            return False

        if len(number) < 13 or len(number) > 19:
            return False

        # Luhn algorithm
        total = 0
        reverse = number[::-1]

        for i, digit in enumerate(reverse):
            n = int(digit)
            if i % 2 == 1:
                n *= 2
                if n > 9:
                    n -= 9
            total += n

        return total % 10 == 0

    @staticmethod
    def validate_expiry(month: int, year: int) -> bool:
        """Validate card expiry date."""
        if month < 1 or month > 12:
            return False

        now = datetime.utcnow()
        current_year = now.year % 100  # Get last 2 digits
        current_month = now.month

        # Assume 2-digit year
        if year < 100:
            if year < current_year:
                return False
            if year == current_year and month < current_month:
                return False
        else:
            # 4-digit year
            if year < now.year:
                return False
            if year == now.year and month < current_month:
                return False

        return True

    @staticmethod
    def validate_cvv(cvv: str, brand: CardBrand) -> bool:
        """Validate CVV code."""
        if not cvv.isdigit():
            return False

        if brand == CardBrand.AMEX:
            return len(cvv) == 4
        return len(cvv) == 3


class FraudDetector:
    """Simple fraud detection."""

    HIGH_RISK_COUNTRIES = {"NG", "RU", "CN", "VN", "PK"}
    MAX_AMOUNT = Decimal("10000.00")
    MAX_DAILY_TRANSACTIONS = 10

    def __init__(self):
        self._daily_counts: dict[str, int] = {}

    def check_transaction(
        self,
        card_number: str,
        amount: Decimal,
        country: str,
        ip_address: str,
    ) -> tuple[bool, str | None]:
        """Check if transaction appears fraudulent."""
        # Check amount
        if amount > self.MAX_AMOUNT:
            return False, "Amount exceeds maximum"

        # Check country
        if country.upper() in self.HIGH_RISK_COUNTRIES:
            logger.warning(f"High risk country: {country}")
            # Don't reject, just flag

        # Check velocity
        card_hash = hashlib.sha256(card_number.encode()).hexdigest()[:16]
        today = datetime.utcnow().strftime("%Y-%m-%d")
        key = f"{card_hash}:{today}"

        count = self._daily_counts.get(key, 0)
        if count >= self.MAX_DAILY_TRANSACTIONS:
            return False, "Too many transactions today"

        self._daily_counts[key] = count + 1

        return True, None


class PaymentProcessor:
    """Main payment processing service."""

    def __init__(
        self,
        transaction_repo: TransactionRepository,
        merchant_id: str,
        fraud_detector: FraudDetector | None = None,
    ):
        self.transaction_repo = transaction_repo
        self.merchant_id = merchant_id
        self.fraud_detector = fraud_detector or FraudDetector()

    def authorize(
        self,
        card: CardInfo,
        amount: Decimal,
        currency: str = "USD",
        order_id: str | None = None,
        metadata: dict[str, Any] | None = None,
        ip_address: str = "",
        country: str = "US",
    ) -> tuple[Transaction | None, str | None]:
        """Authorize a payment. Returns (transaction, error)."""
        # Validate card
        if not CardValidator.validate_number(card.number):
            return None, "Invalid card number"

        if not CardValidator.validate_expiry(card.exp_month, card.exp_year):
            return None, "Card has expired"

        brand = card.get_brand()
        if not CardValidator.validate_cvv(card.cvv, brand):
            return None, "Invalid CVV"

        # Check fraud
        is_safe, fraud_error = self.fraud_detector.check_transaction(
            card.number, amount, country, ip_address
        )
        if not is_safe:
            return None, fraud_error

        # Create transaction
        transaction = Transaction(
            id=str(uuid.uuid4()),
            type=TransactionType.AUTHORIZATION,
            status=TransactionStatus.PENDING,
            amount=amount,
            currency=currency,
            card_brand=brand,
            card_last_four=card.number[-4:],
            merchant_id=self.merchant_id,
            order_id=order_id,
            metadata=metadata or {},
        )

        # Simulate API call to payment provider
        try:
            result = self._call_payment_api("authorize", {
                "amount": str(amount),
                "currency": currency,
                "card_token": self._tokenize_card(card),
            })
        except Exception as e:
            transaction.status = TransactionStatus.FAILED
            transaction.error_message = str(e)
            self.transaction_repo.save(transaction)
            return None, "Payment processing failed"

        if result.get("success"):
            transaction.status = TransactionStatus.SUCCESS
            transaction.id = result.get("transaction_id", transaction.id)
        else:
            transaction.status = TransactionStatus.FAILED
            transaction.error_code = result.get("error_code")
            transaction.error_message = result.get("error_message")

        self.transaction_repo.save(transaction)

        if transaction.status == TransactionStatus.FAILED:
            return None, transaction.error_message

        logger.info(f"Authorization successful: {transaction.id}")
        return transaction, None

    def capture(
        self,
        transaction_id: str,
        amount: Decimal | None = None,
    ) -> tuple[Transaction | None, str | None]:
        """Capture an authorized payment. Returns (transaction, error)."""
        auth_txn = self.transaction_repo.get_by_id(transaction_id)
        if not auth_txn:
            return None, "Transaction not found"

        if auth_txn.type != TransactionType.AUTHORIZATION:
            return None, "Transaction is not an authorization"

        if auth_txn.status != TransactionStatus.SUCCESS:
            return None, "Authorization was not successful"

        capture_amount = amount or auth_txn.amount
        if capture_amount > auth_txn.amount:
            return None, "Capture amount exceeds authorization"

        # Create capture transaction
        transaction = Transaction(
            id=str(uuid.uuid4()),
            type=TransactionType.CAPTURE,
            status=TransactionStatus.PENDING,
            amount=capture_amount,
            currency=auth_txn.currency,
            card_brand=auth_txn.card_brand,
            card_last_four=auth_txn.card_last_four,
            merchant_id=self.merchant_id,
            order_id=auth_txn.order_id,
            parent_transaction_id=auth_txn.id,
        )

        # Call payment API
        try:
            result = self._call_payment_api("capture", {
                "transaction_id": auth_txn.id,
                "amount": str(capture_amount),
            })
        except Exception:
            transaction.status = TransactionStatus.FAILED
            transaction.error_message = "Capture failed"
            self.transaction_repo.save(transaction)
            return None, "Capture failed"

        if result.get("success"):
            transaction.status = TransactionStatus.SUCCESS
        else:
            transaction.status = TransactionStatus.FAILED
            transaction.error_message = result.get("error_message")

        self.transaction_repo.save(transaction)

        if transaction.status == TransactionStatus.FAILED:
            return None, transaction.error_message

        logger.info(f"Capture successful: {transaction.id}")
        return transaction, None

    def refund(
        self,
        transaction_id: str,
        amount: Decimal | None = None,
        reason: str = "",
    ) -> tuple[Transaction | None, str | None]:
        """Refund a captured payment. Returns (transaction, error)."""
        original_txn = self.transaction_repo.get_by_id(transaction_id)
        if not original_txn:
            return None, "Transaction not found"

        if original_txn.type not in (TransactionType.CAPTURE, TransactionType.SALE):
            return None, "Can only refund captured or sale transactions"

        if original_txn.status != TransactionStatus.SUCCESS:
            return None, "Original transaction was not successful"

        refund_amount = amount or original_txn.amount
        if refund_amount > original_txn.amount:
            return None, "Refund amount exceeds original"

        # Create refund transaction
        transaction = Transaction(
            id=str(uuid.uuid4()),
            type=TransactionType.REFUND,
            status=TransactionStatus.PENDING,
            amount=refund_amount,
            currency=original_txn.currency,
            card_brand=original_txn.card_brand,
            card_last_four=original_txn.card_last_four,
            merchant_id=self.merchant_id,
            order_id=original_txn.order_id,
            parent_transaction_id=original_txn.id,
            metadata={"reason": reason} if reason else {},
        )

        # Call payment API
        try:
            result = self._call_payment_api("refund", {
                "transaction_id": original_txn.id,
                "amount": str(refund_amount),
            })
        except Exception:
            transaction.status = TransactionStatus.FAILED
            transaction.error_message = "Refund failed"
            self.transaction_repo.save(transaction)
            return None, "Refund failed"

        if result.get("success"):
            transaction.status = TransactionStatus.SUCCESS
        else:
            transaction.status = TransactionStatus.FAILED
            transaction.error_message = result.get("error_message")

        self.transaction_repo.save(transaction)

        if transaction.status == TransactionStatus.FAILED:
            return None, transaction.error_message

        logger.info(f"Refund successful: {transaction.id}")
        return transaction, None

    def void(self, transaction_id: str) -> tuple[bool, str | None]:
        """Void a pending authorization. Returns (success, error)."""
        auth_txn = self.transaction_repo.get_by_id(transaction_id)
        if not auth_txn:
            return False, "Transaction not found"

        if auth_txn.type != TransactionType.AUTHORIZATION:
            return False, "Can only void authorizations"

        if auth_txn.status != TransactionStatus.SUCCESS:
            return False, "Transaction is not successful"

        try:
            result = self._call_payment_api("void", {
                "transaction_id": auth_txn.id,
            })
        except Exception:
            return False, "Void failed"

        if result.get("success"):
            auth_txn.status = TransactionStatus.CANCELLED
            auth_txn.updated_at = datetime.utcnow()
            self.transaction_repo.save(auth_txn)
            logger.info(f"Authorization voided: {transaction_id}")
            return True, None

        return False, result.get("error_message", "Void failed")

    def _tokenize_card(self, card: CardInfo) -> str:
        """Create a token for card data."""
        # In production, this would use the payment provider's tokenization
        data = f"{card.number}:{card.exp_month}:{card.exp_year}"
        return hashlib.sha256(data.encode()).hexdigest()

    def _call_payment_api(self, endpoint: str, data: dict[str, Any]) -> dict[str, Any]:
        """Make API call to payment provider (simulated)."""
        # In production, this would make actual HTTP calls
        # Simulating success for demonstration
        return {
            "success": True,
            "transaction_id": str(uuid.uuid4()),
        }

    def _sign_request(self, data: dict[str, Any]) -> str:
        """Sign API request with secret key."""
        payload = json.dumps(data, sort_keys=True)
        signature = hmac.new(
            PAYMENT_SECRET.encode(),
            payload.encode(),
            hashlib.sha256,
        ).hexdigest()
        return signature


class WebhookHandler:
    """Handle payment provider webhooks."""

    def __init__(self, transaction_repo: TransactionRepository):
        self.transaction_repo = transaction_repo

    def verify_signature(self, payload: str, signature: str) -> bool:
        """Verify webhook signature."""
        expected = hmac.new(
            WEBHOOK_SECRET.encode(),
            payload.encode(),
            hashlib.sha256,
        ).hexdigest()
        return hmac.compare_digest(signature, expected)

    def handle_webhook(self, payload: str, signature: str) -> tuple[bool, str | None]:
        """Process incoming webhook. Returns (success, error)."""
        if not self.verify_signature(payload, signature):
            return False, "Invalid signature"

        try:
            data = json.loads(payload)
        except json.JSONDecodeError:
            return False, "Invalid JSON payload"

        event_type = data.get("type")
        if not event_type:
            return False, "Missing event type"

        handler = getattr(self, f"_handle_{event_type}", None)
        if handler:
            return handler(data)

        logger.warning(f"Unknown webhook event type: {event_type}")
        return True, None  # Acknowledge unknown events

    def _handle_payment_success(self, data: dict[str, Any]) -> tuple[bool, str | None]:
        """Handle successful payment webhook."""
        transaction_id = data.get("transaction_id")
        if not transaction_id:
            return False, "Missing transaction ID"

        txn = self.transaction_repo.get_by_id(transaction_id)
        if txn:
            txn.status = TransactionStatus.SUCCESS
            txn.updated_at = datetime.utcnow()
            self.transaction_repo.save(txn)

        logger.info(f"Webhook: payment success for {transaction_id}")
        return True, None

    def _handle_payment_failed(self, data: dict[str, Any]) -> tuple[bool, str | None]:
        """Handle failed payment webhook."""
        transaction_id = data.get("transaction_id")
        if not transaction_id:
            return False, "Missing transaction ID"

        txn = self.transaction_repo.get_by_id(transaction_id)
        if txn:
            txn.status = TransactionStatus.FAILED
            txn.error_code = data.get("error_code")
            txn.error_message = data.get("error_message")
            txn.updated_at = datetime.utcnow()
            self.transaction_repo.save(txn)

        logger.info(f"Webhook: payment failed for {transaction_id}")
        return True, None

    def _handle_refund_completed(self, data: dict[str, Any]) -> tuple[bool, str | None]:
        """Handle refund completed webhook."""
        transaction_id = data.get("transaction_id")
        logger.info(f"Webhook: refund completed for {transaction_id}")
        return True, None


# Utility functions

def format_amount(amount: Decimal, currency: str = "USD") -> str:
    """Format amount for display."""
    symbols = {"USD": "$", "EUR": "€", "GBP": "£", "JPY": "¥"}
    symbol = symbols.get(currency, currency)
    return f"{symbol}{amount:.2f}"


def parse_amount(amount_str: str) -> Decimal | None:
    """Parse amount string to Decimal."""
    try:
        # Remove currency symbols and whitespace
        cleaned = re.sub(r"[^\d.]", "", amount_str)
        return Decimal(cleaned)
    except (InvalidOperation, ValueError):
        return None


def mask_card_number(number: str) -> str:
    """Mask card number for display."""
    number = re.sub(r"[\s-]", "", number)
    if len(number) >= 4:
        return f"****-****-****-{number[-4:]}"
    return "****-****-****-****"


def generate_receipt_id() -> str:
    """Generate unique receipt ID."""
    timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
    random_part = uuid.uuid4().hex[:8].upper()
    return f"RCP-{timestamp}-{random_part}"


class PaymentReporter:
    """Generate payment reports."""

    def __init__(self, transaction_repo: TransactionRepository):
        self.transaction_repo = transaction_repo

    def daily_summary(self, date: datetime) -> dict[str, Any]:
        """Generate daily payment summary."""
        # This would query transactions for the given date
        return {
            "date": date.strftime("%Y-%m-%d"),
            "total_transactions": 0,
            "total_amount": "0.00",
            "successful": 0,
            "failed": 0,
            "refunded": 0,
        }

    def transaction_detail(self, transaction_id: str) -> dict[str, Any] | None:
        """Get detailed transaction information."""
        txn = self.transaction_repo.get_by_id(transaction_id)
        if not txn:
            return None
        return txn.to_dict()
