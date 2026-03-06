"""dead_assign design specification (step: wiring-integrity-2.dead-assign-design).

Primary sources:
    - plan.yaml:wiring-integrity-2.dead-assign-design
    - plan.yaml verification text for dead-assign-design
    - src/invar/core/rule_meta.py dead_assign metadata and hint
    - Prior design commit: cceca32 (seed note reused and expanded here)

Scope strategy (v1)
===================
Decision:
    Analyze only function-local variables inside a single function body.

Why (source-linked):
    - plan.yaml explicitly requires "assigned but never read in the same scope" and
      verifies "function-local only for v1".
    - rule_meta detects "Local variable assigned but never read later in function".

In scope:
    - Assignments to local names in FunctionDef/AsyncFunctionDef/Lambda bodies.
    - Read/write tracking for those local names after assignment.

Out of scope for v1:
    - Module globals and cross-function propagation.
    - Class attribute/member flow (`self.x`, `cls.x`, attribute nodes).
    - Interprocedural use via closures, callbacks, decorators, dynamic exec/eval.

Data-flow model
===============
Decision:
    Use AST event collection per function with conservative path handling.

Operational contract for implementation step:
    1. Collect write events (`ast.Name` with Store context) with source locations.
    2. Collect read events (`ast.Name` with Load context) with source locations.
    3. Match each write to any reachable later read of the same local name.
    4. Emit warning only for writes with no later matched read.

This favors low false positives for a warning-level rule, accepting some false
negatives under complex control flow.

Augmented assignment handling
=============================
Decision:
    Treat `x += expr` (and other AugAssign forms) as read-then-write of `x`.

Rule:
    - The target read in AugAssign proves the previous value of `x` is used.
    - The new write from AugAssign can still be dead if no later read consumes it.
    - For non-name targets (`obj.x += 1`, `arr[i] += 1`), skip dead_assign in v1
      because target is not a function-local `Name` binding.

Unpacking handling
==================
Decision:
    Explode unpacking targets into independent local writes.

Rule:
    - `a, b = expr` -> writes: `a`, `b`.
    - Nested unpacking (`a, (b, c) = expr`) -> writes: `a`, `b`, `c`.
    - Star target (`a, *rest = expr`) -> writes: `a`, `rest`.
    - Each target name is judged independently for later reads.

Control-flow / if-else handling
===============================
Decision:
    Use conservative branch merge semantics for v1.

Rule:
    - A write is considered live if any reachable branch path has a later read.
    - If no branch has a later read, report as dead.
    - This intentionally avoids aggressive path-sensitive proof to keep runtime
      predictable and avoid noisy warnings.

Examples:
    - `if cond: x = 1; print(x)` -> not dead.
    - `if cond: x = 1; else: x = 2; return 0` -> both writes dead.

Exemption list (v1)
===================
The checker should skip/report-suppress these by design:
    1. Names starting with `_` (throwaway intent convention).
    2. Explicit rule suppression comment:
       `# @invar:allow dead_assign: <reason>` (per rule_meta hint).
    3. Non-local targets (attributes/subscripts) in assignment nodes.
    4. Imports/aliases (`import x as y`) and pattern-match bindings for now
       unless the implementation step explicitly opts in.

Deliverables status
===================
This document now finalizes the dead_assign design for:
    - scope strategy (function-local v1)
    - augmented assignment behavior
    - unpacking behavior
    - control-flow (if/else) behavior
    - explicit exemption list
"""
