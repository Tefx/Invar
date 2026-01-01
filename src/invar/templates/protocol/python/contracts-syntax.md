## Contract Syntax (Python)

### Lambda Signature (Critical)

```python
# WRONG: Lambda only takes first parameter
@pre(lambda x: x >= 0)
def calculate(x: int, y: int = 0): ...

# CORRECT: Lambda must include ALL parameters (even defaults)
@pre(lambda x, y=0: x >= 0)
def calculate(x: int, y: int = 0): ...
```

Guard's `param_mismatch` rule catches this as ERROR.

### Meaningful Contracts

```python
# Redundant - type hints already check this
@pre(lambda x: isinstance(x, int))
def calc(x: int): ...

# Meaningful - checks business logic
@pre(lambda x: x > 0)
def calc(x: int): ...

# Meaningful - checks relationship between params
@pre(lambda start, end: start < end)
def process_range(start: int, end: int): ...
```

### @post Scope

```python
# WRONG: @post cannot access function parameters
@post(lambda result: result > x)  # 'x' not available!
def calc(x: int) -> int: ...

# CORRECT: @post can only use 'result'
@post(lambda result: result >= 0)
def calc(x: int) -> int: ...
```

### Doctest Examples

```python
def calculate(x: int) -> int:
    """
    >>> calculate(5)
    10
    >>> calculate(0)      # Edge case
    0
    """
    return x * 2
```
