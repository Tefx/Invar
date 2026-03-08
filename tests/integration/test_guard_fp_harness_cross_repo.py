"""Cross-repo guard false-positive harness fixtures.

These fixtures are self-contained reproductions of external symptoms observed in
../anima, ../tasca, and ../lattice. They intentionally use synthetic symbols and
inline source snippets so the harness never depends on sibling repositories at
runtime.

Mapping:
- redundant_type_contract -> malformed suggestion payload surface (`format_guard_agent`)
- shell_result + shell_pure_logic -> overlapping classification on MCP-style helpers
- dead_export -> runtime-registered/reflection-driven handler false positives
- duplicate_escape_reason -> count/list aggregation mismatch
- property-tests integration -> async RuntimeWarning surfacing in guard flow
"""

from __future__ import annotations

import warnings
from pathlib import Path

from invar.core.contracts import check_redundant_type_contracts
from invar.core.dead_param import check_dead_params
from invar.core.dead_export import check_dead_exports
from invar.core.formatter import format_guard_agent
from invar.core.models import Contract, FileInfo, GuardReport, RuleConfig, Symbol, SymbolKind
from invar.core.references import count_cross_file_references
from invar.core.review_trigger import check_duplicate_escape_reasons
from invar.core.rules import check_shell_result
from invar.core.shell_architecture import check_shell_pure_logic
from invar.shell.commands.guard import _scan_and_check
from invar.shell.guard_helpers import run_property_tests_phase


def test_redundant_type_contract_suggestion_payload_contains_unresolved_placeholder() -> None:
    """Verify malformed suggestion payload for redundant_type_contract is now fixed."""
    symbol = Symbol(
        name="collect",
        kind=SymbolKind.FUNCTION,
        line=1,
        end_line=6,
        signature="(x: int) -> list[Violation]",
        contracts=[Contract(kind="pre", expression="lambda x: isinstance(x, int)", line=1)],
    )
    file_info = FileInfo(path="core/collector.py", lines=10, is_core=True, symbols=[symbol])

    violations = check_redundant_type_contracts(file_info, RuleConfig())
    assert len(violations) == 1

    report = GuardReport(files_checked=1)
    report.add_violation(violations[0])
    payload = format_guard_agent(report)

    finding = payload["static"]["findings"][0]
    fix = finding["fix"]
    assert fix is not None
    assert fix["action"] == "replace_decorator"

    # Verify no unresolved placeholders remain
    code = fix["code"]
    assert "RULE_NAME" not in code, f"Found unresolved RULE_NAME in: {code}"
    assert "<predicate>" not in code, f"Found unresolved <predicate> in: {code}"
    assert "<type>" not in code, f"Found unresolved <type> in: {code}"
    assert "<semantic_predicate>" not in code, f"Found unresolved <semantic_predicate> in: {code}"
    assert "<condition>" not in code, f"Found unresolved <condition> in: {code}"

    # Verify actionable fix code is syntactically focused
    assert code.startswith("@pre("), f"Expected concrete decorator code, got: {code}"
    assert "\n" not in code, f"Fix code should be single-line actionable snippet: {code}"
    assert "or @" not in code, f"Fix code should not embed alternatives inline: {code}"

    context = fix.get("context")
    assert context is None or isinstance(context, str)


def test_mcp_style_helper_prefers_shell_result_without_overlap() -> None:
    """MCP-style helper should report shell_result without shell_pure_logic overlap."""
    source = """
def _run_guard(args: dict[str, object]) -> list[str]:
    content = []
    for key in args:
        if key.startswith("a"):
            content.append(key)
        else:
            content.append(key.upper())
    return content
""".lstrip()
    symbol = Symbol(
        name="_run_guard",
        kind=SymbolKind.FUNCTION,
        line=1,
        end_line=8,
        signature="(args: dict[str, object]) -> list[str]",
    )
    file_info = FileInfo(
        path="shell/mcp_helpers.py",
        lines=8,
        is_shell=True,
        symbols=[symbol],
        source=source,
    )

    shell_result = check_shell_result(file_info, RuleConfig())
    shell_pure_logic = check_shell_pure_logic(file_info, RuleConfig())

    assert len(shell_result) == 1
    assert shell_result[0].severity.value == "error"
    assert len(shell_pure_logic) == 0
    assert shell_result[0].rule == "shell_result"
    assert shell_result[0].line == 1


def test_shell_pure_logic_still_warns_for_non_result_none_return_helpers() -> None:
    """Control: shell_pure_logic still warns where shell_result does not apply."""
    source = """
def _normalize_payload(args: dict[str, object]) -> None:
    content = []
    for key in args:
        if key.startswith("a"):
            content.append(key)
        else:
            content.append(key.upper())
    _ = content
""".lstrip()
    symbol = Symbol(
        name="_normalize_payload",
        kind=SymbolKind.FUNCTION,
        line=1,
        end_line=8,
        signature="(args: dict[str, object]) -> None",
    )
    file_info = FileInfo(
        path="shell/mcp_helpers.py",
        lines=8,
        is_shell=True,
        symbols=[symbol],
        source=source,
    )

    shell_result = check_shell_result(file_info, RuleConfig())
    shell_pure_logic = check_shell_pure_logic(file_info, RuleConfig())

    assert shell_result == []
    assert len(shell_pure_logic) == 1
    assert shell_pure_logic[0].rule == "shell_pure_logic"
    assert shell_pure_logic[0].severity.value == "warning"


def test_dead_export_ignores_runtime_registered_handler_assignment() -> None:
    """Runtime registry assignment should count as a real caller for dead_export."""
    source = """
HANDLERS = {}

def on_ping(payload: str) -> str:
    return payload

HANDLERS["ping"] = on_ping
""".lstrip()
    symbol = Symbol(name="on_ping", kind=SymbolKind.FUNCTION, line=3, end_line=4)
    file_info = FileInfo(
        path="shell/runtime_registry.py",
        lines=6,
        symbols=[symbol],
        is_shell=True,
        source=source,
    )

    ref_counts = count_cross_file_references(
        [file_info],
        sources={"shell/runtime_registry.py": source},
        include_same_file=True,
    )

    violations = check_dead_exports([file_info], ref_counts=ref_counts, config=RuleConfig())

    assert violations == []


def test_dead_export_ignores_mcp_tool_decorated_handler() -> None:
    """Tasca-style @mcp.tool handlers should be treated as entry points."""
    source = """
@mcp.tool()
def table_wait(table_id: str) -> dict[str, object]:
    return {"ok": True}
""".lstrip()
    symbol = Symbol(name="table_wait", kind=SymbolKind.FUNCTION, line=2, end_line=3)
    file_info = FileInfo(
        path="shell/mcp_server.py",
        lines=3,
        symbols=[symbol],
        is_shell=True,
        source=source,
    )

    violations = check_dead_exports(
        [file_info],
        ref_counts={"shell/mcp_server.py::table_wait": 0},
        config=RuleConfig(),
    )

    assert violations == []


def test_dead_export_pipeline_handles_runtime_registration_and_control(tmp_path: Path) -> None:
    """Full guard static pipeline should suppress dynamic handlers but keep real dead exports."""
    project_root = tmp_path / "guard_fp_fixture"
    shell_dir = project_root / "shell"
    shell_dir.mkdir(parents=True)

    (shell_dir / "runtime_registry.py").write_text(
        """
HANDLERS = {}

def on_ping(payload: str) -> str:
    return payload

def truly_dead(payload: str) -> str:
    return payload

HANDLERS["ping"] = on_ping
""".lstrip(),
        encoding="utf-8",
    )

    result = _scan_and_check(project_root, RuleConfig())

    report = result.unwrap()
    dead_export_violations = [v for v in report.violations if v.rule == "dead_export"]
    messages = [v.message for v in dead_export_violations]

    assert all("on_ping" not in message for message in messages)
    assert any("truly_dead" in message for message in messages)


def test_dead_param_framework_handler_request_signature_is_exempt() -> None:
    """Framework-style request handler should not trigger dead_param."""
    source = """
class AgentServer:
    async def _handle_stream_request(self, request):
        return {"ok": True}
""".lstrip()
    file_info = FileInfo(path="shell/mcp_agent.py", lines=4, is_shell=True, source=source)

    violations = check_dead_params([file_info], RuleConfig())

    assert violations == []


def test_dead_param_non_framework_unused_request_still_reports() -> None:
    """Control case: non-framework unused request parameter is still reported."""
    source = """
def process_stream(request):
    return {"ok": True}
""".lstrip()
    file_info = FileInfo(path="shell/runtime.py", lines=2, is_shell=True, source=source)

    violations = check_dead_params([file_info], RuleConfig())

    assert len(violations) == 1
    assert violations[0].rule == "dead_param"
    assert "request" in violations[0].message


def test_duplicate_escape_reason_count_list_mismatch() -> None:
    """Reproduce mismatch between duplicate count and listed file set."""
    # 3 escape entries but only 2 unique files - should NOT trigger (needs 3+ unique files)
    escapes = [
        ("shell/a.py", "shell_result", "False positive - registry call"),
        ("shell/a.py", "shell_result", "False positive - registry call"),
        ("shell/b.py", "shell_result", "False positive - registry call"),
    ]

    violations = check_duplicate_escape_reasons(escapes)

    # With 2 unique files, should be no violation (threshold is 3+)
    assert len(violations) == 0

    # Test 3 unique files - should trigger correctly
    escapes3 = [
        ("shell/a.py", "shell_result", "False positive - registry call"),
        ("shell/b.py", "shell_result", "False positive - registry call"),
        ("shell/c.py", "shell_result", "False positive - registry call"),
    ]
    violations3 = check_duplicate_escape_reasons(escapes3)

    assert len(violations3) == 1
    violation = violations3[0]
    assert violation.rule == "duplicate_escape_reason"
    assert "3 files share escape reason" in violation.message
    assert "shell/a.py, shell/b.py, shell/c.py" in (violation.suggestion or "")


def test_property_phase_skips_async_functions_without_runtimewarning(tmp_path: Path) -> None:
    """Property phase skips async functions and avoids RuntimeWarning noise."""
    project_root = tmp_path / "proj"
    (project_root / "src" / "core").mkdir(parents=True)
    (project_root / "src" / "core" / "__init__.py").write_text("", encoding="utf-8")
    (project_root / "pyproject.toml").write_text(
        """
[project]
name = "tmp"
version = "0.0.0"

[tool.invar.guard]
core_paths = ["src/core"]
shell_paths = ["src/shell"]
""".lstrip(),
        encoding="utf-8",
    )
    core_file = project_root / "src" / "core" / "async_case.py"
    core_file.write_text(
        """
from deal import pre, post


@pre(lambda x: x >= 0)
@post(lambda result: True)
async def async_identity(x: int) -> int:
    return x
""".lstrip(),
        encoding="utf-8",
    )

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        passed, output, _coverage = run_property_tests_phase(
            project_root=project_root,
            checked_files=[core_file],
            doctest_passed=True,
            static_exit_code=0,
            max_examples=5,
        )

    assert passed is True
    assert output["status"] == "passed"
    assert output["functions_tested"] == 0
    assert output["functions_passed"] == 0
    assert output["total_examples"] == 0
    assert not any(
        isinstance(w.message, RuntimeWarning) and "was never awaited" in str(w.message)
        for w in caught
    )
