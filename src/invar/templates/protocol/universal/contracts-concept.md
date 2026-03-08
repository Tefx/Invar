## Contract Concepts

### Precondition
Constraints on inputs that must be true before function executes.

```
PRECONDITION: input_value > 0 AND input_value < 100
```

### Postcondition
Guarantees about outputs that must be true after function executes.

```
POSTCONDITION: result >= 0
```

### Self-Test Rule

> "Can someone else write the exact same function from just the contracts + examples?"

If yes → Contracts are complete.
If no → Add more constraints or examples.

### Meaningful Contracts

Contracts should check **business logic**, not just types:

```
# Redundant - type system already checks this
PRECONDITION: x is integer

# Meaningful - checks business logic
PRECONDITION: x > 0

# Meaningful - checks relationship between params
PRECONDITION: start < end
```
