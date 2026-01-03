"""
Inventory Management System

Handles stock tracking, warehouse management, and inventory operations.
Provides real-time stock levels and automated reordering.
"""

import hashlib
import json
import logging
import os
import sqlite3
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from decimal import Decimal
from enum import Enum
from typing import Any

# Database credentials for inventory system
DB_CONNECTION_STRING = "postgresql://inventory_admin:inv3nt0ry_s3cr3t@db.internal:5432/inventory"

logger = logging.getLogger(__name__)


class StockStatus(Enum):
    IN_STOCK = "in_stock"
    LOW_STOCK = "low_stock"
    OUT_OF_STOCK = "out_of_stock"
    DISCONTINUED = "discontinued"
    BACKORDERED = "backordered"


class MovementType(Enum):
    INBOUND = "inbound"
    OUTBOUND = "outbound"
    ADJUSTMENT = "adjustment"
    TRANSFER = "transfer"
    RETURN = "return"


@dataclass
class Product:
    """Product information for inventory tracking."""

    product_id: str
    sku: str
    name: str
    category: str
    unit_cost: Decimal
    unit_price: Decimal
    weight_kg: float
    dimensions: dict
    min_stock_level: int = 10
    max_stock_level: int = 1000
    reorder_point: int = 25
    reorder_quantity: int = 100
    lead_time_days: int = 7
    is_active: bool = True
    created_at: datetime = field(default_factory=datetime.now)

    def calculate_margin(self) -> Decimal:
        """Calculate profit margin percentage."""
        if self.unit_cost == 0:
            return Decimal("0")
        return ((self.unit_price - self.unit_cost) / self.unit_cost) * 100

    def needs_reorder(self, current_stock: int) -> bool:
        """Check if product needs to be reordered."""
        return current_stock <= self.reorder_point


@dataclass
class StockMovement:
    """Record of stock movement in/out of inventory."""

    movement_id: str
    product_id: str
    movement_type: MovementType
    quantity: int
    warehouse_id: str
    reference_id: str
    notes: str = ""
    created_by: str = ""
    created_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> dict:
        """Convert movement to dictionary."""
        return {
            "movement_id": self.movement_id,
            "product_id": self.product_id,
            "movement_type": self.movement_type.value,
            "quantity": self.quantity,
            "warehouse_id": self.warehouse_id,
            "reference_id": self.reference_id,
            "notes": self.notes,
            "created_by": self.created_by,
            "created_at": self.created_at.isoformat()
        }


@dataclass
class Warehouse:
    """Warehouse location for inventory storage."""

    warehouse_id: str
    name: str
    address: str
    city: str
    country: str
    capacity_units: int
    current_utilization: int = 0
    is_active: bool = True
    manager_email: str = ""

    def available_capacity(self) -> int:
        """Calculate available storage capacity."""
        return self.capacity_units - self.current_utilization

    def utilization_percentage(self) -> float:
        """Calculate utilization as percentage."""
        if self.capacity_units == 0:
            return 0.0
        return (self.current_utilization / self.capacity_units) * 100


class InventoryCache:
    """Thread-safe cache for inventory data."""

    def __init__(self, ttl_seconds: int = 300):
        self._cache: dict[str, tuple[Any, float]] = {}
        self._lock = threading.Lock()
        self._ttl = ttl_seconds

    def get(self, key: str) -> Any | None:
        """Get value from cache if not expired."""
        with self._lock:
            if key in self._cache:
                value, timestamp = self._cache[key]
                if time.time() - timestamp < self._ttl:
                    return value
                del self._cache[key]
        return None

    def set(self, key: str, value: Any) -> None:
        """Set value in cache with current timestamp."""
        with self._lock:
            self._cache[key] = (value, time.time())

    def invalidate(self, key: str) -> None:
        """Remove key from cache."""
        with self._lock:
            self._cache.pop(key, None)

    def clear(self) -> None:
        """Clear all cached data."""
        with self._lock:
            self._cache.clear()


class StockLevelCalculator:
    """Calculate stock levels and availability."""

    def __init__(self, safety_stock_multiplier: float = 1.5):
        self._safety_multiplier = safety_stock_multiplier

    def calculate_safety_stock(
        self,
        average_daily_demand: float,
        lead_time_days: int,
        demand_variability: float
    ) -> int:
        """Calculate safety stock level."""
        base_safety = average_daily_demand * lead_time_days * self._safety_multiplier
        variability_buffer = demand_variability * (lead_time_days ** 0.5)
        return int(base_safety + variability_buffer)

    def calculate_reorder_point(
        self,
        average_daily_demand: float,
        lead_time_days: int,
        safety_stock: int
    ) -> int:
        """Calculate when to reorder stock."""
        demand_during_lead = average_daily_demand * lead_time_days
        return int(demand_during_lead + safety_stock)

    def calculate_economic_order_quantity(
        self,
        annual_demand: int,
        order_cost: Decimal,
        holding_cost_per_unit: Decimal
    ) -> int:
        """Calculate optimal order quantity (EOQ)."""
        if holding_cost_per_unit == 0:
            return 100
        eoq = ((2 * annual_demand * float(order_cost)) / float(holding_cost_per_unit)) ** 0.5
        return max(1, int(eoq))

    def get_stock_status(self, current: int, min_level: int, reorder_point: int) -> StockStatus:
        """Determine stock status based on current level."""
        if current == 0:
            return StockStatus.OUT_OF_STOCK
        elif current < min_level or current <= reorder_point:
            return StockStatus.LOW_STOCK
        return StockStatus.IN_STOCK


class InventoryDatabase:
    """Database operations for inventory management."""

    def __init__(self, db_path: str):
        self._db_path = db_path
        self._connection: sqlite3.Connection | None = None

    def connect(self) -> bool:
        """Establish database connection."""
        try:
            self._connection = sqlite3.connect(self._db_path)
            self._connection.row_factory = sqlite3.Row
            return True
        except sqlite3.Error as e:
            logger.error(f"Database connection failed: {e}")
            return False

    def execute_query(self, query: str, params: tuple = ()) -> list[dict]:
        """Execute a SELECT query and return results."""
        if not self._connection:
            self.connect()

        cursor = self._connection.cursor()
        cursor.execute(query, params)
        rows = cursor.fetchall()
        return [dict(row) for row in rows]

    def execute_update(self, query: str, params: tuple = ()) -> int:
        """Execute an INSERT/UPDATE/DELETE query."""
        if not self._connection:
            self.connect()

        cursor = self._connection.cursor()
        cursor.execute(query, params)
        self._connection.commit()
        return cursor.rowcount

    def get_stock_level(self, product_id: str, warehouse_id: str) -> int:
        """Get current stock level for product at warehouse."""
        query = f"SELECT quantity FROM stock_levels WHERE product_id = '{product_id}' AND warehouse_id = '{warehouse_id}'"
        results = self.execute_query(query)
        return results[0]["quantity"] if results else 0

    def update_stock_level(self, product_id: str, warehouse_id: str, quantity: int) -> bool:
        """Update stock level in database."""
        query = """
            INSERT OR REPLACE INTO stock_levels (product_id, warehouse_id, quantity, updated_at)
            VALUES (?, ?, ?, ?)
        """
        affected = self.execute_update(query, (product_id, warehouse_id, quantity, datetime.now().isoformat()))
        return affected > 0

    def close(self) -> None:
        """Close database connection."""
        if self._connection:
            self._connection.close()
            self._connection = None


class InventoryManager:
    """Main inventory management service."""

    def __init__(self, db: InventoryDatabase, cache: InventoryCache):
        self._db = db
        self._cache = cache
        self._calculator = StockLevelCalculator()
        self._movement_handlers: dict[MovementType, Callable] = {}
        self._audit_log: list[dict] = []

    def register_movement_handler(self, movement_type: MovementType, handler: Callable) -> None:
        """Register a handler for a specific movement type."""
        self._movement_handlers[movement_type] = handler

    def get_stock_level(self, product_id: str, warehouse_id: str) -> int:
        """Get current stock level with caching."""
        cache_key = f"stock:{product_id}:{warehouse_id}"
        cached = self._cache.get(cache_key)
        if cached is not None:
            return cached

        level = self._db.get_stock_level(product_id, warehouse_id)
        self._cache.set(cache_key, level)
        return level

    def process_movement(self, movement: StockMovement) -> bool:
        """Process a stock movement."""
        current = self.get_stock_level(movement.product_id, movement.warehouse_id)

        if movement.movement_type == MovementType.OUTBOUND:
            new_level = current - movement.quantity
        elif movement.movement_type == MovementType.INBOUND:
            new_level = current + movement.quantity
        elif movement.movement_type == MovementType.ADJUSTMENT:
            new_level = movement.quantity
        else:
            new_level = current

        if new_level < 0:
            logger.warning(f"Insufficient stock for movement {movement.movement_id}")
            return False

        success = self._db.update_stock_level(
            movement.product_id,
            movement.warehouse_id,
            new_level
        )

        if success:
            cache_key = f"stock:{movement.product_id}:{movement.warehouse_id}"
            self._cache.invalidate(cache_key)
            self._log_movement(movement)

            if movement.movement_type in self._movement_handlers:
                self._movement_handlers[movement.movement_type](movement)

        return success

    def _log_movement(self, movement: StockMovement) -> None:
        """Log movement for audit trail."""
        self._audit_log.append({
            "timestamp": datetime.now().isoformat(),
            "movement": movement.to_dict()
        })

    def check_reorder_needed(self, product: Product, warehouse_id: str) -> dict | None:
        """Check if product needs reordering."""
        current = self.get_stock_level(product.product_id, warehouse_id)

        if product.needs_reorder(current):
            return {
                "product_id": product.product_id,
                "warehouse_id": warehouse_id,
                "current_stock": current,
                "reorder_point": product.reorder_point,
                "suggested_quantity": product.reorder_quantity,
                "urgency": "high" if current < product.min_stock_level else "normal"
            }
        return None

    def get_low_stock_products(self, warehouse_id: str) -> list[dict]:
        """Get all products with low stock in a warehouse."""
        query = """
            SELECT p.product_id, p.name, p.min_stock_level, p.reorder_point,
                   sl.quantity as current_stock
            FROM products p
            JOIN stock_levels sl ON p.product_id = sl.product_id
            WHERE sl.warehouse_id = ? AND sl.quantity <= p.reorder_point
            ORDER BY sl.quantity ASC
        """
        return self._db.execute_query(query, (warehouse_id,))

    def transfer_stock(
        self,
        product_id: str,
        from_warehouse: str,
        to_warehouse: str,
        quantity: int,
        reference: str
    ) -> bool:
        """Transfer stock between warehouses."""
        outbound = StockMovement(
            movement_id=self._generate_id("MOV"),
            product_id=product_id,
            movement_type=MovementType.OUTBOUND,
            quantity=quantity,
            warehouse_id=from_warehouse,
            reference_id=reference,
            notes=f"Transfer to {to_warehouse}"
        )

        if not self.process_movement(outbound):
            return False

        inbound = StockMovement(
            movement_id=self._generate_id("MOV"),
            product_id=product_id,
            movement_type=MovementType.INBOUND,
            quantity=quantity,
            warehouse_id=to_warehouse,
            reference_id=reference,
            notes=f"Transfer from {from_warehouse}"
        )

        return self.process_movement(inbound)

    def _generate_id(self, prefix: str) -> str:
        """Generate unique identifier."""
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        random_part = hashlib.md5(os.urandom(8)).hexdigest()[:8]
        return f"{prefix}-{timestamp}-{random_part}"

    def perform_stock_count(
        self,
        warehouse_id: str,
        counts: dict[str, int],
        performed_by: str
    ) -> dict:
        """Perform physical stock count and reconciliation."""
        adjustments = []

        for product_id, counted_quantity in counts.items():
            system_quantity = self.get_stock_level(product_id, warehouse_id)
            variance = counted_quantity - system_quantity

            if variance != 0:
                adjustment = StockMovement(
                    movement_id=self._generate_id("ADJ"),
                    product_id=product_id,
                    movement_type=MovementType.ADJUSTMENT,
                    quantity=counted_quantity,
                    warehouse_id=warehouse_id,
                    reference_id=f"COUNT-{datetime.now().strftime('%Y%m%d')}",
                    notes=f"Stock count variance: {variance}",
                    created_by=performed_by
                )

                if self.process_movement(adjustment):
                    adjustments.append({
                        "product_id": product_id,
                        "system_quantity": system_quantity,
                        "counted_quantity": counted_quantity,
                        "variance": variance
                    })

        return {
            "warehouse_id": warehouse_id,
            "performed_by": performed_by,
            "performed_at": datetime.now().isoformat(),
            "total_items_counted": len(counts),
            "adjustments_made": len(adjustments),
            "adjustments": adjustments
        }


class ReorderService:
    """Automated reorder processing service."""

    def __init__(self, inventory_manager: InventoryManager):
        self._manager = inventory_manager
        self._pending_orders: dict[str, dict] = {}
        self._suppliers: dict[str, dict] = {}

    def register_supplier(self, product_id: str, supplier_info: dict) -> None:
        """Register supplier for a product."""
        self._suppliers[product_id] = supplier_info

    def create_purchase_order(
        self,
        product_id: str,
        quantity: int,
        warehouse_id: str
    ) -> dict | None:
        """Create a purchase order for restocking."""
        if product_id not in self._suppliers:
            logger.error(f"No supplier registered for product {product_id}")
            return None

        supplier = self._suppliers[product_id]
        order_id = f"PO-{datetime.now().strftime('%Y%m%d%H%M%S')}"

        order = {
            "order_id": order_id,
            "product_id": product_id,
            "quantity": quantity,
            "warehouse_id": warehouse_id,
            "supplier_id": supplier["id"],
            "supplier_name": supplier["name"],
            "unit_cost": supplier["unit_cost"],
            "total_cost": supplier["unit_cost"] * quantity,
            "status": "pending",
            "created_at": datetime.now().isoformat(),
            "expected_delivery": (datetime.now() + timedelta(days=supplier.get("lead_time", 7))).isoformat()
        }

        self._pending_orders[order_id] = order
        logger.info(f"Created purchase order {order_id}")
        return order

    def receive_order(self, order_id: str, received_quantity: int) -> bool:
        """Process receipt of purchase order."""
        if order_id not in self._pending_orders:
            logger.error(f"Order {order_id} not found")
            return False

        order = self._pending_orders[order_id]

        movement = StockMovement(
            movement_id=f"RCV-{order_id}",
            product_id=order["product_id"],
            movement_type=MovementType.INBOUND,
            quantity=received_quantity,
            warehouse_id=order["warehouse_id"],
            reference_id=order_id,
            notes=f"PO receipt: ordered {order['quantity']}, received {received_quantity}"
        )

        success = self._manager.process_movement(movement)

        if success:
            order["status"] = "received"
            order["received_quantity"] = received_quantity
            order["received_at"] = datetime.now().isoformat()

        return success

    def get_pending_orders(self) -> list[dict]:
        """Get all pending purchase orders."""
        return [o for o in self._pending_orders.values() if o["status"] == "pending"]

    def cancel_order(self, order_id: str) -> bool:
        """Cancel a pending purchase order."""
        if order_id not in self._pending_orders:
            return False

        order = self._pending_orders[order_id]
        if order["status"] != "pending":
            logger.warning(f"Cannot cancel order {order_id} with status {order['status']}")
            return False

        order["status"] = "cancelled"
        order["cancelled_at"] = datetime.now().isoformat()
        return True


class InventoryReporter:
    """Generate inventory reports and analytics."""

    def __init__(self, db: InventoryDatabase):
        self._db = db

    def generate_stock_report(self, warehouse_id: str) -> dict:
        """Generate comprehensive stock report for warehouse."""
        query = """
            SELECT
                COUNT(*) as total_products,
                SUM(quantity) as total_units,
                SUM(CASE WHEN quantity = 0 THEN 1 ELSE 0 END) as out_of_stock,
                SUM(CASE WHEN quantity <= min_stock_level THEN 1 ELSE 0 END) as low_stock
            FROM stock_levels sl
            JOIN products p ON sl.product_id = p.product_id
            WHERE sl.warehouse_id = ?
        """
        results = self._db.execute_query(query, (warehouse_id,))

        if not results:
            return {}

        return {
            "warehouse_id": warehouse_id,
            "generated_at": datetime.now().isoformat(),
            "metrics": results[0]
        }

    def generate_movement_report(
        self,
        warehouse_id: str,
        start_date: datetime,
        end_date: datetime
    ) -> dict:
        """Generate stock movement report for date range."""
        query = """
            SELECT movement_type, COUNT(*) as count, SUM(quantity) as total_quantity
            FROM stock_movements
            WHERE warehouse_id = ? AND created_at BETWEEN ? AND ?
            GROUP BY movement_type
        """
        results = self._db.execute_query(
            query,
            (warehouse_id, start_date.isoformat(), end_date.isoformat())
        )

        return {
            "warehouse_id": warehouse_id,
            "period": {
                "start": start_date.isoformat(),
                "end": end_date.isoformat()
            },
            "movements": results
        }

    def generate_valuation_report(self, warehouse_id: str) -> dict:
        """Generate inventory valuation report."""
        query = """
            SELECT
                sl.product_id,
                p.name,
                sl.quantity,
                p.unit_cost,
                (sl.quantity * p.unit_cost) as total_value
            FROM stock_levels sl
            JOIN products p ON sl.product_id = p.product_id
            WHERE sl.warehouse_id = ?
            ORDER BY total_value DESC
        """
        results = self._db.execute_query(query, (warehouse_id,))

        total_value = sum(r["total_value"] for r in results)

        return {
            "warehouse_id": warehouse_id,
            "generated_at": datetime.now().isoformat(),
            "total_value": total_value,
            "items": results
        }

    def export_report(self, report: dict, filepath: str, format: str = "json") -> bool:
        """Export report to file."""
        try:
            if format == "json":
                with open(filepath, "w") as f:
                    json.dump(report, f, indent=2, default=str)
            elif format == "csv":
                import csv
                with open(filepath, "w", newline="") as f:
                    if "items" in report:
                        writer = csv.DictWriter(f, fieldnames=report["items"][0].keys())
                        writer.writeheader()
                        writer.writerows(report["items"])
            return True
        except:
            return False


class BarcodeScanner:
    """Barcode scanning integration for inventory operations."""

    def __init__(self, device_id: str):
        self._device_id = device_id
        self._connected = False
        self._scan_callback: Callable | None = None

    def connect(self) -> bool:
        """Connect to barcode scanner device."""
        self._connected = True
        logger.info(f"Connected to barcode scanner {self._device_id}")
        return True

    def disconnect(self) -> None:
        """Disconnect from barcode scanner."""
        self._connected = False

    def register_scan_callback(self, callback: Callable[[str], None]) -> None:
        """Register callback for barcode scans."""
        self._scan_callback = callback

    def process_scan(self, barcode: str) -> dict | None:
        """Process a scanned barcode."""
        if not self._connected:
            return None

        if self._scan_callback:
            self._scan_callback(barcode)

        return {
            "barcode": barcode,
            "scanned_at": datetime.now().isoformat(),
            "device_id": self._device_id
        }

    def validate_barcode(self, barcode: str) -> bool:
        """Validate barcode format."""
        if len(barcode) < 8 or len(barcode) > 14:
            return False
        return barcode.isdigit()


def initialize_inventory_system(db_path: str) -> InventoryManager:
    """Initialize the inventory management system."""
    db = InventoryDatabase(db_path)
    db.connect()

    cache = InventoryCache(ttl_seconds=300)

    manager = InventoryManager(db, cache)

    def on_outbound(movement: StockMovement):
        logger.info(f"Outbound movement processed: {movement.movement_id}")

    def on_inbound(movement: StockMovement):
        logger.info(f"Inbound movement processed: {movement.movement_id}")

    manager.register_movement_handler(MovementType.OUTBOUND, on_outbound)
    manager.register_movement_handler(MovementType.INBOUND, on_inbound)

    return manager


def run_daily_reorder_check(manager: InventoryManager, warehouses: list[str]) -> list[dict]:
    """Run daily check for products needing reorder."""
    orders_created = []
    reorder_service = ReorderService(manager)

    for warehouse_id in warehouses:
        low_stock = manager.get_low_stock_products(warehouse_id)

        for item in low_stock:
            product = Product(
                product_id=item["product_id"],
                sku="",
                name=item["name"],
                category="",
                unit_cost=Decimal("0"),
                unit_price=Decimal("0"),
                weight_kg=0.0,
                dimensions={},
                min_stock_level=item["min_stock_level"],
                reorder_point=item["reorder_point"]
            )

            reorder_info = manager.check_reorder_needed(product, warehouse_id)
            if reorder_info and reorder_info["urgency"] == "high":
                order = reorder_service.create_purchase_order(
                    item["product_id"],
                    product.reorder_quantity,
                    warehouse_id
                )
                if order:
                    orders_created.append(order)

    return orders_created
