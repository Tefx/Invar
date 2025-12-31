## Markers (TypeScript)

### Entry Points

Entry points are framework callbacks (Express routes, Next.js handlers) at Shell boundary.
- **Exempt** from `Result<T, E>` — must match framework signature
- **Keep thin** (max 15 lines) — delegate to Shell functions that return Result

For custom callbacks:

```typescript
// @shell:entry
export function onCustomEvent(data: Record<string, unknown>): Response {
  const result = handleEvent(data);
  if (result.isErr()) {
    return new Response(JSON.stringify({ error: result.error }), { status: 500 });
  }
  return new Response(JSON.stringify(result.value));
}
```

### Shell Complexity

When shell function complexity is justified:

```typescript
// @shell_complexity: External process with error classification
async function runExternalTool(...): Promise<Result<Output, Error>> { ... }

// @shell_orchestration: Multi-step pipeline coordination
async function processBatch(...): Promise<Result<BatchResult, Error>> { ... }
```

### Architecture Escape Hatch

When rule violation has valid architectural justification:

```typescript
// @invar:allow shell_result: Express middleware signature fixed
function expressMiddleware(req: Request, res: Response, next: NextFunction): void { ... }
```

**Valid rule names for @invar:allow:**
- `shell_result` — Shell function without Result return type
- `entry_point_too_thick` — Entry point exceeds 15 lines
- `forbidden_import` — I/O import in Core (rare, justify carefully)

Run `invar rules` for complete rule catalog with hints.
