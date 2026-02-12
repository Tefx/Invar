from __future__ import annotations

import json
from unittest.mock import Mock

from invar.core.models import GuardReport, Severity, Violation
from invar.shell.guard_output import output_agent


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
