# Python Onboarding Patterns

> Patterns for migrating Python projects to Invar framework.
> Library: `returns` (dry-python)

## 1. Overview

```python
# Library: returns (dry-python)
# Install: pip install returns

from returns.result import Result, Success, Failure
from returns.io import IOResultE
from returns.future import FutureResultE
```

---

## 2. Error Handling

### 2.1 Basic Transformation

```python
# Before: raise
def get_user(id: str) -> User:
    user = db.find(id)
    if not user:
        raise NotFoundError(f"User {id} not found")
    return user

# After: Result
from returns.result import Result, Success, Failure

def get_user(id: str) -> Result[User, NotFoundError]:
    user = db.find(id)
    if not user:
        return Failure(NotFoundError(f"User {id} not found"))
    return Success(user)
```

### 2.2 Async Handling

```python
from returns.future import FutureResultE
from returns.io import IOResultE

# Async I/O operations
async def get_user_async(id: str) -> FutureResultE[User, GetUserError]:
    """Use FutureResultE for async operations."""
    ...

# Sync I/O operations
def read_config() -> IOResultE[Config, ConfigError]:
    """Use IOResultE for sync I/O with Result."""
    ...
```

### 2.3 Exception Catching (@safe)

```python
from returns.result import safe

@safe
def parse_json(data: str) -> dict:
    """Automatically converts exceptions to Failure.

    >>> parse_json('{"a": 1}').unwrap()
    {'a': 1}
    >>> parse_json('invalid').is_failure()
    True
    """
    return json.loads(data)  # JSONDecodeError -> Failure
```

### 2.4 Chaining (bind, map)

```python
def process_order(order_id: str) -> Result[Receipt, OrderError]:
    """Chain multiple Result operations."""
    return (
        get_order(order_id)          # Result[Order, NotFoundError]
        .bind(validate_order)        # -> Result[Order, ValidationError]
        .map(calculate_total)        # -> Result[float, ...] (pure transform)
        .bind(charge_payment)        # -> Result[Payment, PaymentError]
        .map(generate_receipt)       # -> Result[Receipt, ...]
    )
```

### 2.5 Error Type Hierarchy

```python
from dataclasses import dataclass
from typing import Union
from returns.result import Result

@dataclass
class DomainError:
    """Base error type."""
    message: str
    code: str

@dataclass
class NotFoundError(DomainError):
    entity: str
    id: str

@dataclass
class ValidationError(DomainError):
    field: str
    reason: str

# Union type for function signatures
OrderError = Union[NotFoundError, ValidationError, PaymentError]

def process(id: str) -> Result[Order, OrderError]:
    ...
```

### 2.6 Combining Multiple Results

```python
from returns.result import Result, Success
from returns.pointfree import bind
from returns.pipeline import flow

def validate_all(items: list[Item]) -> Result[list[Item], ValidationError]:
    """Collect all validation results."""
    results = [validate_item(item) for item in items]

    # Fail on first error
    for r in results:
        if r.is_failure():
            return r

    return Success([r.unwrap() for r in results])
```

---

## 3. Contracts

### 3.1 Input Validation (@pre)

```python
from deal import pre
from returns.result import Result

@pre(lambda id: len(id) > 0 and len(id) <= 36)
@pre(lambda id: id.replace("-", "").isalnum())  # UUID format
def get_user(id: str) -> Result[User, NotFoundError]:
    """
    Get user by ID.

    >>> get_user("user-123").unwrap().name
    'Alice'
    >>> get_user("").is_failure()  # Precondition fails
    True
    """
    ...
```

### 3.2 Pure Function Contracts

```python
from deal import pre, post

@pre(lambda amount, rate=0.1: amount > 0 and 0 <= rate <= 1)
@post(lambda result: result >= 0)
def calculate_tax(amount: float, rate: float = 0.1) -> float:
    """
    Calculate tax amount.

    >>> calculate_tax(100)
    10.0
    >>> calculate_tax(100, 0.2)
    20.0
    >>> calculate_tax(-100)  # Precondition fails
    Traceback (most recent call last):
        ...
    """
    return amount * rate
```

### 3.3 Pydantic Integration

```python
from pydantic import BaseModel, field_validator
from deal import pre
from returns.result import Result

class CreateUserRequest(BaseModel):
    """Input validation via Pydantic."""
    email: str
    name: str

    @field_validator('email')
    def validate_email(cls, v):
        if '@' not in v:
            raise ValueError('Invalid email')
        return v.lower()

# Invar contract for business rules
@pre(lambda req: not user_exists(req.email))  # Business rule
def create_user(req: CreateUserRequest) -> Result[User, CreateUserError]:
    ...
```

---

## 4. Core/Shell Separation

### 4.1 Directory Structure

```
src/myapp/
├── core/                    # Pure functions, no I/O
│   ├── __init__.py
│   ├── order/
│   │   ├── validation.py    # @pre/@post + doctests
│   │   ├── calculation.py   # Pure calculations
│   │   └── types.py         # Domain types
│   └── user/
│       └── ...
└── shell/                   # I/O operations
    ├── __init__.py
    ├── repositories/        # Data access
    │   └── order_repo.py
    ├── services/            # Business orchestration
    │   └── order_service.py
    └── api/                 # HTTP layer
        └── routes.py
```

### 4.2 Core Layer Example

```python
# core/order/validation.py
from deal import pre, post
from returns.result import Result, Success, Failure
from .types import Order, ValidationError

@pre(lambda order: len(order.items) > 0)
def validate_order(order: Order) -> Result[Order, ValidationError]:
    """
    Validate order business rules.

    >>> order = Order(items=[OrderItem(sku="A", qty=1)])
    >>> validate_order(order).is_success()
    True
    >>> validate_order(Order(items=[])).is_failure()
    True
    """
    for item in order.items:
        if item.qty <= 0:
            return Failure(ValidationError(field="qty", reason="must be positive"))
    return Success(order)

def calculate_total(order: Order) -> float:
    """
    Calculate order total (pure function).

    >>> order = Order(items=[OrderItem(sku="A", qty=2, price=10.0)])
    >>> calculate_total(order)
    20.0
    """
    return sum(item.qty * item.price for item in order.items)
```

### 4.3 Shell Layer Example

```python
# shell/services/order_service.py
from returns.result import Result
from myapp.core.order.validation import validate_order, calculate_total
from myapp.shell.repositories.order_repo import OrderRepository

class OrderService:
    def __init__(self, repo: OrderRepository):
        self._repo = repo

    def process_order(self, order_id: str) -> Result[Receipt, OrderError]:
        """Orchestrate Core functions and I/O operations."""
        return (
            self._repo.find(order_id)           # Shell: I/O
            .bind(validate_order)               # Core: pure validation
            .map(calculate_total)               # Core: pure calculation
            .bind(lambda total:
                self._repo.save_total(order_id, total))  # Shell: I/O
        )
```

---

## 5. FastAPI Integration

```python
from fastapi import FastAPI, HTTPException
from returns.result import Result

app = FastAPI()

def result_to_response(result: Result):
    """Convert Result to HTTP response."""
    if result.is_success():
        return result.unwrap()

    error = result.failure()
    if isinstance(error, NotFoundError):
        raise HTTPException(status_code=404, detail=error.message)
    elif isinstance(error, ValidationError):
        raise HTTPException(status_code=400, detail=error.message)
    else:
        raise HTTPException(status_code=500, detail="Internal error")

@app.get("/users/{user_id}")
async def get_user_endpoint(user_id: str):
    result = user_service.get_user(user_id)
    return result_to_response(result)
```

---

## 6. Must Keep `raise` Scenarios

```python
# 1. WSGI/ASGI error handlers (framework expects exceptions)
# 2. Click/Typer CLI (uses exceptions for flow control)
# 3. pytest fixtures (uses exceptions)
# 4. Context managers (__enter__/__exit__)
```

---

## 7. Migration Checklist

- [ ] Install `returns` library: `pip install returns`
- [ ] Define error type hierarchy (`@dataclass` or Pydantic)
- [ ] Transform entry points to return `Result[T, E]`
- [ ] Extract pure functions to `core/` directory
- [ ] Add `@pre/@post` contracts to Core functions
- [ ] Add doctests to all Core functions
- [ ] Run `invar guard` to verify
- [ ] Update API handlers to use `result_to_response`

---

*Pattern Library v1.0 — LX-09*
