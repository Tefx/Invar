## Core/Shell Architecture

| Zone | Location | Requirements |
|------|----------|--------------|
| Core | `**/core/**` | Contracts + Examples, pure (no I/O) |
| Shell | `**/shell/**` | Error-handling return type |

### Decision Tree: Core vs Shell

```
Does this function...
│
├─ Read or write files? ──────────────────→ Shell
├─ Make network requests? ─────────────────→ Shell
├─ Access current time? ──────────────────→ Shell OR inject as parameter
├─ Generate random values? ────────────────→ Shell OR inject as parameter
├─ Print to console? ──────────────────────→ Shell (return data, Shell logs)
├─ Access environment variables? ──────────→ Shell
│
└─ None of the above? ─────────────────────→ Core
```

### Injection Pattern (Universal)

Instead of accessing impure values directly, inject them as parameters:

```
# Core: receives 'current_time' as parameter (pure)
FUNCTION is_expired(expiry, current_time):
    RETURN current_time > expiry

# Shell: calls with actual time
expired = is_expired(token.expiry, get_current_time())
```

This keeps Core functions pure and testable.
