from __future__ import annotations

from invar.core.models import FileInfo, RuleConfig
from invar.core.wiring_gap import check_wiring_gaps


def _mk_file(path: str, source: str) -> FileInfo:
    return FileInfo(path=path, lines=len(source.splitlines()), source=source, is_shell=True)


def test_detects_unpassed_optional_param_name_match() -> None:
    callee = _mk_file(
        "demo/shell/callee.py",
        "def build(payload='x'):\n    return payload\n",
    )
    caller = _mk_file(
        "demo/shell/caller.py",
        "from demo.shell.callee import build\n\n"
        "def run():\n"
        "    payload = 'ok'\n"
        "    return build()\n",
    )

    violations = check_wiring_gaps([callee, caller], RuleConfig())

    assert len(violations) == 1
    assert violations[0].rule == "wiring_gap"
    assert "payload" in violations[0].message


def test_skips_when_optional_param_explicitly_passed() -> None:
    callee = _mk_file(
        "demo/shell/callee.py",
        "def build(payload='x'):\n    return payload\n",
    )
    caller = _mk_file(
        "demo/shell/caller.py",
        "from demo.shell.callee import build\n\n"
        "def run():\n"
        "    payload = 'ok'\n"
        "    return build(payload=payload)\n",
    )

    assert check_wiring_gaps([callee, caller], RuleConfig()) == []


def test_verbose_mode_includes_match_context() -> None:
    callee = _mk_file(
        "demo/shell/callee.py",
        "def build(payload='x'):\n    return payload\n",
    )
    caller = _mk_file(
        "demo/shell/caller.py",
        "from demo.shell.callee import build\n\n"
        "def run():\n"
        "    payload = 'ok'\n"
        "    return build()\n",
    )

    violations = check_wiring_gaps([callee, caller], RuleConfig(), verbose=True)

    assert len(violations) == 1
    assert "locals_before_call=(payload)" in violations[0].message
    assert "optional_unpassed=(payload)" in violations[0].message
