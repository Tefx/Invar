from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path


def test_guard_reports_wiring_gap_in_static_json_output(tmp_path: Path) -> None:
    project_root = Path(__file__).resolve().parents[2]

    (tmp_path / "pyproject.toml").write_text('[project]\nname = "wg-fixture"\nversion = "0.1.0"\n')
    shell_dir = tmp_path / "src" / "demo" / "shell"
    shell_dir.mkdir(parents=True)

    (shell_dir / "callee.py").write_text("def build(payload='x'):\n    return payload\n")
    (shell_dir / "caller.py").write_text(
        "from demo.shell.callee import build\n\n"
        "def run():\n"
        "    payload = 'ok'\n"
        "    return build()\n"
    )

    env = os.environ.copy()
    env["INVAR_MODE"] = "agent"

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "invar.shell.commands.guard",
            "guard",
            str(tmp_path),
            "--all",
            "--static",
        ],
        capture_output=True,
        text=True,
        cwd=project_root,
        env=env,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)

    findings = payload["static"]["findings"]
    wiring_findings = [finding for finding in findings if finding["rule"] == "wiring_gap"]

    assert wiring_findings, payload
    assert wiring_findings[0]["file"].endswith("src/demo/shell/caller.py")
    assert "payload" in wiring_findings[0]["message"]
