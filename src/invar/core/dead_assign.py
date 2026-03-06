"""Design note for dead_assign detection.

Step: dead-assign-design

Chosen approach:
    Use single-pass AST def-use tracking inside each function body.

Rationale:
    - The plan scope is explicitly limited to "single function only (no cross-function)".
    - A full def-use graph is unnecessary for first delivery and adds complexity for
      control-flow joins.
    - Existing core rules (for example dead_param) already use AST walk heuristics,
      so this keeps behavior predictable in guard.

Operational model for next step:
    1. Track writes (ast.Name with Store context) by variable name and line.
    2. Track reads (ast.Name with Load context) by variable name and line.
    3. A write is considered dead if there is no later read for the same variable name
       in the same function body traversal order.
    4. Ignore names that start with '_' to match existing warning suppression style.

Edge-case decisions:
    - Augmented assignment ("x += 1"):
      Treat as read+write; never report the write side of AugAssign as dead in the
      same node because the read proves value use.
    - Tuple unpacking ("a, b = expr"):
      Treat each element target as an independent write; report only elements never
      read later.
    - Conditional branches:
      Use conservative union semantics for first version. If any reachable branch
      contains a read after a write, do not report that write. This reduces false
      positives at the cost of some false negatives.

False-positive analysis (expected):
    - Minimized by conservative branch handling and AugAssign read+write semantics.
    - Remaining risk: path-insensitive ordering can still miss some "actually dead"
      writes (false negatives), which is acceptable for warning-level rule behavior.
"""
