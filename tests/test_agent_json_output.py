"""Tests for agent JSON output, including DX-97 mutation output shape.

DX-97: Additive top-level mutation output for CLI/agent/MCP.
- eligible_files, ineligible_files, files_with_zero_sites counts
- bounded survivor_evidence (max 5 compact snippets)
- skipped_zero_sites distinct from true pass
- Mutation output must be absent when no mutation phase ran.
"""

from __future__ import annotations

import json
from unittest.mock import Mock

from invar.core.models import GuardReport, Severity, Violation
from invar.shell.guard_output import output_agent
from invar.shell.mutation import MutationAggregation


def test_output_agent_emits_parseable_json_without_rich_wrapping(monkeypatch, capsys) -> None:
    """Regression: `--agent` output must always be strict JSON.

    Reported failure mode: Rich Console wrapping inserts real newlines into JSON
    string literals, breaking json.loads().
    """

    report = GuardReport(files_checked=1)
    report.add_violation(
        Violation(
            rule="file_size_warning",
            severity=Severity.WARNING,
            file="src/x.py",
            line=None,
            message="File has 999 lines",
            suggestion=(
                "Consider splitting before reaching limit.\n"
                "Extractable groups:\n"
                "[A] one, two, three\n"
                "[B] four, five"
            ),
        )
    )

    # Guard against regressions: output_agent must not call Rich console.print.
    import invar.shell.guard_output as go

    monkeypatch.setattr(go, "console", Mock())
    go.console.print = Mock(side_effect=AssertionError("Rich console.print must not be used"))

    output_agent(report)
    out = capsys.readouterr().out
    json.loads(out)

    assert go.console.print.call_count == 0


def test_output_agent_mutation_fields_present_when_provided(monkeypatch, capsys) -> None:
    """DX-97: mutation top-level dict appears when mutation_output is provided."""
    import invar.shell.guard_output as go

    monkeypatch.setattr(go, "console", Mock())

    report = GuardReport(files_checked=3)
    agg = MutationAggregation(
        total=5,
        killed=3,  # 60% score → failed
        survived=2,
        eligible_files=3,
        ineligible_files=1,
        files_with_zero_sites=1,
        survivor_evidence=["foo.py:10:Add: x + y -> x - y"],
    )

    output_agent(report, mutation_output=agg)
    out = capsys.readouterr().out
    data = json.loads(out)

    assert "mutation" in data, "mutation key must be present when mutation_output provided"
    mut = data["mutation"]
    assert mut["total"] == 5
    assert mut["killed"] == 3
    assert mut["survived"] == 2
    assert mut["eligible_files"] == 3
    assert mut["ineligible_files"] == 1
    assert mut["files_with_zero_sites"] == 1
    assert mut["score"] == 60.0
    assert mut["passed"] is False  # 60% < 80% threshold
    assert len(mut["survivor_evidence"]) == 1


def test_output_agent_mutation_absent_when_not_provided(monkeypatch, capsys) -> None:
    """DX-97: mutation key must be absent when no mutation phase ran."""
    import invar.shell.guard_output as go

    monkeypatch.setattr(go, "console", Mock())

    report = GuardReport(files_checked=1)
    output_agent(report)
    out = capsys.readouterr().out
    data = json.loads(out)

    assert "mutation" not in data, "mutation key must be absent when mutation_output is None"


def test_output_agent_skipped_zero_sites_distinct_from_pass(monkeypatch, capsys) -> None:
    """DX-97: skipped_zero_sites must be distinguishable from a true pass.

    When all files have zero mutation sites, the score is 100.0 and passed is True,
    but skipped_zero_sites count shows those files were skipped, not genuinely passed.
    """
    import invar.shell.guard_output as go

    monkeypatch.setattr(go, "console", Mock())

    report = GuardReport(files_checked=2)
    agg = MutationAggregation(
        total=0,
        killed=0,
        survived=0,
        eligible_files=0,
        ineligible_files=0,
        files_with_zero_sites=2,
        survivor_evidence=[],
    )

    output_agent(report, mutation_output=agg)
    out = capsys.readouterr().out
    data = json.loads(out)

    mut = data["mutation"]
    assert mut["score"] == 100.0
    assert mut["passed"] is True
    assert mut["files_with_zero_sites"] == 2, (
        "files_with_zero_sites must be 2, not 0 — this distinguishes 'no sites to test' from 'all killed'"
    )


def test_output_agent_survivor_evidence_bounded(monkeypatch, capsys) -> None:
    """DX-97: survivor_evidence is bounded to 5 entries."""
    import invar.shell.guard_output as go

    monkeypatch.setattr(go, "console", Mock())

    report = GuardReport(files_checked=1)
    # 7 survivors but only 5 evidence entries
    evidence = [f"file{i}.py:10:Add: x + y -> x - y" for i in range(7)]
    agg = MutationAggregation(
        total=10,
        killed=3,
        survived=7,
        eligible_files=1,
        ineligible_files=0,
        files_with_zero_sites=0,
        survivor_evidence=evidence[:5],  # Already bounded by MutationAggregation
    )

    output_agent(report, mutation_output=agg)
    out = capsys.readouterr().out
    data = json.loads(out)

    mut = data["mutation"]
    assert len(mut["survivor_evidence"]) <= 5, "survivor_evidence must be bounded to 5"


def test_output_agent_mutation_error_phase(monkeypatch, capsys) -> None:
    """DX-97: mutation phase with errors still reports counts."""
    import invar.shell.guard_output as go

    monkeypatch.setattr(go, "console", Mock())

    report = GuardReport(files_checked=2)
    agg = MutationAggregation(
        total=3,
        killed=2,
        survived=0,
        timeout=1,
        error=0,
        eligible_files=2,
        ineligible_files=0,
        files_with_zero_sites=0,
        survivor_evidence=[],
    )

    output_agent(report, mutation_output=agg)
    out = capsys.readouterr().out
    data = json.loads(out)

    mut = data["mutation"]
    assert mut["timeout"] == 1
    assert mut["survived"] == 0
