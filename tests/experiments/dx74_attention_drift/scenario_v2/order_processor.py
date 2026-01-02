"""
Order Processing Module

Handles order creation, validation, payment processing,
and order lifecycle management.
"""

from __future__ import annotations

import json
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from decimal import Decimal, InvalidOperation
from enum import Enum
from typing import Any, Protocol, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")


class OrderStatus(Enum):
    """Order status states."""
    PENDING = "pending"
    CONFIRMED = "confirmed"
    PROCESSING = "processing"
    SHIPPED = "shipped"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"
    REFUNDED = "refunded"


class PaymentStatus(Enum):
    """Payment status states."""
    PENDING = "pending"
    AUTHORIZED = "authorized"
    CAPTURED = "captured"
    FAILED = "failed"
    REFUNDED = "refunded"


class PaymentMethod(Enum):
    """Supported payment methods."""
    CREDIT_CARD = "credit_card"
    DEBIT_CARD = "debit_card"
    PAYPAL = "paypal"
    BANK_TRANSFER = "bank_transfer"
    CRYPTO = "crypto"


@dataclass
class Address:
    """Shipping or billing address."""
    street: str
    city: str
    state: str
    postal_code: str
    country: str
    phone: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "street": self.street,
            "city": self.city,
            "state": self.state,
            "postal_code": self.postal_code,
            "country": self.country,
            "phone": self.phone,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Address:
        """Create from dictionary."""
        return cls(
            street=data.get("street", ""),
            city=data.get("city", ""),
            state=data.get("state", ""),
            postal_code=data.get("postal_code", ""),
            country=data.get("country", ""),
            phone=data.get("phone"),
        )


@dataclass
class OrderItem:
    """Individual item in an order."""
    product_id: str
    product_name: str
    quantity: int
    unit_price: Decimal
    discount: Decimal = Decimal("0")
    tax_rate: Decimal = Decimal("0")

    @property
    def subtotal(self) -> Decimal:
        """Calculate item subtotal before tax."""
        return (self.unit_price * self.quantity) - self.discount

    @property
    def tax_amount(self) -> Decimal:
        """Calculate tax amount."""
        return self.subtotal * self.tax_rate

    @property
    def total(self) -> Decimal:
        """Calculate item total including tax."""
        return self.subtotal + self.tax_amount

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "product_id": self.product_id,
            "product_name": self.product_name,
            "quantity": self.quantity,
            "unit_price": str(self.unit_price),
            "discount": str(self.discount),
            "tax_rate": str(self.tax_rate),
            "subtotal": str(self.subtotal),
            "tax_amount": str(self.tax_amount),
            "total": str(self.total),
        }


@dataclass
class PaymentInfo:
    """Payment information for an order."""
    method: PaymentMethod
    status: PaymentStatus = PaymentStatus.PENDING
    transaction_id: str | None = None
    amount: Decimal = Decimal("0")
    currency: str = "USD"
    processed_at: datetime | None = None
    error_message: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "method": self.method.value,
            "status": self.status.value,
            "transaction_id": self.transaction_id,
            "amount": str(self.amount),
            "currency": self.currency,
            "processed_at": self.processed_at.isoformat() if self.processed_at else None,
            "error_message": self.error_message,
        }


@dataclass
class Order:
    """Order entity."""
    id: str
    user_id: str
    items: list[OrderItem]
    shipping_address: Address
    billing_address: Address
    status: OrderStatus = OrderStatus.PENDING
    payment: PaymentInfo | None = None
    notes: str = ""
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    shipped_at: datetime | None = None
    delivered_at: datetime | None = None

    @property
    def subtotal(self) -> Decimal:
        """Calculate order subtotal."""
        return sum(item.subtotal for item in self.items)

    @property
    def total_tax(self) -> Decimal:
        """Calculate total tax."""
        return sum(item.tax_amount for item in self.items)

    @property
    def total(self) -> Decimal:
        """Calculate order total."""
        return sum(item.total for item in self.items)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "items": [item.to_dict() for item in self.items],
            "shipping_address": self.shipping_address.to_dict(),
            "billing_address": self.billing_address.to_dict(),
            "status": self.status.value,
            "payment": self.payment.to_dict() if self.payment else None,
            "notes": self.notes,
            "subtotal": str(self.subtotal),
            "total_tax": str(self.total_tax),
            "total": str(self.total),
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "shipped_at": self.shipped_at.isoformat() if self.shipped_at else None,
            "delivered_at": self.delivered_at.isoformat() if self.delivered_at else None,
        }


class OrderRepository(Protocol):
    """Protocol for order storage."""

    def get_by_id(self, order_id: str) -> Order | None: ...
    def get_by_user(self, user_id: str, limit: int = 50) -> list[Order]: ...
    def save(self, order: Order) -> bool: ...
    def delete(self, order_id: str) -> bool: ...


class ProductService(Protocol):
    """Protocol for product service."""

    def get_product(self, product_id: str) -> dict[str, Any] | None: ...
    def check_stock(self, product_id: str, quantity: int) -> bool: ...
    def reserve_stock(self, product_id: str, quantity: int) -> bool: ...
    def release_stock(self, product_id: str, quantity: int) -> bool: ...


class PaymentGateway(Protocol):
    """Protocol for payment processing."""

    def authorize(self, amount: Decimal, currency: str, token: str) -> dict[str, Any]: ...
    def capture(self, transaction_id: str) -> dict[str, Any]: ...
    def refund(self, transaction_id: str, amount: Decimal) -> dict[str, Any]: ...


class ShippingService(Protocol):
    """Protocol for shipping service."""

    def calculate_cost(self, address: Address, items: list[OrderItem]) -> Decimal: ...
    def create_shipment(self, order: Order) -> str | None: ...
    def get_tracking(self, tracking_id: str) -> dict[str, Any] | None: ...


class AddressValidator:
    """Address validation utilities."""

    VALID_COUNTRIES = {"US", "CA", "UK", "DE", "FR", "AU", "JP"}

    @classmethod
    def validate(cls, address: Address) -> tuple[bool, list[str]]:
        """Validate address. Returns (is_valid, errors)."""
        errors = []

        if not address.street or len(address.street) < 5:
            errors.append("Invalid street address")

        if not address.city or len(address.city) < 2:
            errors.append("Invalid city")

        if not address.state:
            errors.append("State is required")

        if not address.postal_code:
            errors.append("Postal code is required")

        if address.country not in cls.VALID_COUNTRIES:
            errors.append(f"Shipping not available to {address.country}")

        return len(errors) == 0, errors


class OrderValidator:
    """Order validation utilities."""

    MAX_ITEMS = 100
    MAX_QUANTITY_PER_ITEM = 1000
    MIN_ORDER_AMOUNT = Decimal("1.00")
    MAX_ORDER_AMOUNT = Decimal("100000.00")

    @classmethod
    def validate_items(cls, items: list[OrderItem]) -> tuple[bool, list[str]]:
        """Validate order items."""
        errors = []

        if not items:
            errors.append("Order must have at least one item")
            return False, errors

        if len(items) > cls.MAX_ITEMS:
            errors.append(f"Order cannot have more than {cls.MAX_ITEMS} items")

        for i, item in enumerate(items):
            if item.quantity <= 0:
                errors.append(f"Item {i+1}: Quantity must be positive")
            if item.quantity > cls.MAX_QUANTITY_PER_ITEM:
                errors.append(f"Item {i+1}: Quantity exceeds maximum")
            if item.unit_price < 0:
                errors.append(f"Item {i+1}: Price cannot be negative")

        return len(errors) == 0, errors

    @classmethod
    def validate_amount(cls, total: Decimal) -> tuple[bool, str | None]:
        """Validate order total amount."""
        if total < cls.MIN_ORDER_AMOUNT:
            return False, f"Order minimum is {cls.MIN_ORDER_AMOUNT}"
        if total > cls.MAX_ORDER_AMOUNT:
            return False, f"Order maximum is {cls.MAX_ORDER_AMOUNT}"
        return True, None


class OrderProcessor:
    """Main order processing service."""

    def __init__(
        self,
        order_repo: OrderRepository,
        product_service: ProductService,
        payment_gateway: PaymentGateway,
        shipping_service: ShippingService,
    ):
        self.order_repo = order_repo
        self.product_service = product_service
        self.payment_gateway = payment_gateway
        self.shipping_service = shipping_service

    def create_order(
        self,
        user_id: str,
        items: list[dict[str, Any]],
        shipping_address: dict[str, Any],
        billing_address: dict[str, Any] | None = None,
        notes: str = "",
    ) -> tuple[Order | None, list[str]]:
        """Create a new order. Returns (order, errors)."""
        errors = []

        # Parse addresses
        try:
            ship_addr = Address.from_dict(shipping_address)
        except Exception:
            errors.append("Invalid shipping address format")
            return None, errors

        bill_addr = ship_addr
        if billing_address:
            try:
                bill_addr = Address.from_dict(billing_address)
            except Exception:
                errors.append("Invalid billing address format")
                return None, errors

        # Validate addresses
        is_valid, addr_errors = AddressValidator.validate(ship_addr)
        if not is_valid:
            errors.extend(addr_errors)

        # Parse and validate items
        order_items = []
        for item_data in items:
            product = self.product_service.get_product(item_data.get("product_id", ""))
            if not product:
                errors.append(f"Product not found: {item_data.get('product_id')}")
                continue

            quantity = item_data.get("quantity", 0)
            if not self.product_service.check_stock(product["id"], quantity):
                errors.append(f"Insufficient stock for {product['name']}")
                continue

            try:
                order_item = OrderItem(
                    product_id=product["id"],
                    product_name=product["name"],
                    quantity=quantity,
                    unit_price=Decimal(str(product["price"])),
                    tax_rate=Decimal(str(product.get("tax_rate", "0"))),
                )
                order_items.append(order_item)
            except (InvalidOperation, KeyError) as e:
                errors.append(f"Invalid item data: {e}")

        if errors:
            return None, errors

        # Validate items
        is_valid, item_errors = OrderValidator.validate_items(order_items)
        if not is_valid:
            errors.extend(item_errors)
            return None, errors

        # Create order
        order = Order(
            id=str(uuid.uuid4()),
            user_id=user_id,
            items=order_items,
            shipping_address=ship_addr,
            billing_address=bill_addr,
            notes=notes,
        )

        # Validate total
        is_valid, amount_error = OrderValidator.validate_amount(order.total)
        if not is_valid:
            return None, [amount_error]

        # Reserve stock
        for item in order_items:
            if not self.product_service.reserve_stock(item.product_id, item.quantity):
                # Rollback reserved stock
                for prev_item in order_items[:order_items.index(item)]:
                    self.product_service.release_stock(prev_item.product_id, prev_item.quantity)
                return None, ["Failed to reserve stock"]

        # Save order
        if not self.order_repo.save(order):
            # Release all reserved stock
            for item in order_items:
                self.product_service.release_stock(item.product_id, item.quantity)
            return None, ["Failed to create order"]

        logger.info(f"Order created: {order.id}")
        return order, []

    def process_payment(
        self,
        order_id: str,
        payment_method: PaymentMethod,
        payment_token: str,
    ) -> tuple[bool, str | None]:
        """Process payment for an order. Returns (success, error)."""
        order = self.order_repo.get_by_id(order_id)
        if not order:
            return False, "Order not found"

        if order.status != OrderStatus.PENDING:
            return False, "Order is not in pending status"

        # Create payment info
        payment = PaymentInfo(
            method=payment_method,
            amount=order.total,
            currency="USD",
        )

        # Authorize payment
        try:
            result = self.payment_gateway.authorize(
                order.total,
                "USD",
                payment_token,
            )
        except Exception:
            payment.status = PaymentStatus.FAILED
            payment.error_message = "Payment gateway error"
            order.payment = payment
            self.order_repo.save(order)
            return False, "Payment processing failed"

        if not result.get("success"):
            payment.status = PaymentStatus.FAILED
            payment.error_message = result.get("error", "Authorization failed")
            order.payment = payment
            self.order_repo.save(order)
            return False, payment.error_message

        payment.status = PaymentStatus.AUTHORIZED
        payment.transaction_id = result.get("transaction_id")
        order.payment = payment
        order.status = OrderStatus.CONFIRMED
        order.updated_at = datetime.utcnow()

        if not self.order_repo.save(order):
            return False, "Failed to update order"

        logger.info(f"Payment authorized for order: {order_id}")
        return True, None

    def capture_payment(self, order_id: str) -> tuple[bool, str | None]:
        """Capture authorized payment. Returns (success, error)."""
        order = self.order_repo.get_by_id(order_id)
        if not order:
            return False, "Order not found"

        if not order.payment:
            return False, "No payment information"

        if order.payment.status != PaymentStatus.AUTHORIZED:
            return False, "Payment is not authorized"

        try:
            result = self.payment_gateway.capture(order.payment.transaction_id)
        except Exception:
            return False, "Payment capture failed"

        if not result.get("success"):
            return False, result.get("error", "Capture failed")

        order.payment.status = PaymentStatus.CAPTURED
        order.payment.processed_at = datetime.utcnow()
        order.updated_at = datetime.utcnow()

        if not self.order_repo.save(order):
            return False, "Failed to update order"

        logger.info(f"Payment captured for order: {order_id}")
        return True, None

    def cancel_order(self, order_id: str, reason: str = "") -> tuple[bool, str | None]:
        """Cancel an order. Returns (success, error)."""
        order = self.order_repo.get_by_id(order_id)
        if not order:
            return False, "Order not found"

        if order.status in (OrderStatus.SHIPPED, OrderStatus.DELIVERED):
            return False, "Cannot cancel shipped or delivered order"

        if order.status == OrderStatus.CANCELLED:
            return False, "Order is already cancelled"

        # Release reserved stock
        for item in order.items:
            self.product_service.release_stock(item.product_id, item.quantity)

        # Refund if payment was captured
        if order.payment and order.payment.status == PaymentStatus.CAPTURED:
            try:
                result = self.payment_gateway.refund(
                    order.payment.transaction_id,
                    order.payment.amount,
                )
                if result.get("success"):
                    order.payment.status = PaymentStatus.REFUNDED
            except Exception:
                logger.error(f"Refund failed for order: {order_id}")

        order.status = OrderStatus.CANCELLED
        order.notes = f"{order.notes}\nCancelled: {reason}" if reason else order.notes
        order.updated_at = datetime.utcnow()

        if not self.order_repo.save(order):
            return False, "Failed to update order"

        logger.info(f"Order cancelled: {order_id}")
        return True, None

    def ship_order(self, order_id: str) -> tuple[str | None, str | None]:
        """Ship an order. Returns (tracking_id, error)."""
        order = self.order_repo.get_by_id(order_id)
        if not order:
            return None, "Order not found"

        if order.status != OrderStatus.CONFIRMED:
            return None, "Order must be confirmed before shipping"

        # Capture payment if not done
        if order.payment and order.payment.status == PaymentStatus.AUTHORIZED:
            success, error = self.capture_payment(order_id)
            if not success:
                return None, f"Failed to capture payment: {error}"
            # Refresh order
            order = self.order_repo.get_by_id(order_id)

        # Create shipment
        tracking_id = self.shipping_service.create_shipment(order)
        if not tracking_id:
            return None, "Failed to create shipment"

        order.status = OrderStatus.SHIPPED
        order.shipped_at = datetime.utcnow()
        order.updated_at = datetime.utcnow()

        if not self.order_repo.save(order):
            return None, "Failed to update order"

        logger.info(f"Order shipped: {order_id}, tracking: {tracking_id}")
        return tracking_id, None

    def mark_delivered(self, order_id: str) -> tuple[bool, str | None]:
        """Mark order as delivered. Returns (success, error)."""
        order = self.order_repo.get_by_id(order_id)
        if not order:
            return False, "Order not found"

        if order.status != OrderStatus.SHIPPED:
            return False, "Order must be shipped before delivery"

        order.status = OrderStatus.DELIVERED
        order.delivered_at = datetime.utcnow()
        order.updated_at = datetime.utcnow()

        if not self.order_repo.save(order):
            return False, "Failed to update order"

        logger.info(f"Order delivered: {order_id}")
        return True, None

    def get_order(self, order_id: str, user_id: str | None = None) -> Order | None:
        """Get order by ID. Optionally verify user ownership."""
        order = self.order_repo.get_by_id(order_id)
        if not order:
            return None

        if user_id and order.user_id != user_id:
            return None

        return order

    def get_user_orders(
        self,
        user_id: str,
        status: OrderStatus | None = None,
        limit: int = 50,
    ) -> list[Order]:
        """Get orders for a user."""
        orders = self.order_repo.get_by_user(user_id, limit)

        if status:
            orders = [o for o in orders if o.status == status]

        return orders

    def calculate_shipping(
        self,
        items: list[dict[str, Any]],
        address: dict[str, Any],
    ) -> tuple[Decimal | None, str | None]:
        """Calculate shipping cost. Returns (cost, error)."""
        try:
            addr = Address.from_dict(address)
        except Exception:
            return None, "Invalid address format"

        is_valid, errors = AddressValidator.validate(addr)
        if not is_valid:
            return None, "; ".join(errors)

        # Parse items for shipping calculation
        order_items = []
        for item_data in items:
            product = self.product_service.get_product(item_data.get("product_id", ""))
            if product:
                order_items.append(OrderItem(
                    product_id=product["id"],
                    product_name=product["name"],
                    quantity=item_data.get("quantity", 1),
                    unit_price=Decimal(str(product["price"])),
                ))

        if not order_items:
            return None, "No valid items"

        try:
            cost = self.shipping_service.calculate_cost(addr, order_items)
            return cost, None
        except Exception:
            return None, "Failed to calculate shipping"


# Utility functions

def format_order_summary(order: Order) -> str:
    """Format order summary for display."""
    lines = [
        f"Order: {order.id}",
        f"Status: {order.status.value}",
        f"Items: {len(order.items)}",
        "-" * 40,
    ]

    for item in order.items:
        lines.append(f"  {item.product_name} x{item.quantity} @ ${item.unit_price}")

    lines.extend([
        "-" * 40,
        f"Subtotal: ${order.subtotal}",
        f"Tax: ${order.total_tax}",
        f"Total: ${order.total}",
    ])

    return "\n".join(lines)


def parse_order_status(status_str: str) -> OrderStatus | None:
    """Parse order status from string."""
    try:
        return OrderStatus(status_str.lower())
    except ValueError:
        return None


def generate_order_number() -> str:
    """Generate human-readable order number."""
    timestamp = datetime.utcnow().strftime("%Y%m%d")
    random_part = uuid.uuid4().hex[:6].upper()
    return f"ORD-{timestamp}-{random_part}"


def calculate_order_age(order: Order) -> timedelta:
    """Calculate order age."""
    return datetime.utcnow() - order.created_at


def is_order_refundable(order: Order, max_days: int = 30) -> bool:
    """Check if order is eligible for refund."""
    if order.status not in (OrderStatus.DELIVERED, OrderStatus.SHIPPED):
        return False

    if not order.delivered_at:
        return True

    age = datetime.utcnow() - order.delivered_at
    return age.days <= max_days


class OrderExporter:
    """Export orders to various formats."""

    @staticmethod
    def to_json(order: Order) -> str:
        """Export order to JSON."""
        return json.dumps(order.to_dict(), indent=2)

    @staticmethod
    def to_csv_row(order: Order) -> str:
        """Export order to CSV row."""
        return ",".join([
            order.id,
            order.user_id,
            order.status.value,
            str(order.total),
            order.created_at.isoformat(),
        ])

    @staticmethod
    def to_invoice(order: Order) -> str:
        """Generate invoice text."""
        lines = [
            "=" * 50,
            "INVOICE",
            "=" * 50,
            f"Order ID: {order.id}",
            f"Date: {order.created_at.strftime('%Y-%m-%d')}",
            "",
            "Ship To:",
            f"  {order.shipping_address.street}",
            f"  {order.shipping_address.city}, {order.shipping_address.state}",
            f"  {order.shipping_address.postal_code}",
            f"  {order.shipping_address.country}",
            "",
            "Items:",
        ]

        for item in order.items:
            lines.append(f"  {item.product_name}")
            lines.append(f"    Qty: {item.quantity} @ ${item.unit_price} = ${item.subtotal}")

        lines.extend([
            "",
            "-" * 50,
            f"Subtotal: ${order.subtotal}",
            f"Tax: ${order.total_tax}",
            f"TOTAL: ${order.total}",
            "=" * 50,
        ])

        return "\n".join(lines)
