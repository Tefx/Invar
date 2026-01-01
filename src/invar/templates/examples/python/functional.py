"""
Invar Functional Pattern Examples (DX-61)

Reference patterns for higher-quality code. These are SUGGESTIONS, not requirements.
Guard will suggest them when it detects opportunities for improvement.

Patterns covered:
  P0 (Core):
    1. NewType         - Semantic clarity for primitive types
    2. Validation      - Error accumulation instead of fail-fast
    3. NonEmpty        - Compile-time safety for non-empty collections
    4. Literal         - Type-safe finite value sets
    5. ExhaustiveMatch - Catch missing cases at compile time

  P1 (Extended):
    6. SmartConstructor - Validation at construction time
    7. StructuredError  - Typed errors for programmatic handling

Managed by Invar - do not edit directly.
"""
# @invar:allow missing_contract: Educational file with intentional "bad" examples
# @invar:allow partial_contract: Educational file with intentional "bad" examples
# @invar:allow contract_quality_ratio: Educational file - coverage intentionally low
# @invar:allow file_size: Educational file with comprehensive pattern examples
# @invar:allow internal_import: Demo functions show self-contained examples

import json
from dataclasses import dataclass
from enum import Enum
from typing import Generic, Literal, NewType, TypeVar, assert_never

from invar_runtime import post, pre
from returns.result import Failure, Result, Success

T = TypeVar("T")


# =============================================================================
# Pattern 1: NewType for Semantic Clarity (P0)
# =============================================================================

# BEFORE: Easy to confuse parameters - all are just "str"
# def find_symbol_bad(
#     module_path: str,
#     symbol_name: str,
#     file_pattern: str,
# ) -> Symbol:
#     ...

# AFTER: Self-documenting, type-checker catches mistakes
ModulePath = NewType("ModulePath", str)
SymbolName = NewType("SymbolName", str)
FilePattern = NewType("FilePattern", str)


@dataclass(frozen=True)
class Symbol:
    """Example symbol for demonstration."""

    name: str
    line: int


@pre(lambda path, name: len(path) > 0 and len(name) > 0)
@post(lambda result: result is not None)
def find_symbol(path: ModulePath, name: SymbolName) -> Symbol:
    """
    Find symbol by module path and name.

    With NewType, swapping arguments is a type error:
    find_symbol(name, path)  # Type checker catches this!

    >>> find_symbol(ModulePath("src/core"), SymbolName("calculate"))
    Symbol(name='calculate', line=42)
    """
    # Demo implementation
    return Symbol(name=name, line=42)


# =============================================================================
# Pattern 2: Validation for Error Accumulation (P0)
# =============================================================================


@dataclass(frozen=True)
class Config:
    """Example config for validation demo."""

    path: str
    max_lines: int
    enabled: bool


# BEFORE: User sees one error at a time
def validate_config_bad(data: dict) -> Result[Config, str]:
    """
    Bad: Fail-fast validation.

    If multiple fields are invalid, user only sees the first error.
    They fix it, run again, see the next error. Frustrating!
    """
    if "path" not in data:
        return Failure("Missing 'path'")
    if "max_lines" not in data:
        return Failure("Missing 'max_lines'")  # Never reached if path missing
    if "enabled" not in data:
        return Failure("Missing 'enabled'")
    return Success(Config(**data))


# AFTER: User sees all errors at once
def validate_config_good(data: dict) -> Result[Config, list[str]]:
    """
    Good: Accumulating validation.

    Collect all errors, return them together. User can fix everything
    in one iteration. Much better UX!

    >>> validate_config_good({})
    Failure(["Missing 'path'", "Missing 'max_lines'", "Missing 'enabled'"])

    >>> validate_config_good({"path": "/tmp", "max_lines": 100, "enabled": True})
    Success(Config(path='/tmp', max_lines=100, enabled=True))

    >>> result = validate_config_good({"path": ""})
    >>> isinstance(result, Failure)
    True
    >>> "path cannot be empty" in result.failure()
    True
    """
    errors: list[str] = []

    # Collect ALL errors, don't return early
    if "path" not in data:
        errors.append("Missing 'path'")
    elif not data["path"]:
        errors.append("path cannot be empty")

    if "max_lines" not in data:
        errors.append("Missing 'max_lines'")
    elif not isinstance(data["max_lines"], int):
        errors.append("max_lines must be an integer")
    elif data["max_lines"] < 0:
        errors.append("max_lines must be >= 0")

    if "enabled" not in data:
        errors.append("Missing 'enabled'")

    if errors:
        return Failure(errors)

    return Success(
        Config(
            path=data["path"],
            max_lines=data["max_lines"],
            enabled=data["enabled"],
        )
    )


# =============================================================================
# Pattern 3: NonEmpty for Compile-Time Safety (P0)
# =============================================================================


@dataclass(frozen=True)
class NonEmpty(Generic[T]):
    """
    List guaranteed to have at least one element.

    Instead of runtime checks like `if not items: raise`,
    use the type system to guarantee non-emptiness.

    >>> ne = NonEmpty.from_list([1, 2, 3])
    >>> isinstance(ne, Success)
    True
    >>> ne.unwrap().first
    1
    """

    head: T
    tail: tuple[T, ...]

    @property
    def first(self) -> T:
        """Always safe - guaranteed non-empty by construction."""
        return self.head

    @property
    def all(self) -> tuple[T, ...]:
        """Get all elements as tuple."""
        return (self.head, *self.tail)

    def __len__(self) -> int:
        """Length is always >= 1."""
        return 1 + len(self.tail)

    @classmethod
    def from_list(cls, items: list[T]) -> Result["NonEmpty[T]", str]:
        """
        Safely construct from list.

        >>> NonEmpty.from_list([])
        Failure('Cannot create NonEmpty from empty list')

        >>> NonEmpty.from_list([1, 2, 3])
        Success(NonEmpty(head=1, tail=(2, 3)))
        """
        if not items:
            return Failure("Cannot create NonEmpty from empty list")
        return Success(cls(head=items[0], tail=tuple(items[1:])))


# BEFORE: Defensive runtime check
def summarize_bad(items: list[str]) -> str:
    """
    Bad: Runtime check that could be compile-time.

    The `if not items` check is defensive but the type system
    can't help prevent calling with empty list.
    """
    if not items:
        raise ValueError("Cannot summarize empty list")
    return f"First: {items[0]}, Total: {len(items)}"


# AFTER: Type-safe, no check needed
@post(lambda result: "First:" in result)
def summarize_good(items: NonEmpty[str]) -> str:
    """
    Good: Type guarantees non-empty.

    No runtime check needed - if you have a NonEmpty,
    it's guaranteed to have at least one element.

    >>> ne = NonEmpty.from_list(["a", "b", "c"]).unwrap()
    >>> summarize_good(ne)
    'First: a, Total: 3'
    """
    return f"First: {items.first}, Total: {len(items)}"


# =============================================================================
# Pattern 4: Literal for Finite Value Sets (P0)
# =============================================================================

# BEFORE: Runtime validation for finite set
def set_log_level_bad(level: str) -> None:
    """
    Bad: Runtime check for finite values.

    Type checker can't know that only certain strings are valid.
    Invalid values discovered at runtime.
    """
    if level not in ("debug", "info", "warning", "error"):
        raise ValueError(f"Invalid log level: {level}")
    # ... set the level


# AFTER: Compile-time safety with Literal
LogLevel = Literal["debug", "info", "warning", "error"]


def set_log_level_good(level: LogLevel) -> str:
    """
    Good: Type checker catches invalid values.

    >>> set_log_level_good("debug")
    'Log level set to: debug'

    # This would be a type error (caught by mypy/pyright):
    # set_log_level_good("invalid")  # Error!
    """
    return f"Log level set to: {level}"


# =============================================================================
# Pattern 5: Exhaustive Match (P0)
# =============================================================================


class Status(Enum):
    """Task status for exhaustive match demo."""

    PENDING = "pending"
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"


# BEFORE: Missing cases fail silently
def status_message_bad(status: Status) -> str:
    """
    Bad: Non-exhaustive match.

    If a new status is added (e.g., CANCELLED), this code
    silently returns "unknown" instead of failing to compile.
    """
    match status:
        case Status.PENDING:
            return "Waiting to start"
        case Status.RUNNING:
            return "In progress"
        # DONE and FAILED missing - falls through to default!
    return "unknown"


# AFTER: Compiler catches missing cases
def status_message_good(status: Status) -> str:
    """
    Good: Exhaustive match with assert_never.

    If a new status is added, type checker reports an error
    because assert_never expects type Never, but gets the new status.

    >>> status_message_good(Status.PENDING)
    'Waiting to start'
    >>> status_message_good(Status.DONE)
    'Completed successfully'
    >>> status_message_good(Status.FAILED)
    'Task failed'
    """
    match status:
        case Status.PENDING:
            return "Waiting to start"
        case Status.RUNNING:
            return "In progress"
        case Status.DONE:
            return "Completed successfully"
        case Status.FAILED:
            return "Task failed"
        case _:
            assert_never(status)  # Type error if cases are missing!


# =============================================================================
# Pattern 6: Smart Constructor (P1)
# =============================================================================


# BEFORE: Can create invalid objects
@dataclass
class EmailBad:
    """
    Bad: No validation at construction.

    EmailBad("not-an-email") creates an invalid object.
    Validation happens elsewhere, if at all.
    """

    value: str


# AFTER: Validation at construction
@dataclass(frozen=True)
class Email:
    """
    Good: Smart constructor validates on creation.

    Invalid emails can never exist - construction fails.

    >>> Email.create("user@example.com")
    Success(Email(_value='user@example.com'))

    >>> Email.create("not-an-email")
    Failure('Email must contain @')

    >>> Email.create("")
    Failure('Email cannot be empty')
    """

    _value: str

    @classmethod
    def create(cls, value: str) -> Result["Email", str]:
        """Validate and construct email."""
        if not value:
            return Failure("Email cannot be empty")
        if "@" not in value:
            return Failure("Email must contain @")
        if "." not in value.split("@")[1]:
            return Failure("Email domain must have a dot")
        return Success(cls(_value=value))

    @property
    def value(self) -> str:
        """Expose validated value."""
        return self._value


# =============================================================================
# Pattern 7: Structured Error (P1)
# =============================================================================


# BEFORE: String error messages with embedded data
def parse_bad(text: str, line: int) -> Result[str, str]:
    """
    Bad: Error information embedded in string.

    The line number is in the message but not accessible
    for programmatic handling (highlighting, jumping to line).
    """
    if not text:
        return Failure(f"Parse error at line {line}: unexpected EOF")
    return Success(text)


# AFTER: Structured error type
@dataclass(frozen=True)
class ParseError:
    """
    Good: Structured error with accessible fields.

    Code can extract line number for highlighting,
    message for display, etc.
    """

    message: str
    line: int
    column: int = 0


def parse_good(text: str, line: int) -> Result[str, ParseError]:
    """
    Good: Structured error for programmatic handling.

    >>> result = parse_good("", 42)
    >>> isinstance(result, Failure)
    True
    >>> result.failure().line
    42
    >>> result.failure().message
    'unexpected EOF'

    >>> parse_good("valid", 1)
    Success('valid')
    """
    if not text:
        return Failure(ParseError(message="unexpected EOF", line=line))
    return Success(text)


# =============================================================================
# Pattern 8: Optional → Result Conversion
# =============================================================================


def find_user_bad(user_id: str) -> dict | None:
    """
    Bad: Optional return hides error reason.

    Caller can't distinguish "not found" from "invalid id" from "db error".
    """
    # Demo: return None for missing
    if not user_id:
        return None
    return {"id": user_id, "name": "Demo"}


@dataclass(frozen=True)
class UserNotFoundError:
    """Specific error: user doesn't exist."""

    user_id: str


@dataclass(frozen=True)
class InvalidUserIdError:
    """Specific error: invalid ID format."""

    user_id: str
    reason: str


UserError = UserNotFoundError | InvalidUserIdError


def find_user_good(user_id: str) -> Result[dict, UserError]:
    """
    Good: Result with specific error types.

    >>> find_user_good("")
    Failure(InvalidUserIdError(user_id='', reason='empty id'))

    >>> find_user_good("unknown")
    Failure(UserNotFoundError(user_id='unknown'))

    >>> find_user_good("user123")
    Success({'id': 'user123', 'name': 'Demo'})
    """
    if not user_id:
        return Failure(InvalidUserIdError(user_id=user_id, reason="empty id"))
    if user_id == "unknown":
        return Failure(UserNotFoundError(user_id=user_id))
    return Success({"id": user_id, "name": "Demo"})


# =============================================================================
# Pattern 9: try/except → Result Conversion
# =============================================================================


def parse_json_bad(text: str) -> dict:
    """
    Bad: Exceptions for expected errors.

    JSON parsing failure is expected (user input), not exceptional.
    """
    return json.loads(text)  # Raises JSONDecodeError


@dataclass(frozen=True)
class JsonParseError:
    """Structured JSON parse error."""

    message: str
    position: int


def parse_json_good(text: str) -> Result[dict, JsonParseError]:
    """
    Good: Result for expected failures.

    >>> parse_json_good('{"a": 1}')
    Success({'a': 1})

    >>> result = parse_json_good('invalid')
    >>> isinstance(result, Failure)
    True
    >>> result.failure().message
    'Expecting value: line 1 column 1 (char 0)'
    """
    try:
        return Success(json.loads(text))
    except json.JSONDecodeError as e:
        return Failure(JsonParseError(message=str(e), position=e.pos))


# =============================================================================
# Pattern 10: Result Chaining with bind/map
# =============================================================================


def process_pipeline_bad(raw: str) -> str:
    """
    Bad: Nested try/except for sequential operations.

    Error handling scattered, hard to follow the happy path.
    """
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        raise ValueError("Invalid JSON")

    try:
        name = data["user"]["name"]
    except KeyError:
        raise ValueError("Missing user.name")

    return name.upper()


def extract_name(data: dict) -> Result[str, str]:
    """Extract user.name from dict."""
    try:
        return Success(data["user"]["name"])
    except KeyError:
        return Failure("Missing user.name")


def process_pipeline_good(raw: str) -> Result[str, str]:
    """
    Good: Result chaining for sequential operations.

    Happy path is clear: parse → extract → transform.
    Errors propagate automatically.

    >>> process_pipeline_good('{"user": {"name": "alice"}}')
    Success('ALICE')

    >>> process_pipeline_good('invalid json')
    Failure('Expecting value: line 1 column 1 (char 0)')

    >>> process_pipeline_good('{"other": 1}')
    Failure('Missing user.name')
    """
    # Parse JSON → extract name → uppercase
    # Each step returns Result, errors propagate automatically
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        return Failure(str(e))

    return extract_name(data).map(lambda name: name.upper())


# =============================================================================
# Summary: When to Use Each Pattern
# =============================================================================

# | Pattern           | Use When                                    |
# |-------------------|---------------------------------------------|
# | NewType           | 3+ params of same primitive type            |
# | Validation        | Multiple independent validations            |
# | NonEmpty          | Functions that require non-empty input      |
# | Literal           | Parameter with finite valid values          |
# | ExhaustiveMatch   | Matching on enums                           |
# | SmartConstructor  | Types with invariants                       |
# | StructuredError   | Errors with metadata (line, column, etc.)   |
# | Optional→Result   | Functions returning None for failures       |
# | try/except→Result | Wrapping exceptions as Result               |
# | Result Chaining   | Sequential operations with error propagation|
