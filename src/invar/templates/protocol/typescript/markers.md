## Markers (TypeScript)

### Entry Points

Entry points are framework callbacks (Express routes, Next.js handlers) at Shell boundary.
- **Exempt** from `Result<T, E>` — must match framework signature
- **Keep thin** — delegate to Shell functions that return Result
  - Traditional callbacks: max **15** lines (`entry_max_lines`)
  - MCP tool handlers: max **35** lines (`entry_point_thresholds["mcp_tool"]`)

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
- `entry_point_too_thick` — Entry point exceeds kind-specific limit (15 traditional / 35 MCP tool handlers)
- `forbidden_import` — I/O import in Core (rare, justify carefully)

Run `invar rules` for complete rule catalog with hints.
