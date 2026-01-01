# Visible Workflow Example

Complete example of USBV workflow with checkpoints for complex tasks.

## Scenario

User: "Add rate limiting to the API endpoints"

## Workflow Execution

```
Agent: "Entering /develop for: Add rate limiting to API endpoints

✓ Check-In: MyApp | feature/rate-limit | clean

□ [UNDERSTAND]
  - Task: Add rate limiting to API endpoints
  - Scope: All routes in src/myapp/shell/api.py
  - Constraint: Must be configurable per-route
  - Existing: No rate limiting currently

□ [SPECIFY] RateLimiter class (Core)
  @pre(lambda max_requests, window_seconds: max_requests > 0 and window_seconds > 0)
  @post(lambda result: result is not None)
  def is_allowed(self, key: str) -> bool:
      '''
      >>> limiter = RateLimiter(max_requests=2, window_seconds=60)
      >>> limiter.is_allowed('user1')
      True
      >>> limiter.is_allowed('user1')
      True
      >>> limiter.is_allowed('user1')  # 3rd request
      False
      '''
      ...

□ [SPECIFY] rate_limit decorator (Shell)
  def rate_limit(max_requests: int, window_seconds: int):
      '''Decorator for Flask routes. Returns Result[Response, RateLimitError].'''
      ...

[BUILD - implementing RateLimiter...]
[BUILD - implementing decorator...]
[BUILD - applying to routes...]

□ [VALIDATE]
  - Guard: PASS (0 errors, 0 warnings)
  - Tests: All passing
  - Integration: Manual test with curl

✓ Final: guard PASS | 0 errors, 0 warnings

Development complete. Added rate limiting:
- Created: src/myapp/core/rate_limiter.py
- Modified: src/myapp/shell/api.py (decorator applied)
- Config: RATE_LIMIT_REQUESTS, RATE_LIMIT_WINDOW in .env"
```

## Key Points

1. **Check-In first** - Shows project, branch, git status (no guard/map here)
2. **UNDERSTAND visible** - Task scope and constraints clear
3. **SPECIFY visible** - Contracts shown BEFORE implementation
4. **BUILD hidden** - Internal work, not in checkpoints
5. **VALIDATE visible** - Guard results and integration status
6. **Final last** - Runs guard and completes the session

## When to Use

| Complexity | Use Visible Workflow? |
|------------|----------------------|
| 3+ functions | Yes |
| Architectural changes | Yes |
| New Core module | Yes |
| Single-line fix | No |
| Documentation only | No |
| Trivial refactoring | No |

---

*Example for the Invar Protocol v5.0*
