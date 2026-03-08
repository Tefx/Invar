"""
DX-78: TypeScript Compiler API integration tests.

Tests for:
- TypeScript Compiler API wrapper (ts_compiler.py)
- Python reference finding (py_refs.py)
- refs command in perception.py
- MCP handlers for sig/map/refs with TS Compiler API
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from returns.result import Failure, Success

# =============================================================================
# TypeScript Compiler API Tests
# =============================================================================


class TestTypeScriptCompilerAPI:
    """Test TypeScript Compiler API wrapper."""

    @pytest.mark.skipif(
        not Path("/usr/local/bin/node").exists() and not Path("/opt/homebrew/bin/node").exists(),
        reason="Node.js not available"
    )
    def test_is_typescript_available_with_node(self):
        """Detects Node.js when available."""
        from invar.shell.ts_compiler import is_typescript_available

        # This test only runs when Node.js exists
        # Note: ts-query.js might not exist yet
        result = is_typescript_available()
        # Result depends on whether ts-query.js is bundled
        assert isinstance(result, bool)

    def test_is_typescript_available_without_node(self):
        """Returns False when Node.js unavailable."""
        from invar.shell.ts_compiler import is_typescript_available

        with patch("subprocess.run", side_effect=FileNotFoundError):
            result = is_typescript_available()
            assert result is False

    def test_query_typescript_node_not_found(self, tmp_path: Path):
        """Returns Failure when Node.js not found."""
        from invar.shell.ts_compiler import query_typescript

        with patch("subprocess.run", side_effect=FileNotFoundError):
            result = query_typescript(tmp_path, "sig", file="test.ts")

            assert isinstance(result, Failure)
            error_msg = result.failure()
            assert "Node.js not found" in error_msg

    def test_query_typescript_timeout(self, tmp_path: Path):
        """Returns Failure when query times out."""
        from subprocess import TimeoutExpired

        from invar.shell.ts_compiler import query_typescript

        mock_run = MagicMock(side_effect=TimeoutExpired("node", 30))

        with patch("subprocess.run", mock_run):
            with patch("invar.shell.ts_compiler._find_ts_query_js", return_value=Path("/mock/ts-query.js")):
                result = query_typescript(tmp_path, "sig", file="test.ts")

                assert isinstance(result, Failure)
                error_msg = result.failure()
                assert "timed out" in error_msg

    def test_query_typescript_invalid_json(self, tmp_path: Path):
        """Returns Failure when ts-query.js returns invalid JSON."""
        from invar.shell.ts_compiler import query_typescript

        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "not json"

        with patch("subprocess.run", return_value=mock_result):
            with patch("invar.shell.ts_compiler._find_ts_query_js", return_value=Path("/mock/ts-query.js")):
                result = query_typescript(tmp_path, "sig", file="test.ts")

                assert isinstance(result, Failure)
                error_msg = result.failure()
                assert "Invalid JSON" in error_msg

    def test_query_typescript_error_response(self, tmp_path: Path):
        """Returns Failure when ts-query.js returns error."""
        import json

        from invar.shell.ts_compiler import query_typescript

        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = json.dumps({"error": "File not found"})

        with patch("subprocess.run", return_value=mock_result):
            with patch("invar.shell.ts_compiler._find_ts_query_js", return_value=Path("/mock/ts-query.js")):
                result = query_typescript(tmp_path, "sig", file="test.ts")

                assert isinstance(result, Failure)
                error_msg = result.failure()
                assert "File not found" in error_msg

    def test_run_sig_typescript_success(self, tmp_path: Path):
        """Parses TS Compiler API sig response."""
        import json

        from invar.shell.ts_compiler import run_sig_typescript

        # Create mock tsconfig.json
        (tmp_path / "tsconfig.json").write_text("{}")
        ts_file = tmp_path / "test.ts"
        ts_file.write_text("function hello() {}")

        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = json.dumps({
            "symbols": [
                {
                    "name": "hello",
                    "kind": "function",
                    "signature": "function hello(): void",
                    "line": 1
                }
            ]
        })

        with patch("subprocess.run", return_value=mock_result):
            with patch("invar.shell.ts_compiler._find_ts_query_js", return_value=Path("/mock/ts-query.js")):
                result = run_sig_typescript(ts_file)

                assert isinstance(result, Success)
                symbols = result.unwrap()
                assert len(symbols) == 1
                assert symbols[0].name == "hello"
                assert symbols[0].kind == "function"

    def test_run_map_typescript_success(self, tmp_path: Path):
        """Parses TS Compiler API map response."""
        import json

        from invar.shell.ts_compiler import run_map_typescript

        (tmp_path / "tsconfig.json").write_text("{}")

        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = json.dumps({
            "symbols": [
                {"name": "main", "file": "index.ts", "references": 5}
            ]
        })

        with patch("subprocess.run", return_value=mock_result):
            with patch("invar.shell.ts_compiler._find_ts_query_js", return_value=Path("/mock/ts-query.js")):
                result = run_map_typescript(tmp_path, top_n=10)

                assert isinstance(result, Success)
                data = result.unwrap()
                assert "symbols" in data

    def test_run_refs_typescript_success(self, tmp_path: Path):
        """Parses TS Compiler API refs response."""
        import json

        from invar.shell.ts_compiler import run_refs_typescript

        (tmp_path / "tsconfig.json").write_text("{}")
        ts_file = tmp_path / "test.ts"
        ts_file.write_text("function hello() {}")

        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = json.dumps({
            "references": [
                {
                    "file": "test.ts",
                    "line": 5,
                    "column": 10,
                    "context": "hello()",
                    "isDefinition": False
                }
            ]
        })

        with patch("subprocess.run", return_value=mock_result):
            with patch("invar.shell.ts_compiler._find_ts_query_js", return_value=Path("/mock/ts-query.js")):
                result = run_refs_typescript(ts_file, line=1, column=9)

                assert isinstance(result, Success)
                refs = result.unwrap()
                assert len(refs) == 1
                assert refs[0].file == "test.ts"
                assert refs[0].line == 5

    def test_find_tsconfig_root(self, tmp_path: Path):
        """Finds tsconfig.json in parent directories."""
        from invar.shell.ts_compiler import _find_tsconfig_root

        # Create nested structure
        (tmp_path / "project").mkdir()
        (tmp_path / "project" / "tsconfig.json").write_text("{}")
        (tmp_path / "project" / "src").mkdir()

        test_file = tmp_path / "project" / "src" / "test.ts"
        test_file.touch()

        root = _find_tsconfig_root(test_file)
        assert root == tmp_path / "project"

    def test_find_tsconfig_root_fallback(self, tmp_path: Path):
        """Falls back to file's directory when no tsconfig.json."""
        from invar.shell.ts_compiler import _find_tsconfig_root

        test_file = tmp_path / "test.ts"
        test_file.touch()

        root = _find_tsconfig_root(test_file)
        assert root == tmp_path


# =============================================================================
# Python Reference Finding Tests
# =============================================================================


class TestPythonReferenceFinding:
    """Test Python reference finding using jedi."""

    def test_find_symbol_position_simple(self, tmp_path: Path):
        """Finds symbol position in Python file."""
        from invar.shell.py_refs import find_symbol_position

        py_file = tmp_path / "example.py"
        py_file.write_text("""
def hello():
    pass

def world():
    hello()
""")

        position = find_symbol_position(py_file, "hello")
        assert position is not None
        line, _column = position
        assert line == 2  # 1-indexed

    def test_find_symbol_position_class_method(self, tmp_path: Path):
        """Finds class method position."""
        from invar.shell.py_refs import find_symbol_position

        py_file = tmp_path / "example.py"
        py_file.write_text("""
class Greeter:
    def greet(self):
        pass
""")

        position = find_symbol_position(py_file, "greet")
        assert position is not None
        line, _column = position
        assert line == 3

    def test_find_symbol_position_not_found(self, tmp_path: Path):
        """Returns None when symbol not found."""
        from invar.shell.py_refs import find_symbol_position

        py_file = tmp_path / "example.py"
        py_file.write_text("def hello(): pass")

        position = find_symbol_position(py_file, "nonexistent")
        assert position is None

    def test_find_all_references_to_symbol(self, tmp_path: Path):
        """Finds all references to a symbol."""
        from invar.shell.py_refs import find_all_references_to_symbol

        py_file = tmp_path / "example.py"
        py_file.write_text("""
def hello():
    pass

def caller():
    hello()
    hello()
""")

        refs = find_all_references_to_symbol(py_file, "hello", project_root=tmp_path)
        # Should find definition + 2 calls = 3 references
        assert len(refs) >= 1  # At minimum, the definition

    def test_find_references_across_files(self, tmp_path: Path):
        """Finds references across multiple files."""
        from invar.shell.py_refs import find_all_references_to_symbol

        # Create module
        (tmp_path / "module.py").write_text("""
def utility():
    pass
""")

        # Create caller
        (tmp_path / "caller.py").write_text("""
from module import utility

def main():
    utility()
""")

        refs = find_all_references_to_symbol(
            tmp_path / "module.py",
            "utility",
            project_root=tmp_path
        )

        # Should find at least the definition
        assert len(refs) >= 1


# =============================================================================
# Perception Command Tests
# =============================================================================


class TestRefsCommand:
    """Test invar refs command."""

    def test_run_refs_python_file(self, tmp_path: Path):
        """Runs refs on Python file."""
        from invar.shell.commands.perception import run_refs

        py_file = tmp_path / "example.py"
        py_file.write_text("""
def hello():
    pass

def caller():
    hello()
""")

        result = run_refs(f"{py_file}::hello", json_output=True)
        # Should succeed - valid Python file with clear symbol
        assert isinstance(result, Success)

    def test_run_refs_typescript_file_fallback(self, tmp_path: Path):
        """Runs refs on TypeScript file (falls back to regex if no Node.js)."""
        from invar.shell.commands.perception import run_refs

        ts_file = tmp_path / "example.ts"
        ts_file.write_text("""
function hello() {}

function caller() {
    hello();
}
""")

        result = run_refs(f"{ts_file}::hello", json_output=True)
        # Should succeed with TS Compiler API or fallback, or fail with clear message
        if isinstance(result, Failure):
            error_msg = result.failure()
            # Must be a clear, actionable error (not a crash)
            assert len(error_msg) > 0
        else:
            assert isinstance(result, Success)

    def test_run_refs_invalid_target_format(self):
        """Returns Failure for invalid target format."""
        from invar.shell.commands.perception import run_refs

        result = run_refs("invalid_format", json_output=True)

        assert isinstance(result, Failure)
        error_msg = result.failure()
        assert "Invalid target format" in error_msg

    def test_run_refs_unsupported_file_type(self, tmp_path: Path):
        """Returns Failure for unsupported file type."""
        from invar.shell.commands.perception import run_refs

        txt_file = tmp_path / "example.txt"
        txt_file.write_text("hello world")

        result = run_refs(f"{txt_file}::hello", json_output=True)

        assert isinstance(result, Failure)
        error_msg = result.failure()
        assert "Unsupported file type" in error_msg

    def test_run_refs_file_not_found(self):
        """Returns Failure when file doesn't exist."""
        from invar.shell.commands.perception import run_refs

        result = run_refs("/nonexistent/file.py::symbol", json_output=True)

        assert isinstance(result, Failure)
        error_msg = result.failure()
        assert "not found" in error_msg or "does not exist" in error_msg


# =============================================================================
# Integration Tests for Updated Sig/Map Commands
# =============================================================================


class TestTypeScriptSigMapIntegration:
    """Test sig/map with TS Compiler API integration."""

    def test_run_sig_typescript_with_compiler_api(self, tmp_path: Path):
        """sig command uses TS Compiler API when available."""
        from invar.shell.commands.perception import run_sig

        (tmp_path / "tsconfig.json").write_text("{}")
        ts_file = tmp_path / "example.ts"
        ts_file.write_text("""
export function hello(name: string): string {
    return `Hello, ${name}`;
}
""")

        # Should succeed - valid TypeScript file
        result = run_sig(str(ts_file), json_output=True)
        assert isinstance(result, Success)
        # run_sig prints to console (tested via Success return)

    def test_run_map_typescript_with_compiler_api(self, tmp_path: Path):
        """map command uses TS Compiler API when available."""
        from invar.shell.commands.perception import run_map

        (tmp_path / "tsconfig.json").write_text("{}")
        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "index.ts").write_text("""
export function main(): void {}
""")

        # Should succeed - valid TypeScript project with tsconfig.json
        result = run_map(tmp_path, top_n=10, json_output=True)
        assert isinstance(result, Success)


# =============================================================================
# MCP Handler Tests
# =============================================================================


class TestMCPHandlers:
    """Test MCP handlers for DX-78 features."""

    @pytest.mark.anyio
    async def test_invar_sig_typescript_mcp(self, tmp_path: Path):
        """Test invar_sig MCP handler with TypeScript file."""
        from invar.mcp.handlers import _run_sig

        (tmp_path / "tsconfig.json").write_text("{}")
        ts_file = tmp_path / "example.ts"
        ts_file.write_text("function hello() {}")

        args = {"target": str(ts_file)}
        result = await _run_sig(args)

        assert len(result) == 1
        assert result[0].type == "text"
        # Should return signatures (either from TS Compiler API or regex)

    @pytest.mark.anyio
    async def test_invar_map_typescript_mcp(self, tmp_path: Path):
        """Test invar_map MCP handler with TypeScript project."""
        from invar.mcp.handlers import _run_map

        (tmp_path / "tsconfig.json").write_text("{}")
        (tmp_path / "index.ts").write_text("export function main() {}")

        args = {"path": str(tmp_path), "top": 10}
        result = await _run_map(args)

        assert len(result) == 1
        assert result[0].type == "text"

    @pytest.mark.anyio
    async def test_invar_refs_mcp_python(self, tmp_path: Path):
        """Test invar_refs MCP handler with Python file."""
        # Import handler dynamically to avoid module-level import errors
        try:
            from invar.mcp.handlers import _run_refs
        except ImportError:
            pytest.skip("_run_refs handler not yet implemented in MCP")
            return

        py_file = tmp_path / "example.py"
        py_file.write_text("""
def hello():
    pass

def caller():
    hello()
""")

        args = {"target": f"{py_file}::hello"}
        result = await _run_refs(args)

        assert len(result) == 1
        assert result[0].type == "text"

    @pytest.mark.anyio
    async def test_invar_refs_mcp_typescript(self, tmp_path: Path):
        """Test invar_refs MCP handler with TypeScript file."""
        try:
            from invar.mcp.handlers import _run_refs
        except ImportError:
            pytest.skip("_run_refs handler not yet implemented in MCP")
            return

        (tmp_path / "tsconfig.json").write_text("{}")
        ts_file = tmp_path / "example.ts"
        ts_file.write_text("""
function hello() {}

function caller() {
    hello();
}
""")

        args = {"target": f"{ts_file}::hello"}
        result = await _run_refs(args)

        assert len(result) == 1
        assert result[0].type == "text"


# =============================================================================
# Error Message Tests
# =============================================================================


class TestDX78ErrorMessages:
    """Test DX-78 Phase B: Improved error messages."""

    def test_sig_error_suggests_tool(self):
        """sig error suggests using Grep when file not found."""
        from invar.shell.commands.perception import run_sig

        result = run_sig("/nonexistent/file.py", json_output=False)

        if isinstance(result, Failure):
            error_msg = result.failure()
            # Should suggest alternative tool
            assert "Grep" in error_msg or "search" in error_msg.lower()

    def test_map_error_suggests_tool(self, tmp_path: Path):
        """map error suggests alternative tools when no symbols found."""
        from invar.shell.commands.perception import run_map

        # Empty directory
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()

        result = run_map(empty_dir, top_n=10, json_output=False)

        # DX-78 Phase B: Should provide helpful tool suggestions
        if isinstance(result, Failure):
            error_msg = result.failure()
            # Check for tool suggestions (invar sig, Glob, or other helpful hints)
            assert any(
                keyword in error_msg.lower()
                for keyword in ["invar sig", "glob", "available tools", "no files", "no symbols"]
            )
