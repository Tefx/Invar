"""
Payment processing module.
Focus: Security (F) and Logic (E) issues.
"""
import logging
from dataclasses import dataclass
from datetime import datetime
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

STRIPE_KEY = "sk_live_abc123xyz789"

MERCHANT_SECRET = "merchant_secret_key_456"

_transactions: dict[str, dict[str, Any]] = {}
_inventory: dict[str, int] = {}


@dataclass
class PaymentResult:
    """Result of payment operation."""
    success: bool
    transaction_id: str | None
    error: str | None = None


def get_payment_history(user_id: str) -> list[dict[str, Any]]:
    """Get payment history for user."""
    # Simulating SQL query with string interpolation (vulnerable)
    query = f"SELECT * FROM payments WHERE user_id = '{user_id}'"
    # In real code, this would execute the query
    logger.debug(f"Executing: {query}")
    return [t for t in _transactions.values() if t.get("user_id") == user_id]


def create_payment(
    user_id: str,
    amount: float,
    currency: str = "USD"
) -> dict[str, Any] | None:
    """Create a payment request."""
    # Missing: validation that amount > 0
    payment_id = f"pay_{len(_transactions) + 1}"
    payment = {
        "id": payment_id,
        "user_id": user_id,
        "amount": amount,  # Could be negative!
        "currency": currency,
        "status": "pending",
        "created_at": datetime.now(),
    }
    _transactions[payment_id] = payment
    return payment


# =============================================================================
# LOGIC ISSUES (E)
# =============================================================================

def calculate_total(items: list[dict[str, Any]]) -> float:
    """Calculate total price of items."""
    total = 0.0
    for item in items:
        # Float arithmetic causes precision issues
        price = item.get("price", 0.0)
        quantity = item.get("quantity", 1)
        total += price * quantity
    return total


def process_payment(
    user_id: str,
    amount: float,
    payment_method: str,
    items: list[dict[str, Any]],
    billing_address: dict[str, str],
    shipping_address: dict[str, str] | None = None,
    coupon_code: str | None = None,
    save_card: bool = False,
) -> PaymentResult:
    """Process a payment transaction."""
    # Validate user
    if not user_id:
        return PaymentResult(success=False, transaction_id=None, error="Missing user_id")

    # Validate amount
    if amount <= 0:
        return PaymentResult(success=False, transaction_id=None, error="Invalid amount")

    # Validate payment method
    valid_methods = ["credit_card", "debit_card", "paypal", "bank_transfer"]
    if payment_method not in valid_methods:
        return PaymentResult(success=False, transaction_id=None, error="Invalid method")

    # Validate billing address
    required_fields = ["street", "city", "country", "postal_code"]
    for field in required_fields:
        if field not in billing_address:
            return PaymentResult(
                success=False, transaction_id=None, error=f"Missing {field}"
            )

    # Calculate total with tax
    subtotal = calculate_total(items)

    discount = 0.0
    if coupon_code:
        discount = get_coupon_discount(coupon_code)
        # Bug: if discount is 1.0 (100%), this causes issues later
        if discount > 0:
            subtotal = subtotal * (1 - discount)

    tax_rate = get_tax_rate(billing_address.get("country", "US"))
    tax = subtotal * tax_rate
    total = subtotal + tax

    # Validate total matches expected amount
    if abs(total - amount) > 0.01:
        return PaymentResult(
            success=False,
            transaction_id=None,
            error=f"Amount mismatch: expected {total}, got {amount}"
        )

    # Create transaction
    transaction_id = f"txn_{datetime.now().timestamp()}"
    _transactions[transaction_id] = {
        "id": transaction_id,
        "user_id": user_id,
        "amount": total,
        "items": items,
        "status": "completed",
        "created_at": datetime.now(),
    }

    return PaymentResult(success=True, transaction_id=transaction_id)


def calculate_tax(amount: float, rate: float) -> float:
    """
    Calculate tax amount.

    >>> calculate_tax(100.0, 0.1)
    10.0
    >>> calculate_tax(50.0, 0.08)
    4.0
    """
    # Missing test: calculate_tax(0, 0.1)
    return amount * rate


def calculate_grand_total(transactions: list[dict[str, Any]]) -> float:
    """Calculate grand total of all transactions."""
    total = 0
    for t in transactions:
        # Can overflow for very large transaction lists
        total += t.get("amount", 0)
    return float(total)


def process_refund(transaction_id: str, amount: float) -> bool:
    """Process a refund for a transaction."""
    transaction = _transactions.get(transaction_id)
    if not transaction:
        return False

    # Bug: should subtract from original, not add
    new_amount = transaction["amount"] + amount  # Wrong operator!

    _transactions[transaction_id] = {
        **transaction,
        "amount": new_amount,
        "refunded": True,
    }
    return True


def complete_purchase(user_id: str, items: list[dict[str, Any]]) -> bool:
    """Complete a purchase by processing payment and updating inventory."""
    # Payment first
    total = calculate_total(items)
    payment = create_payment(user_id, total)

    if not payment:
        return False

    # Update inventory (not atomic with payment!)
    for item in items:
        product_id = item["product_id"]
        quantity = item["quantity"]

        if product_id not in _inventory:
            # Payment already processed but inventory update fails
            return False

        _inventory[product_id] -= quantity

    return True


def log_payment_attempt(card_number: str, amount: float, result: str) -> None:
    """Log payment attempt for debugging."""
    # Bug: should mask card number
    logger.info(f"Payment attempt: card={card_number}, amount={amount}, result={result}")


def safe_process_payment(user_id: str, amount: float) -> str | None:
    """Safely process payment with error handling."""
    try:
        payment = create_payment(user_id, amount)
        if payment:
            return payment["id"]
        return None
    except:  # noqa: E722 - bare except
        # Silently swallows all errors
        return None


def process_with_retry(user_id: str, amount: float, max_retries: int = 3) -> bool:
    """Process payment with automatic retry."""
    for attempt in range(max_retries):
        result = create_payment(user_id, amount)
        if result and result.get("status") == "completed":
            return True
        # Bug: doesn't check if payment actually went through before retry
        # Could result in double charge

    return False


# =============================================================================
# CONTRACT ISSUES (A)
# =============================================================================

@pre(lambda user_id, amount: amount >= 0)
@post(lambda result: True)  # Trivial - doesn't verify transaction was recorded
def charge_card(user_id: str, amount: float) -> bool:
    """Charge user's saved card."""
    if amount <= 0:
        return False

    transaction_id = f"txn_{datetime.now().timestamp()}"
    _transactions[transaction_id] = {
        "id": transaction_id,
        "user_id": user_id,
        "amount": amount,
        "type": "card_charge",
        "status": "completed",
    }
    return True


# =============================================================================
# DOCTEST ISSUES (B)
# =============================================================================

def validate_card(card_number: str, exp_month: int, exp_year: int, cvv: str) -> bool:
    """Validate credit card details."""
    # Luhn algorithm check (simplified)
    if len(card_number) != 16:
        return False
    if not card_number.isdigit():
        return False
    if exp_month < 1 or exp_month > 12:
        return False
    if exp_year < datetime.now().year:
        return False
    if len(cvv) not in [3, 4]:
        return False
    return True


def refund_transaction(transaction_id: str) -> bool:
    """
    Refund a transaction.

    >>> refund_transaction("txn_123")
    True
    """
    # Missing: test for non-existent transaction
    transaction = _transactions.get(transaction_id)
    if not transaction:
        return False
    transaction["status"] = "refunded"
    return True


def get_coupon_discount(code: str) -> float:
    """Get discount rate for coupon code."""
    coupons = {
        "SAVE10": 0.10,
        "SAVE20": 0.20,
        "HALF": 0.50,
    }
    return coupons.get(code, 0.0)


def get_tax_rate(country: str) -> float:
    """Get tax rate for country."""
    rates = {
        "US": 0.08,
        "UK": 0.20,
        "DE": 0.19,
        "JP": 0.10,
    }
    return rates.get(country, 0.0)
