# ruff: noqa: ERA001
"""
Invar Core/Shell Separation Examples

Reference patterns for Core vs Shell architecture.
Managed by Invar - do not edit directly.
"""
# @invar:allow forbidden_import: Example file demonstrates Shell pattern with pathlib
# @invar:allow missing_contract: Shell functions intentionally without contracts to show pattern
# @invar:allow contract_quality_ratio: Educational file with Shell examples

from pathlib import Path

# invar_runtime supports both lambda and Contract objects
from invar_runtime import post, pre
from returns.result import Failure, Result, Success

# =============================================================================
# CORE: Pure Logic (no I/O)
# =============================================================================
# Location: src/*/core/
# Requirements: @pre/@post, doctests, no I/O imports
# =============================================================================


# @invar:allow shell_result: Example file - demonstrates Core pattern
# @shell_orchestration: Example file - demonstrates Core pattern
@pre(lambda content: content is not None)  # Accepts any string including empty
@post(lambda result: all(line.strip() == line and line for line in result))  # No whitespace, non-empty
def parse_lines(content: str) -> list[str]:
    """
    Parse content into non-empty lines.

    >>> parse_lines("a\\nb\\nc")
    ['a', 'b', 'c']
    >>> parse_lines("")
    []
    >>> parse_lines("  \\n  ")  # Edge: whitespace only
    []
    """
    return [line.strip() for line in content.split("\n") if line.strip()]


# @invar:allow shell_result: Example file - demonstrates Core pattern
# @shell_orchestration: Example file - demonstrates Core pattern
@pre(lambda items: all(isinstance(i, str) for i in items))  # All items must be strings
@post(lambda result: all(v > 0 for v in result.values()))  # All counts are positive
def count_items(items: list[str]) -> dict[str, int]:
    """
    Count occurrences of each item.

    >>> sorted(count_items(['a', 'b', 'a']).items())
    [('a', 2), ('b', 1)]
    >>> count_items([])
    {}
    """
    counts: dict[str, int] = {}
    for item in items:
        counts[item] = counts.get(item, 0) + 1
    return counts


# =============================================================================
# SHELL: I/O Operations
# =============================================================================
# Location: src/*/shell/
# Requirements: Result[T, E] return type, calls Core for logic
# =============================================================================


def read_file(path: Path) -> Result[str, str]:
    """
    Read file content.

    Shell handles I/O, returns Result for error handling.
    """
    try:
        return Success(path.read_text())
    except FileNotFoundError:
        return Failure(f"File not found: {path}")
    except PermissionError:
        return Failure(f"Permission denied: {path}")


def count_lines_in_file(path: Path) -> Result[dict[str, int], str]:
    """
    Count lines in file - demonstrates Core/Shell integration.

    Shell reads file → Core parses content → Shell returns result.
    """
    # Shell: I/O operation
    content_result = read_file(path)

    if isinstance(content_result, Failure):
        return content_result

    content = content_result.unwrap()

    # Core: Pure logic (no I/O)
    lines = parse_lines(content)
    counts = count_items(lines)

    # Shell: Return result
    return Success(counts)


# =============================================================================
# ANTI-PATTERNS
# =============================================================================

# DON'T: I/O in Core
# def parse_file(path: Path):  # BAD: Path in Core
#     content = path.read_text()  # BAD: I/O in Core
#     return parse_lines(content)

# DO: Core receives content, not paths
# def parse_content(content: str):  # GOOD: receives data
#     return parse_lines(content)


# DON'T: Missing Result in Shell
# def load_config(path: Path) -> dict:  # BAD: no Result type
#     return json.loads(path.read_text())  # Exceptions not handled

# DO: Return Result[T, E]
# def load_config(path: Path) -> Result[dict, str]:  # GOOD
#     try:
#         return Success(json.loads(path.read_text()))
#     except Exception as e:
#         return Failure(str(e))


# =============================================================================
# FastAPI Integration Pattern
# =============================================================================
# Demonstrates how to use Result with FastAPI endpoints.
# Shell (API handler) → Core (business logic) → Shell (HTTP response)

# NOTE: This is pseudocode - requires FastAPI to be installed
# from fastapi import FastAPI, HTTPException
# from pydantic import BaseModel

# class UserResponse(BaseModel):
#     id: str
#     name: str

# app = FastAPI()

# CORE: Pure business logic
# @pre(lambda user_id: len(user_id) > 0)
# @post(lambda result: result.get("name") is not None)
# def get_user_data(user_id: str) -> dict:
#     """Core function - pure logic, receives string ID."""
#     # Business logic here (no HTTP, no database I/O)
#     return {"id": user_id, "name": "Demo User"}

# SHELL: I/O layer - database
# def fetch_user_from_db(user_id: str) -> Result[dict, str]:
#     """Shell function - database I/O, returns Result."""
#     try:
#         # In real code: query database
#         if user_id == "not-found":
#             return Failure("User not found")
#         return Success({"id": user_id, "name": "DB User"})
#     except Exception as e:
#         return Failure(f"Database error: {e}")

# SHELL: I/O layer - HTTP endpoint
# @app.get("/users/{user_id}", response_model=UserResponse)
# def get_user_endpoint(user_id: str):
#     """
#     FastAPI endpoint - Shell layer.
#
#     Pattern: Shell → Core → Shell
#     1. Shell receives HTTP request
#     2. Core processes business logic
#     3. Shell converts Result to HTTP response
#     """
#     result = fetch_user_from_db(user_id)
#
#     # Convert Result to HTTP response
#     match result:
#         case Success(user):
#             return UserResponse(**user)
#         case Failure(error):
#             if "not found" in error.lower():
#                 raise HTTPException(status_code=404, detail=error)
#             raise HTTPException(status_code=500, detail=error)


# =============================================================================
# Result → HTTP Response Mapping
# =============================================================================
# Common pattern for converting Result errors to HTTP status codes:
#
# | Error Type      | HTTP Status | When to Use                    |
# |-----------------|-------------|--------------------------------|
# | NotFoundError   | 404         | Resource doesn't exist         |
# | ValidationError | 400         | Invalid input from client      |
# | AuthError       | 401/403     | Authentication/authorization   |
# | ConflictError   | 409         | Resource state conflict        |
# | InternalError   | 500         | Unexpected server error        |
#
# Example error types:
# @dataclass(frozen=True)
# class NotFoundError:
#     resource: str
#     id: str
#
# @dataclass(frozen=True)
# class ValidationError:
#     field: str
#     message: str
#
# AppError = NotFoundError | ValidationError | str
#
# def result_to_response(result: Result[T, AppError]) -> T:
#     """Convert Result to HTTP response or raise appropriate HTTPException."""
#     match result:
#         case Success(value):
#             return value
#         case Failure(NotFoundError(resource, id)):
#             raise HTTPException(404, f"{resource} {id} not found")
#         case Failure(ValidationError(field, message)):
#             raise HTTPException(400, f"Invalid {field}: {message}")
#         case Failure(error):
#             raise HTTPException(500, str(error))
