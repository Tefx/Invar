"""
Review trigger detection for DX-30 Visible Workflow and DX-31 Independent Adversarial Reviewer.

DX-30: Contract quality ratio check (80% threshold)
DX-31: Independent review triggers (escape count, coverage, security)

Core module: pure logic, no I/O.
"""

from __future__ import annotations

import re

from deal import post, pre

from invar.core.entry_points import count_escape_hatches
from invar.core.models import FileInfo, RuleConfig, Severity, SymbolKind, Violation

# DX-31: Security-sensitive path patterns that trigger review suggestion
# Split into two groups to reduce false positives:

# Patterns safe to match as substrings (authentication, cryptography are valid matches)
SECURITY_SUBSTRING_PATTERNS: tuple[str, ...] = (
    "auth",       # authentication, authorize, authority
    "crypt",      # cryptography, encrypt, decrypt
    "secret",
    "password",
    "credential",
    "permission",
)

# Patterns that must be exact word matches (to avoid keyboard, tokenizer, accessory)
SECURITY_WORD_PATTERNS: tuple[str, ...] = (
    "token",      # not tokenizer
    "key",        # not keyboard, monkey
    "session",    # not obsession
    "access",     # not accessory
)


@post(lambda result: len(result) == 3 and 0.0 <= result[0] <= 1.0)  # Ratio in [0, 1]
def calculate_contract_ratio(file_info: FileInfo) -> tuple[float, int, int]:
    """
    Calculate contract coverage ratio for a file (DX-31).

    Returns (ratio, total_functions, with_contracts).
    Only counts public functions (not starting with _).

    Examples:
        >>> from invar.core.models import Contract, Symbol, SymbolKind
        >>> # No functions
        >>> empty = FileInfo(path="empty.py", lines=10)
        >>> calculate_contract_ratio(empty)
        (1.0, 0, 0)
        >>> # 100% coverage
        >>> c = Contract(kind="pre", expression="x > 0", line=1)
        >>> sym = Symbol(name="calc", kind=SymbolKind.FUNCTION, line=1, end_line=5, contracts=[c])
        >>> full = FileInfo(path="full.py", lines=10, symbols=[sym])
        >>> calculate_contract_ratio(full)
        (1.0, 1, 1)
        >>> # 0% coverage
        >>> sym_no = Symbol(name="calc", kind=SymbolKind.FUNCTION, line=1, end_line=5)
        >>> none = FileInfo(path="none.py", lines=10, symbols=[sym_no])
        >>> calculate_contract_ratio(none)
        (0.0, 1, 0)
        >>> # Private functions ignored
        >>> priv = Symbol(name="_helper", kind=SymbolKind.FUNCTION, line=1, end_line=5)
        >>> private_only = FileInfo(path="priv.py", lines=10, symbols=[priv])
        >>> calculate_contract_ratio(private_only)
        (1.0, 0, 0)
    """
    # Only check public functions (not starting with _)
    # MINOR-9: This excludes dunder methods (__init__, __str__, etc.) which is intentional.
    # Dunder methods are boilerplate; public API methods are the focus of contract coverage.
    functions = [
        s for s in file_info.symbols
        if s.kind in (SymbolKind.FUNCTION, SymbolKind.METHOD) and not s.name.startswith("_")
    ]

    if not functions:
        return (1.0, 0, 0)

    total = len(functions)
    with_contracts = sum(1 for f in functions if f.contracts)
    ratio = with_contracts / total

    return (ratio, total, with_contracts)


@post(lambda result: all(v.rule == "contract_quality_ratio" for v in result))
def check_contract_quality_ratio(file_info: FileInfo, config: RuleConfig) -> list[Violation]:
    """
    Check contract coverage ratio in Core files (DX-30).

    WARNING if less than 80% of public functions have @pre or @post.
    This encourages "Contract before Implement" workflow.

    Examples:
        >>> # Shell file - no check
        >>> shell_info = FileInfo(path="shell/cli.py", lines=50, is_shell=True)
        >>> check_contract_quality_ratio(shell_info, RuleConfig())
        []
        >>> # Core file with 100% coverage - pass
        >>> from invar.core.models import Contract, Symbol
        >>> c = Contract(kind="pre", expression="x > 0", line=1)
        >>> sym = Symbol(name="calc", kind=SymbolKind.FUNCTION, line=1, end_line=5, contracts=[c])
        >>> core_ok = FileInfo(path="core/calc.py", lines=50, symbols=[sym], is_core=True)
        >>> check_contract_quality_ratio(core_ok, RuleConfig())
        []
        >>> # Core file with 0% coverage - warning
        >>> sym_no = Symbol(name="calc", kind=SymbolKind.FUNCTION, line=1, end_line=5)
        >>> core_bad = FileInfo(path="core/calc.py", lines=50, symbols=[sym_no], is_core=True)
        >>> vs = check_contract_quality_ratio(core_bad, RuleConfig())
        >>> len(vs) == 1 and vs[0].rule == "contract_quality_ratio"
        True
    """
    violations: list[Violation] = []

    if not file_info.is_core:
        return violations

    ratio, total, with_contracts = calculate_contract_ratio(file_info)

    if total == 0:
        return violations

    if ratio < 0.8:
        pct = int(ratio * 100)
        violations.append(
            Violation(
                rule="contract_quality_ratio",
                severity=Severity.WARNING,
                file=file_info.path,
                line=None,
                message=f"Contract coverage: {pct}% ({with_contracts}/{total}). Target: 80%+",
                suggestion="Add @pre/@post to public functions. See INVAR.md 'Visible Workflow'",
            )
        )

    return violations


# @invar:allow missing_contract: Boolean predicate, accepts empty string (doctest shows)
def is_security_sensitive(path: str) -> bool:
    """
    Check if path indicates security-sensitive code (DX-31).

    Uses two-tier matching to reduce false positives:
    - Substring matching for unambiguous patterns (auth, crypt, secret, etc.)
    - Word-exact matching for ambiguous patterns (key, token, access, session)

    Examples:
        >>> # Substring patterns (auth, crypt, secret, password, credential, permission)
        >>> is_security_sensitive("src/auth/login.py")
        True
        >>> is_security_sensitive("src/authentication.py")
        True
        >>> is_security_sensitive("src/core/crypto.py")
        True
        >>> is_security_sensitive("src/utils/helpers.py")
        False

        >>> # Word-exact patterns (token, key, session, access)
        >>> is_security_sensitive("src/token_handler.py")
        True
        >>> is_security_sensitive("src/api_key.py")
        True
        >>> is_security_sensitive("src/access_control.py")
        True

        >>> # False positive prevention
        >>> is_security_sensitive("src/tokenizer.py")
        False
        >>> is_security_sensitive("src/keyboard.py")
        False
        >>> is_security_sensitive("src/monkey.py")
        False
        >>> is_security_sensitive("src/accessory.py")
        False
        >>> is_security_sensitive("src/hockey.py")
        False

        >>> # Edge cases
        >>> is_security_sensitive("")
        False
    """
    if not path:
        return False

    path_lower = path.lower()

    # Check substring patterns (safe, low false positive rate)
    if any(pattern in path_lower for pattern in SECURITY_SUBSTRING_PATTERNS):
        return True

    # Check word-exact patterns (split path into words first)
    words = re.split(r"[/_.\-\\]", path_lower)
    return any(word in SECURITY_WORD_PATTERNS for word in words)


@post(lambda result: all(v.rule == "review_suggested" for v in result))
def check_review_suggested(file_info: FileInfo, config: RuleConfig) -> list[Violation]:
    """
    Suggest independent review when conditions warrant (DX-31).

    Triggers review suggestion for Core files when:
    - escape_count >= 3: Multiple escape hatches indicate complexity
    - contract_ratio < 50%: Low contract coverage needs review
    - security-sensitive path: Security code needs extra scrutiny

    Examples:
        >>> from invar.core.models import Contract, Symbol, SymbolKind
        >>> # Shell file - no check
        >>> shell = FileInfo(path="shell/cli.py", lines=50, is_shell=True)
        >>> check_review_suggested(shell, RuleConfig())
        []
        >>> # Core file with no triggers - pass
        >>> c = Contract(kind="pre", expression="x > 0", line=1)
        >>> sym = Symbol(name="calc", kind=SymbolKind.FUNCTION, line=1, end_line=5, contracts=[c])
        >>> core_ok = FileInfo(path="core/calc.py", lines=50, symbols=[sym], is_core=True)
        >>> check_review_suggested(core_ok, RuleConfig())
        []
        >>> # Security-sensitive path - warning
        >>> auth = FileInfo(path="core/auth/login.py", lines=50, is_core=True, source="")
        >>> vs = check_review_suggested(auth, RuleConfig())
        >>> len(vs) == 1 and vs[0].rule == "review_suggested"
        True
        >>> # Low contract ratio - warning
        >>> sym_no = Symbol(name="calc", kind=SymbolKind.FUNCTION, line=1, end_line=5)
        >>> low = FileInfo(path="core/calc.py", lines=50, symbols=[sym_no], is_core=True)
        >>> vs = check_review_suggested(low, RuleConfig())
        >>> len(vs) == 1 and "contract" in vs[0].message.lower()
        True
        >>> # Multiple escape hatches - warning
        >>> source = '''
        ... # @invar:allow rule1: reason1
        ... # @invar:allow rule2: reason2
        ... # @invar:allow rule3: reason3
        ... '''
        >>> escapes = FileInfo(path="core/complex.py", lines=50, is_core=True, source=source, symbols=[sym])
        >>> vs = check_review_suggested(escapes, RuleConfig())
        >>> len(vs) == 1 and "escape" in vs[0].message.lower()
        True
    """
    violations: list[Violation] = []

    # Only check Core files
    if not file_info.is_core:
        return violations

    # Trigger 1: Security-sensitive path
    if is_security_sensitive(file_info.path):
        violations.append(
            Violation(
                rule="review_suggested",
                severity=Severity.WARNING,
                file=file_info.path,
                line=None,
                message=f"Security-sensitive file: {file_info.path}",
                suggestion="Consider independent /review before task completion",
            )
        )
        return violations  # Only one suggestion per file

    # Trigger 2: Multiple escape hatches (>= 3)
    source = file_info.source or ""
    escape_count = count_escape_hatches(source)
    if escape_count >= 3:
        violations.append(
            Violation(
                rule="review_suggested",
                severity=Severity.WARNING,
                file=file_info.path,
                line=None,
                message=f"High escape hatch count: {escape_count} @invar:allow markers",
                suggestion="Consider independent /review to validate escape justifications",
            )
        )
        return violations  # Only one suggestion per file

    # Trigger 3: Low contract ratio (< 50%)
    ratio, total, _ = calculate_contract_ratio(file_info)
    if total > 0 and ratio < 0.5:
        pct = int(ratio * 100)
        violations.append(
            Violation(
                rule="review_suggested",
                severity=Severity.WARNING,
                file=file_info.path,
                line=None,
                message=f"Low contract coverage: {pct}% (threshold: 50%)",
                suggestion="Add contracts, or request independent /review to assess quality",
            )
        )

    return violations


@pre(lambda escapes: all(len(e) == 3 for e in escapes))  # Validate tuple structure
@post(lambda result: all(v.rule == "duplicate_escape_reason" for v in result))
def check_duplicate_escape_reasons(
    escapes: list[tuple[str, str, str]],
) -> list[Violation]:
    """
    Detect duplicate escape hatch reasons across files (DX-33 Option E).

    Warns when 3+ files share identical escape reason text,
    suggesting a systematic issue that should be fixed at the root.

    Args:
        escapes: List of (file_path, rule, reason) tuples

    Returns:
        List of violations for duplicate reasons

    Examples:
        >>> check_duplicate_escape_reasons([])
        []
        >>> # 2 files with same reason - no warning (threshold is 3)
        >>> escapes = [
        ...     ("a.py", "rule", "same reason"),
        ...     ("b.py", "rule", "same reason"),
        ... ]
        >>> check_duplicate_escape_reasons(escapes)
        []
        >>> # 3+ files with same reason - warning
        >>> escapes = [
        ...     ("a.py", "rule", "False positive - .get()"),
        ...     ("b.py", "rule", "False positive - .get()"),
        ...     ("c.py", "rule", "False positive - .get()"),
        ... ]
        >>> vs = check_duplicate_escape_reasons(escapes)
        >>> len(vs) == 1
        True
        >>> "3 files" in vs[0].message
        True
        >>> "False positive" in vs[0].message
        True
    """
    violations: list[Violation] = []

    # Group by (reason) - normalize whitespace for comparison
    reason_files: dict[str, list[str]] = {}
    for file_path, _rule, reason in escapes:
        normalized = reason.strip().lower()
        if normalized not in reason_files:
            reason_files[normalized] = []
        reason_files[normalized].append(file_path)

    # Check for duplicates (threshold: 3+ files)
    for reason, files in reason_files.items():
        if len(files) >= 3:
            # Get original reason text from first occurrence
            original_reason = next(
                r for f, _, r in escapes if r.strip().lower() == reason
            )
            violations.append(
                Violation(
                    rule="duplicate_escape_reason",
                    severity=Severity.WARNING,
                    file="<project>",
                    line=None,
                    message=f'{len(files)} files share escape reason: "{original_reason}"',
                    suggestion="Consider fixing the detection rule instead of adding escapes. "
                    f"Files: {', '.join(sorted(set(files))[:5])}"
                    + (f" (+{len(files) - 5} more)" if len(files) > 5 else ""),
                )
            )

    return violations
