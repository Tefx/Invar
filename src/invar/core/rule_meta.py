"""
Centralized rule metadata for Guard rules.

Phase 9.2 P3: Single source of truth for rule information.
Used by: hints (P5), --agent output, invar rules command.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from deal import post

from invar.core.models import Severity


class RuleCategory(str, Enum):
    """Categories for grouping rules."""

    SIZE = "size"
    CONTRACTS = "contracts"
    PURITY = "purity"
    SHELL = "shell"
    DOCS = "docs"


@dataclass(frozen=True)
class RuleMeta:
    """
    Metadata for a Guard rule.

    Examples:
        >>> meta = RULE_META["file_size"]
        >>> meta.category
        <RuleCategory.SIZE: 'size'>
        >>> "Split" in meta.hint
        True
    """

    name: str
    severity: Severity
    category: RuleCategory
    detects: str
    cannot_detect: tuple[str, ...]
    hint: str


# All rule metadata definitions
RULE_META: dict[str, RuleMeta] = {
    # Size rules
    "file_size": RuleMeta(
        name="file_size",
        severity=Severity.ERROR,
        category=RuleCategory.SIZE,
        detects="File exceeds max_file_lines limit",
        cannot_detect=("Code complexity", "Logical cohesion", "Coupling between modules"),
        hint="Split into smaller modules by responsibility",
    ),
    "file_size_warning": RuleMeta(
        name="file_size_warning",
        severity=Severity.WARNING,
        category=RuleCategory.SIZE,
        detects="File approaching max_file_lines limit (80% threshold)",
        cannot_detect=("Whether split is actually needed",),
        hint="Consider splitting before reaching limit",
    ),
    "function_size": RuleMeta(
        name="function_size",
        severity=Severity.WARNING,
        category=RuleCategory.SIZE,
        detects="Function exceeds max_function_lines limit",
        cannot_detect=("Algorithm complexity", "Whether extraction helps readability"),
        hint="Extract helper functions or simplify logic",
    ),
    # Contract rules
    "missing_contract": RuleMeta(
        name="missing_contract",
        severity=Severity.ERROR,
        category=RuleCategory.CONTRACTS,
        detects="Core function without @pre or @post decorator",
        cannot_detect=("Contract quality", "Whether contract is meaningful"),
        hint="Ask: what inputs are invalid? what does output guarantee?",
    ),
    "empty_contract": RuleMeta(
        name="empty_contract",
        severity=Severity.ERROR,
        category=RuleCategory.CONTRACTS,
        detects="Contract with tautology like @pre(lambda: True)",
        cannot_detect=("Subtle tautologies", "Semantic correctness"),
        hint="Replace lambda: True with actual constraint on inputs/output",
    ),
    "redundant_type_contract": RuleMeta(
        name="redundant_type_contract",
        severity=Severity.INFO,
        category=RuleCategory.CONTRACTS,
        detects="Contract only checks types already in annotations",
        cannot_detect=("Whether better constraints exist",),
        hint="Add value constraints beyond type checks if possible",
    ),
    "param_mismatch": RuleMeta(
        name="param_mismatch",
        severity=Severity.ERROR,
        category=RuleCategory.CONTRACTS,
        detects="@pre lambda parameters don't match function signature",
        cannot_detect=("Runtime binding errors",),
        hint="Lambda must accept ALL function parameters (include defaults like x=10)",
    ),
    "postcondition_scope_error": RuleMeta(
        name="postcondition_scope_error",
        severity=Severity.ERROR,
        category=RuleCategory.CONTRACTS,
        detects="@post lambda references function parameters (not available in postcondition)",
        cannot_detect=("Indirect parameter access via closures",),
        hint="@post can only use 'result', not function parameters like x, y",
    ),
    "must_use_ignored": RuleMeta(
        name="must_use_ignored",
        severity=Severity.WARNING,
        category=RuleCategory.CONTRACTS,
        detects="Return value of @must_use function is ignored",
        cannot_detect=("Cross-module must_use", "Dynamic function references"),
        hint="Assign or use the return value - it may contain errors or resources",
    ),
    # Purity rules
    "forbidden_import": RuleMeta(
        name="forbidden_import",
        severity=Severity.ERROR,
        category=RuleCategory.PURITY,
        detects="Core module imports I/O libraries (os, sys, pathlib, etc.)",
        cannot_detect=("Transitive imports", "Dynamic imports"),
        hint="Move I/O operations to Shell layer",
    ),
    "internal_import": RuleMeta(
        name="internal_import",
        severity=Severity.WARNING,
        category=RuleCategory.PURITY,
        detects="Import statement inside function body",
        cannot_detect=("Lazy imports for performance", "Circular import workarounds"),
        hint="Move import to module top-level or justify with comment",
    ),
    "impure_call": RuleMeta(
        name="impure_call",
        severity=Severity.ERROR,
        category=RuleCategory.PURITY,
        detects="Call to impure function (datetime.now, random.*, print, open)",
        cannot_detect=("Custom impure functions", "Impurity via method calls"),
        hint="Inject impure values as parameters or move to Shell",
    ),
    # Shell rules
    "shell_result": RuleMeta(
        name="shell_result",
        severity=Severity.ERROR,  # DX-22: Architecture rule, must fix or explain
        category=RuleCategory.SHELL,
        detects="Shell function not returning Result[T, E]",
        cannot_detect=("Result usage correctness", "Error handling quality"),
        hint="Wrap with Success()/Failure(), or add: # @invar:allow shell_result: <reason>",
    ),
    "entry_point_too_thick": RuleMeta(
        name="entry_point_too_thick",
        severity=Severity.ERROR,  # DX-22: Architecture rule, must fix or explain
        category=RuleCategory.SHELL,
        detects="Entry point (Flask route, Typer command, etc.) exceeds max lines",
        cannot_detect=("Whether complexity is unavoidable", "Framework constraints"),
        hint="Move logic to Shell function, or add: # @invar:allow entry_point_too_thick: <reason>",
    ),
    "shell_pure_logic": RuleMeta(
        name="shell_pure_logic",
        severity=Severity.WARNING,
        category=RuleCategory.SHELL,
        detects="Shell function with no I/O operations (pure logic belongs in Core)",
        cannot_detect=("Indirect I/O via method calls", "Framework-specific patterns"),
        hint="Move to Core layer and add @pre/@post contracts, or add: # @shell_orchestration: <reason>",
    ),
    "shell_too_complex": RuleMeta(
        name="shell_too_complex",
        severity=Severity.INFO,
        category=RuleCategory.SHELL,
        detects="Shell function with excessive branching complexity",
        cannot_detect=("Whether complexity is justified", "Domain-specific patterns"),
        hint="Extract logic to Core, or add: # @shell_complexity: <reason>",
    ),
    "shell_complexity_debt": RuleMeta(
        name="shell_complexity_debt",
        severity=Severity.ERROR,
        category=RuleCategory.SHELL,
        detects="Project accumulated too many unaddressed complexity warnings (DX-22 Fix-or-Explain)",
        cannot_detect=("Individual function justifications",),
        hint="Address shell_too_complex warnings: refactor OR add @shell_complexity: markers",
    ),
    # Documentation rules
    "missing_doctest": RuleMeta(
        name="missing_doctest",
        severity=Severity.WARNING,
        category=RuleCategory.DOCS,
        detects="Core function without doctest examples",
        cannot_detect=("Doctest quality", "Edge case coverage"),
        hint="Add >>> examples showing typical usage and edge cases",
    ),
    # DX-28: Skip abuse prevention
    "skip_without_reason": RuleMeta(
        name="skip_without_reason",
        severity=Severity.WARNING,
        category=RuleCategory.CONTRACTS,
        detects="@skip_property_test used without justification reason",
        cannot_detect=("Whether the reason is valid", "Skip abuse patterns"),
        hint='Add reason: @skip_property_test("category: explanation")',
    ),
    # DX-30: Contract coverage ratio
    "contract_quality_ratio": RuleMeta(
        name="contract_quality_ratio",
        severity=Severity.WARNING,
        category=RuleCategory.CONTRACTS,
        detects="Core file with less than 80% contract coverage on public functions",
        cannot_detect=("Contract quality", "Whether contracts are meaningful"),
        hint="Add @pre/@post to public functions. Use Phase TodoList for complex tasks",
    ),
    # DX-31: Review suggestion trigger
    "review_suggested": RuleMeta(
        name="review_suggested",
        severity=Severity.WARNING,
        category=RuleCategory.DOCS,
        detects="Conditions warranting independent code review (escape count, coverage, security)",
        cannot_detect=("Whether review was performed", "Review quality"),
        hint="Consider independent /review sub-agent before task completion",
    ),
}


@post(lambda result: result is None or isinstance(result, RuleMeta))
def get_rule_meta(rule_name: str) -> RuleMeta | None:
    """
    Get metadata for a rule by name.

    Examples:
        >>> meta = get_rule_meta("file_size")
        >>> meta is not None
        True
        >>> get_rule_meta("nonexistent") is None
        True
    """
    return RULE_META.get(rule_name)


@post(lambda result: len(result) > 0)
def get_all_rule_names() -> list[str]:
    """
    Get list of all rule names.

    Examples:
        >>> names = get_all_rule_names()
        >>> "file_size" in names
        True
        >>> len(names) >= 10
        True
    """
    return list(RULE_META.keys())


@post(lambda result: isinstance(result, list))
def get_rules_by_category(category: RuleCategory) -> list[RuleMeta]:
    """
    Get all rules in a category.

    Examples:
        >>> size_rules = get_rules_by_category(RuleCategory.SIZE)
        >>> len(size_rules) >= 2
        True
    """
    return [meta for meta in RULE_META.values() if meta.category == category]
