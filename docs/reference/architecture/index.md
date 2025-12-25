# Architecture Mechanisms

Invar enforces a two-layer architecture for maintainable, testable code.

## Core/Shell Separation

### Core Layer (`src/*/core/`)

**Purpose:** Pure business logic, fully testable

**Requirements:**
- `@pre`/`@post` contracts on functions
- Doctests for verification
- No I/O imports (os, sys, pathlib, subprocess, etc.)

**Example:**
```python
# src/myapp/core/calc.py
from deal import pre, post

@pre(lambda x, y: y != 0)
@post(lambda result: isinstance(result, float))
def divide(x: float, y: float) -> float:
    """
    >>> divide(10.0, 2.0)
    5.0
    >>> divide(1.0, 0.0)  # Raises PreContractError
    Traceback (most recent call last):
        ...
    deal.PreContractError: ...
    """
    return x / y
```

### Shell Layer (`src/*/shell/`)

**Purpose:** I/O orchestration, error handling

**Requirements:**
- Return `Result[T, E]` for error handling
- Delegate logic to Core functions
- Handle I/O (files, network, CLI)

**Example:**
```python
# src/myapp/shell/api.py
from returns.result import Result, Success, Failure
from myapp.core.calc import divide

def divide_endpoint(x: float, y: float) -> Result[float, str]:
    """Handle division request with proper error handling."""
    if y == 0:
        return Failure("Division by zero")
    return Success(divide(x, y))
```

## Entry Points (DX-23)

Entry points are framework callbacks that don't return `Result[T, E]`.

### Auto-Detected Frameworks

| Framework | Decorator Pattern |
|-----------|------------------|
| Flask | `@app.route`, `@blueprint.route` |
| FastAPI | `@app.get`, `@router.post` |
| Typer | `@app.command` |
| Click | `@click.command` |
| pytest | `@pytest.fixture` |

### Entry Point Rules

1. **Exempt from Result requirement** - Can return framework types
2. **Must be thin** - Max 15 lines (configurable: `entry_max_lines`)
3. **Delegate to Shell** - Business logic in Result-returning functions

**Example:**
```python
@app.command()
def process(file: Path) -> None:
    """Entry point - thin wrapper."""
    result = process_file(file)  # Shell function returns Result
    if isinstance(result, Failure):
        console.print(f"[red]Error:[/red] {result.failure()}")
        raise typer.Exit(1)
    console.print(f"[green]Success:[/green] {result.unwrap()}")
```

### Manual Marker

For custom frameworks not auto-detected:
```python
# @shell:entry
def custom_callback():
    ...
```

## Fix-or-Explain Markers

### `@shell_orchestration:`

For Shell functions that coordinate modules without direct I/O:

```python
# @shell_orchestration: Coordinates verification phases
def run_verification(path: Path) -> Result[Report, str]:
    static_result = run_static(path)
    doctest_result = run_doctests(path)
    return combine_results(static_result, doctest_result)
```

### `@shell_complexity:`

For justified complexity that cannot be refactored:

```python
# @shell_complexity: Config cascade with multiple fallback sources
def load_config(path: Path) -> Result[Config, str]:
    # Check file, env, defaults - branching is inherent
    ...
```

## Configuration

In `pyproject.toml`:

```toml
[tool.invar]
max_file_lines = 500
max_function_lines = 50
entry_max_lines = 15          # DX-23
shell_max_branches = 3        # DX-22
shell_complexity_debt_limit = 5  # DX-22 Fix-or-Explain
```
