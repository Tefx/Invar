# Visible Workflow Example (TypeScript)

Complete example of USBV workflow with checkpoints for complex tasks.

## Scenario

User: "Add rate limiting to the API endpoints"

## Workflow Execution

```
Agent: "Entering /develop for: Add rate limiting to API endpoints

✓ Check-In: MyApp | feature/rate-limit | clean

□ [UNDERSTAND]
  - Task: Add rate limiting to API endpoints
  - Scope: All routes in src/myapp/shell/api.ts
  - Constraint: Must be configurable per-route
  - Existing: No rate limiting currently

□ [SPECIFY] RateLimiter class (Core)
  // Zod schema for constructor
  const RateLimiterConfig = z.object({
    maxRequests: z.number().positive(),
    windowSeconds: z.number().positive(),
  });

  /**
   * Check if request is allowed under rate limit.
   *
   * @example
   * const limiter = new RateLimiter({ maxRequests: 2, windowSeconds: 60 });
   * limiter.isAllowed('user1');  // => true
   * limiter.isAllowed('user1');  // => true
   * limiter.isAllowed('user1');  // => false (3rd request)
   */
  isAllowed(key: string): boolean { ... }

□ [SPECIFY] rateLimit middleware (Shell)
  /**
   * Express middleware for rate limiting.
   * Returns Result<void, RateLimitError>.
   */
  function rateLimit(config: RateLimiterConfig): RequestHandler { ... }

[BUILD - implementing RateLimiter...]
[BUILD - implementing middleware...]
[BUILD - applying to routes...]

□ [VALIDATE]
  - Guard: PASS (0 errors, 0 warnings)
  - Tests: All passing (vitest)
  - Integration: Manual test with curl

✓ Final: guard PASS | 0 errors, 0 warnings

Development complete. Added rate limiting:
- Created: src/myapp/core/rate-limiter.ts
- Modified: src/myapp/shell/api.ts (middleware applied)
- Config: RATE_LIMIT_REQUESTS, RATE_LIMIT_WINDOW in .env"
```

## Key Points

1. **Check-In first** - Shows project, branch, git status (no guard/map here)
2. **UNDERSTAND visible** - Task scope and constraints clear
3. **SPECIFY visible** - Zod schemas and JSDoc shown BEFORE implementation
4. **BUILD hidden** - Internal work, not in checkpoints
5. **VALIDATE visible** - Guard results and integration status
6. **Final last** - Runs guard and completes the session

## TypeScript Contract Patterns

| Pattern | Example |
|---------|---------|
| **Precondition** | `z.number().positive()` |
| **Postcondition** | Return type validation with Zod |
| **Examples** | JSDoc `@example` blocks |
| **Error handling** | `Result<T, E>` from neverthrow |

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

*Example for the Invar Protocol v5.0 (TypeScript)*
