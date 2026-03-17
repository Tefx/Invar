# P0 Migration Report: Current `@invar:allow` Inventory

## Scope and Method

- Scope: `src/invar/**/*.py` only (read-only inventory step).
- Command (as requested): `grep -rn '@invar:allow' src/invar/ --include='*.py'`.
- Parsing method for counting/classification: Python `tokenize` comment tokens with regex `@invar:allow <rule>: <reason>` to avoid counting non-comment string literals.

## Totals

- Total markers classified: **96**
- Exempt Candidate: **72**
- Ambiguous: **9**
- Should Fix: **15**

## Count by Rule

| Rule | Count |
|---|---:|
| `shell_result` | 43 |
| `dead_export` | 15 |
| `entry_point_too_thick` | 10 |
| `missing_contract` | 9 |
| `dead_assign` | 7 |
| `file_size` | 5 |
| `missing_doctest` | 4 |
| `shell_too_complex` | 2 |
| `shell_pure_logic` | 1 |

## Count by File

| File | Count |
|---|---:|
| `src/invar/mcp/handlers.py` | 25 |
| `src/invar/mcp/server.py` | 14 |
| `src/invar/mcp/guard_runs.py` | 9 |
| `src/invar/shell/commands/doc.py` | 6 |
| `src/invar/core/doc_parser.py` | 4 |
| `src/invar/core/hypothesis_strategies.py` | 4 |
| `src/invar/core/patterns/detector.py` | 4 |
| `src/invar/shell/templates.py` | 4 |
| `src/invar/shell/commands/guard.py` | 3 |
| `src/invar/shell/coverage.py` | 3 |
| `src/invar/core/template_parser.py` | 2 |
| `src/invar/shell/commands/merge.py` | 2 |
| `src/invar/shell/prove/accept.py` | 2 |
| `src/invar/shell/testing.py` | 2 |
| `src/invar/core/dead_assign.py` | 1 |
| `src/invar/core/models.py` | 1 |
| `src/invar/core/patterns/registry.py` | 1 |
| `src/invar/core/purity.py` | 1 |
| `src/invar/core/review_trigger.py` | 1 |
| `src/invar/core/rules.py` | 1 |
| `src/invar/core/shell_analysis.py` | 1 |
| `src/invar/core/timeout_inference.py` | 1 |
| `src/invar/core/verification_routing.py` | 1 |
| `src/invar/shell/config.py` | 1 |
| `src/invar/shell/guard_output.py` | 1 |
| `src/invar/shell/mcp_config.py` | 1 |

## Exempt-Candidate Groups and Proposed Patterns

### `shell_result`

- Count: **43**
- Proposed exempt patterns:
  - `src/invar/mcp/**/*.py::*`

### `dead_export`

- Count: **15**
- Proposed exempt patterns:
  - `src/invar/shell/**/*.py::*command*`
  - `src/invar/shell/**/*::main`
  - `src/invar/shell/{coverage,guard_output,mcp_config,testing,prove/accept}.py::*`

### `entry_point_too_thick`

- Count: **10**
- Proposed exempt patterns:
  - `src/invar/shell/commands/{doc,guard}.py::*`
  - `src/invar/shell/config.py::validate_config`

### `missing_doctest`

- Count: **4**
- Proposed exempt patterns:
  - `src/invar/core/patterns/detector.py::PatternDetector/{language,priority,supports_file,detect}`

## Full Marker Classification

| File | Line | Rule | Classification | Reason |
|---|---:|---|---|---|
| `src/invar/core/dead_assign.py` | 2 | `file_size` | should fix | AST walker stays explicit to keep rule behavior auditable. |
| `src/invar/core/doc_parser.py` | 7 | `file_size` | should fix | DX-77 Phase A adds Unicode fuzzy matching, extraction planned |
| `src/invar/core/doc_parser.py` | 282 | `dead_assign` | should fix | loop index read by next while iteration |
| `src/invar/core/doc_parser.py` | 283 | `dead_assign` | should fix | loop index read by next while iteration |
| `src/invar/core/doc_parser.py` | 378 | `dead_assign` | should fix | traversed in next for-iteration |
| `src/invar/core/hypothesis_strategies.py` | 7 | `file_size` | should fix | Strategy gen inherently complex, extraction increases coupling |
| `src/invar/core/hypothesis_strategies.py` | 28 | `missing_contract` | ambiguous | Boolean availability check, no meaningful contract |
| `src/invar/core/hypothesis_strategies.py` | 41 | `missing_contract` | ambiguous | Boolean availability check, no meaningful contract |
| `src/invar/core/hypothesis_strategies.py` | 460 | `dead_assign` | should fix | loop index consumed by next while condition |
| `src/invar/core/models.py` | 1 | `file_size` | should fix | LX-10 added layer types and functions, extraction planned |
| `src/invar/core/patterns/detector.py` | 30 | `missing_doctest` | exempt candidate | Abstract property - no executable implementation |
| `src/invar/core/patterns/detector.py` | 38 | `missing_doctest` | exempt candidate | Abstract property - no executable implementation |
| `src/invar/core/patterns/detector.py` | 46 | `missing_doctest` | exempt candidate | Abstract property - no executable implementation |
| `src/invar/core/patterns/detector.py` | 54 | `missing_doctest` | exempt candidate | Abstract method - no executable implementation |
| `src/invar/core/patterns/registry.py` | 42 | `missing_contract` | ambiguous | __init__ takes only self, no inputs to validate |
| `src/invar/core/purity.py` | 290 | `dead_assign` | should fix | loop-carried state read next iteration |
| `src/invar/core/review_trigger.py` | 144 | `missing_contract` | ambiguous | Boolean predicate, accepts empty string (doctest shows) |
| `src/invar/core/rules.py` | 1 | `file_size` | should fix | LX-10 added doctests, consider extraction later |
| `src/invar/core/shell_analysis.py` | 98 | `missing_contract` | ambiguous | Boolean predicate, empty string is valid input |
| `src/invar/core/template_parser.py` | 56 | `missing_contract` | ambiguous | Boolean derived from dict length |
| `src/invar/core/template_parser.py` | 279 | `missing_contract` | ambiguous | Boolean derived from state enum check |
| `src/invar/core/timeout_inference.py` | 102 | `missing_contract` | ambiguous | Boolean predicate, empty string is valid input |
| `src/invar/core/verification_routing.py` | 67 | `missing_contract` | ambiguous | Boolean predicate, empty string returns False |
| `src/invar/mcp/guard_runs.py` | 39 | `shell_result` | exempt candidate | Envelope helper returns dict for MCP error payload |
| `src/invar/mcp/guard_runs.py` | 68 | `shell_result` | exempt candidate | Timestamp helper for shell lifecycle metadata |
| `src/invar/mcp/guard_runs.py` | 73 | `shell_result` | exempt candidate | Timestamp formatting helper for shell lifecycle metadata |
| `src/invar/mcp/guard_runs.py` | 80 | `shell_result` | exempt candidate | Pure transformation helper used by MCP shell layer |
| `src/invar/mcp/guard_runs.py` | 115 | `shell_result` | exempt candidate | Parses subprocess JSON payload for shell orchestration |
| `src/invar/mcp/guard_runs.py` | 133 | `shell_result` | exempt candidate | Helper returns scalar boolean for summary output |
| `src/invar/mcp/guard_runs.py` | 151 | `shell_result` | exempt candidate | Converts guard payload to report dict for MCP output |
| `src/invar/mcp/guard_runs.py` | 194 | `shell_too_complex` | should fix | State lifecycle management needs branching |
| `src/invar/mcp/guard_runs.py` | 196 | `shell_result` | exempt candidate | MCP state registry does not expose Result[T, E] |
| `src/invar/mcp/handlers.py` | 29 | `shell_result` | exempt candidate | Pure validation helper, no I/O, returns tuple not Result |
| `src/invar/mcp/handlers.py` | 70 | `shell_result` | exempt candidate | MCP handler for guard tool |
| `src/invar/mcp/handlers.py` | 127 | `shell_result` | exempt candidate | MCP handler for guard status tool |
| `src/invar/mcp/handlers.py` | 140 | `shell_result` | exempt candidate | MCP handler for guard wait tool |
| `src/invar/mcp/handlers.py` | 164 | `shell_result` | exempt candidate | MCP handler for sig tool |
| `src/invar/mcp/handlers.py` | 182 | `shell_result` | exempt candidate | MCP handler for map tool |
| `src/invar/mcp/handlers.py` | 201 | `shell_result` | exempt candidate | MCP handler for refs tool |
| `src/invar/mcp/handlers.py` | 231 | `shell_result` | exempt candidate | MCP handler for doc_toc tool |
| `src/invar/mcp/handlers.py` | 261 | `shell_result` | exempt candidate | Pure data transformation, no I/O |
| `src/invar/mcp/handlers.py` | 279 | `shell_result` | exempt candidate | MCP handler for doc_read tool |
| `src/invar/mcp/handlers.py` | 308 | `shell_result` | exempt candidate | MCP handler for doc_read_many tool |
| `src/invar/mcp/handlers.py` | 340 | `shell_result` | exempt candidate | MCP handler for doc_find tool |
| `src/invar/mcp/handlers.py` | 384 | `shell_result` | exempt candidate | MCP handler for doc_replace tool |
| `src/invar/mcp/handlers.py` | 418 | `shell_result` | exempt candidate | MCP handler for doc_insert tool |
| `src/invar/mcp/handlers.py` | 458 | `shell_result` | exempt candidate | MCP handler for doc_delete tool |
| `src/invar/mcp/handlers.py` | 487 | `shell_result` | exempt candidate | MCP subprocess wrapper utility |
| `src/invar/mcp/handlers.py` | 543 | `shell_too_complex` | should fix | Simple state machine, 6 branches is minimal |
| `src/invar/mcp/handlers.py` | 544 | `shell_pure_logic` | should fix | No I/O, but called from shell context |
| `src/invar/mcp/handlers.py` | 545 | `shell_result` | exempt candidate | Pure transformation, returns str not Result |
| `src/invar/mcp/handlers.py` | 562 | `dead_assign` | should fix | loop index consumed by next while iteration |
| `src/invar/mcp/handlers.py` | 584 | `dead_assign` | should fix | loop index consumed by next while iteration |
| `src/invar/mcp/handlers.py` | 588 | `shell_result` | exempt candidate | Pure argument parsing helper for MCP |
| `src/invar/mcp/handlers.py` | 599 | `shell_result` | exempt candidate | Planner returns bool for handler branching |
| `src/invar/mcp/handlers.py` | 607 | `shell_result` | exempt candidate | Planner computes scalar estimate only |
| `src/invar/mcp/handlers.py` | 633 | `shell_result` | exempt candidate | Planner helper returns file count scalar |
| `src/invar/mcp/server.py` | 162 | `shell_result` | exempt candidate | MCP tool factory for guard command |
| `src/invar/mcp/server.py` | 209 | `shell_result` | exempt candidate | MCP tool factory for guard status command |
| `src/invar/mcp/server.py` | 233 | `shell_result` | exempt candidate | MCP tool factory for guard wait command |
| `src/invar/mcp/server.py` | 262 | `shell_result` | exempt candidate | MCP tool factory for sig command |
| `src/invar/mcp/server.py` | 284 | `shell_result` | exempt candidate | MCP tool factory for map command |
| `src/invar/mcp/server.py` | 306 | `shell_result` | exempt candidate | MCP tool factory for refs command |
| `src/invar/mcp/server.py` | 335 | `shell_result` | exempt candidate | MCP tool factory for doc_toc command |
| `src/invar/mcp/server.py` | 362 | `shell_result` | exempt candidate | MCP tool factory for doc_read command |
| `src/invar/mcp/server.py` | 392 | `shell_result` | exempt candidate | MCP tool factory for doc_read_many command |
| `src/invar/mcp/server.py` | 424 | `shell_result` | exempt candidate | MCP tool factory for doc_find command |
| `src/invar/mcp/server.py` | 455 | `shell_result` | exempt candidate | MCP tool factory for doc_replace command |
| `src/invar/mcp/server.py` | 489 | `shell_result` | exempt candidate | MCP tool factory for doc_insert command |
| `src/invar/mcp/server.py` | 524 | `shell_result` | exempt candidate | MCP tool factory for doc_delete command |
| `src/invar/mcp/server.py` | 549 | `shell_result` | exempt candidate | MCP framework API returns Server |
| `src/invar/shell/commands/doc.py` | 140 | `entry_point_too_thick` | exempt candidate | Multi-file glob + dual output format orchestration |
| `src/invar/shell/commands/doc.py` | 211 | `entry_point_too_thick` | exempt candidate | Section addressing + output format orchestration |
| `src/invar/shell/commands/doc.py` | 246 | `entry_point_too_thick` | exempt candidate | Multi-file glob + pattern/level filtering orchestration |
| `src/invar/shell/commands/doc.py` | 311 | `entry_point_too_thick` | exempt candidate | Content input + section replacement orchestration |
| `src/invar/shell/commands/doc.py` | 348 | `entry_point_too_thick` | exempt candidate | Content input + position-based insertion orchestration |
| `src/invar/shell/commands/doc.py` | 395 | `entry_point_too_thick` | exempt candidate | Section deletion with children handling |
| `src/invar/shell/commands/guard.py` | 185 | `entry_point_too_thick` | exempt candidate | Main CLI entry point, orchestrates all verification phases |
| `src/invar/shell/commands/guard.py` | 585 | `entry_point_too_thick` | exempt candidate | Python reference finding with examples |
| `src/invar/shell/commands/guard.py` | 606 | `entry_point_too_thick` | exempt candidate | Rules display with filtering and dual output modes |
| `src/invar/shell/commands/merge.py` | 63 | `dead_export` | exempt candidate | Public helper API exported for external integrations |
| `src/invar/shell/commands/merge.py` | 115 | `dead_export` | exempt candidate | Public helper API exported for external integrations |
| `src/invar/shell/config.py` | 533 | `entry_point_too_thick` | exempt candidate | False positive - .get() matches router.get pattern |
| `src/invar/shell/coverage.py` | 206 | `dead_export` | exempt candidate | Public helper API exported for external integrations |
| `src/invar/shell/coverage.py` | 265 | `dead_export` | exempt candidate | Public helper API exported for external integrations |
| `src/invar/shell/coverage.py` | 309 | `dead_export` | exempt candidate | Public helper API exported for external integrations |
| `src/invar/shell/guard_output.py` | 53 | `dead_export` | exempt candidate | Public helper API exported for external integrations |
| `src/invar/shell/mcp_config.py` | 120 | `dead_export` | exempt candidate | Public helper API exported for external integrations |
| `src/invar/shell/prove/accept.py` | 57 | `dead_export` | exempt candidate | Public helper API exported for external integrations |
| `src/invar/shell/prove/accept.py` | 102 | `dead_export` | exempt candidate | Public helper API exported for external integrations |
| `src/invar/shell/templates.py` | 154 | `dead_export` | exempt candidate | Typer CLI command registered at runtime via app.command() |
| `src/invar/shell/templates.py` | 181 | `dead_export` | exempt candidate | Typer CLI command registered at runtime via app.command() |
| `src/invar/shell/templates.py` | 212 | `dead_export` | exempt candidate | Typer CLI command registered at runtime via app.command() |
| `src/invar/shell/templates.py` | 247 | `dead_export` | exempt candidate | Typer CLI command registered at runtime via app.command() |
| `src/invar/shell/testing.py` | 85 | `dead_export` | exempt candidate | Public helper API used by external integrations |
| `src/invar/shell/testing.py` | 227 | `dead_export` | exempt candidate | Backward-compatible CLI helper invoked by external callers |
