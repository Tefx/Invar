"""
LX-06: TypeScript tooling integration tests.

Tests for TypeScript guard, sig, and map functionality.
"""

from __future__ import annotations

from pathlib import Path

# =============================================================================
# TypeScript File Discovery Tests
# =============================================================================


class TestTypeScriptFileDiscovery:
    """Test TypeScript file discovery."""

    def test_discover_ts_files(self, tmp_path: Path):
        """Discovers .ts files."""
        from invar.shell.fs import discover_typescript_files

        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "index.ts").touch()
        (tmp_path / "src" / "utils.ts").touch()

        files = list(discover_typescript_files(tmp_path))
        assert len(files) == 2
        assert all(f.suffix == ".ts" for f in files)

    def test_discover_tsx_files(self, tmp_path: Path):
        """Discovers .tsx files."""
        from invar.shell.fs import discover_typescript_files

        (tmp_path / "components").mkdir()
        (tmp_path / "components" / "App.tsx").touch()

        files = list(discover_typescript_files(tmp_path))
        assert len(files) == 1
        assert files[0].suffix == ".tsx"

    def test_excludes_node_modules(self, tmp_path: Path):
        """Excludes node_modules directory."""
        from invar.shell.fs import discover_typescript_files

        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "index.ts").touch()
        (tmp_path / "node_modules").mkdir()
        (tmp_path / "node_modules" / "lib.ts").touch()

        files = list(discover_typescript_files(tmp_path))
        assert len(files) == 1
        # Check relative path doesn't include node_modules
        rel_path = str(files[0].relative_to(tmp_path))
        assert not rel_path.startswith("node_modules")

    def test_excludes_dist(self, tmp_path: Path):
        """Excludes dist directory."""
        from invar.shell.fs import discover_typescript_files

        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "index.ts").touch()
        (tmp_path / "dist").mkdir()
        (tmp_path / "dist" / "bundle.ts").touch()

        files = list(discover_typescript_files(tmp_path))
        assert len(files) == 1
        # Check relative path doesn't include dist
        rel_path = str(files[0].relative_to(tmp_path))
        assert not rel_path.startswith("dist")

    def test_does_not_exclude_prefix_match(self, tmp_path: Path):
        """Does NOT exclude directories that start with excluded name."""
        from invar.shell.fs import discover_typescript_files

        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "index.ts").touch()
        # dist_backup should NOT be excluded (only 'dist' should be)
        (tmp_path / "dist_backup").mkdir()
        (tmp_path / "dist_backup" / "old.ts").touch()

        files = list(discover_typescript_files(tmp_path))
        assert len(files) == 2  # Both index.ts and old.ts should be found
        names = {f.name for f in files}
        assert names == {"index.ts", "old.ts"}


# =============================================================================
# TypeScript Signature Extraction Tests
# =============================================================================


class TestTypeScriptSignatureExtraction:
    """Test TypeScript signature extraction from source code."""

    def test_extract_function(self):
        """Extracts function signature."""
        from invar.core.ts_sig_parser import extract_ts_signatures

        code = """
function greet(name: string): string {
    return `Hello, ${name}`;
}
"""
        symbols = extract_ts_signatures(code)
        assert len(symbols) == 1
        assert symbols[0].name == "greet"
        assert symbols[0].kind == "function"
        assert "name: string" in symbols[0].signature

    def test_extract_async_function(self):
        """Extracts async function signature."""
        from invar.core.ts_sig_parser import extract_ts_signatures

        code = """
async function fetchData(url: string): Promise<Response> {
    return fetch(url);
}
"""
        symbols = extract_ts_signatures(code)
        assert len(symbols) == 1
        assert symbols[0].name == "fetchData"
        assert symbols[0].kind == "function"

    def test_extract_class(self):
        """Extracts class signature."""
        from invar.core.ts_sig_parser import extract_ts_signatures

        code = """
export class User {
    constructor(public name: string) {}
}
"""
        symbols = extract_ts_signatures(code)
        assert len(symbols) == 1
        assert symbols[0].name == "User"
        assert symbols[0].kind == "class"

    def test_extract_interface(self):
        """Extracts interface signature."""
        from invar.core.ts_sig_parser import extract_ts_signatures

        code = """
interface Config {
    port: number;
    host: string;
}
"""
        symbols = extract_ts_signatures(code)
        assert len(symbols) == 1
        assert symbols[0].name == "Config"
        assert symbols[0].kind == "interface"

    def test_extract_type_alias(self):
        """Extracts type alias."""
        from invar.core.ts_sig_parser import extract_ts_signatures

        code = """
type Status = "pending" | "active" | "done";
"""
        symbols = extract_ts_signatures(code)
        assert len(symbols) == 1
        assert symbols[0].name == "Status"
        assert symbols[0].kind == "type"

    def test_extract_multiple_symbols(self):
        """Extracts multiple symbols from same file."""
        from invar.core.ts_sig_parser import extract_ts_signatures

        code = """
interface User {
    id: number;
    name: string;
}

function createUser(name: string): User {
    return { id: 1, name };
}

export class UserService {
    private users: User[] = [];
}
"""
        symbols = extract_ts_signatures(code)
        assert len(symbols) == 3
        names = {s.name for s in symbols}
        assert names == {"User", "createUser", "UserService"}

    def test_extract_decorated_class(self):
        """Extracts decorated class with correct signature (not decorator)."""
        from invar.core.ts_sig_parser import extract_ts_signatures

        code = """
@Component({selector: 'app-root'})
export class AppComponent {
    title = 'app';
}
"""
        symbols = extract_ts_signatures(code)
        assert len(symbols) == 1
        assert symbols[0].name == "AppComponent"
        assert symbols[0].kind == "class"
        # Signature should be the class line, NOT the decorator
        assert "export class AppComponent" in symbols[0].signature
        assert "@Component" not in symbols[0].signature


# =============================================================================
# TypeScript Parser Output Tests
# =============================================================================


class TestTypeScriptParsers:
    """Test TypeScript tool output parsers."""

    def test_parse_tsc_error(self):
        """Parses tsc error line."""
        from invar.core.ts_parsers import parse_tsc_line

        line = "src/index.ts(10,5): error TS2322: Type 'string' is not assignable to type 'number'."
        result = parse_tsc_line(line)
        assert result is not None
        assert result.file == "src/index.ts"
        assert result.line == 10
        assert result.column == 5
        assert result.rule == "TS2322"
        assert "Type 'string'" in result.message

    def test_parse_tsc_output_multiple(self):
        """Parses multiple tsc errors."""
        from invar.core.ts_parsers import parse_tsc_output

        output = """
src/a.ts(1,1): error TS2304: Cannot find name 'foo'.
src/b.ts(2,3): error TS2322: Type mismatch.
"""
        violations = parse_tsc_output(output)
        assert len(violations) == 2
        assert violations[0].file == "src/a.ts"
        assert violations[1].file == "src/b.ts"

    def test_parse_eslint_json(self):
        """Parses ESLint JSON output."""
        from invar.core.ts_parsers import parse_eslint_json

        output = """[
    {
        "filePath": "/project/src/index.ts",
        "messages": [
            {
                "ruleId": "no-unused-vars",
                "severity": 2,
                "message": "'x' is defined but never used",
                "line": 5,
                "column": 7
            }
        ]
    }
]"""
        violations = parse_eslint_json(output, "/project")
        assert len(violations) == 1
        assert violations[0].file == "src/index.ts"
        assert violations[0].rule == "no-unused-vars"
        assert violations[0].severity == "error"

    def test_parse_eslint_empty(self):
        """Handles empty ESLint output."""
        from invar.core.ts_parsers import parse_eslint_json

        violations = parse_eslint_json("[]", "/project")
        assert violations == []

    def test_parse_eslint_invalid_json(self):
        """Handles invalid JSON gracefully."""
        from invar.core.ts_parsers import parse_eslint_json

        violations = parse_eslint_json("not json", "/project")
        assert violations == []


# =============================================================================
# TypeScript Guard Result Tests
# =============================================================================


class TestTypeScriptGuardResult:
    """Test TypeScript guard result structure."""

    def test_result_structure(self):
        """Guard result has expected fields."""
        from invar.shell.prove.guard_ts import TypeScriptGuardResult

        result = TypeScriptGuardResult(status="passed")
        assert result.status == "passed"
        assert result.violations == []
        assert result.error_count == 0
        assert result.warning_count == 0
        assert result.tool_errors == []

    def test_result_with_violations(self):
        """Guard result tracks violations correctly."""
        from invar.core.ts_parsers import TSViolation
        from invar.shell.prove.guard_ts import TypeScriptGuardResult

        violation = TSViolation(
            file="src/index.ts",
            line=10,
            column=5,
            rule="TS2322",
            message="Type error",
            severity="error",
            source="tsc",
        )
        result = TypeScriptGuardResult(
            status="failed",
            violations=[violation],
            error_count=1,
        )
        assert result.status == "failed"
        assert len(result.violations) == 1
        assert result.error_count == 1


# =============================================================================
# TypeScript Sig/Map Integration Tests
# =============================================================================


class TestTypeScriptPerception:
    """Test TypeScript sig and map integration."""

    def test_sig_typescript_file(self, tmp_path: Path):
        """sig extracts signatures from .ts file."""
        from returns.result import Success

        from invar.shell.commands.perception import run_sig

        ts_file = tmp_path / "example.ts"
        ts_file.write_text("""
function hello(name: string): string {
    return `Hello, ${name}`;
}

export class Greeter {
    greet(): void {}
}
""")
        # Note: run_sig prints to console, so we just verify it succeeds
        result = run_sig(str(ts_file), json_output=True)
        assert isinstance(result, Success)

    def test_map_typescript_project(self, tmp_path: Path):
        """map discovers symbols in TypeScript project."""
        from returns.result import Success

        from invar.shell.commands.perception import run_map

        # Create TypeScript project structure
        (tmp_path / "tsconfig.json").write_text("{}")
        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "index.ts").write_text("""
export function main(): void {}
""")
        (tmp_path / "src" / "utils.ts").write_text("""
export function helper(): string { return ""; }
""")

        result = run_map(tmp_path, top_n=10, json_output=True)
        assert isinstance(result, Success)


# =============================================================================
# Format Output Tests
# =============================================================================


class TestTypeScriptFormatters:
    """Test TypeScript output formatters."""

    def test_format_json(self):
        """JSON formatter produces valid structure."""
        from invar.core.ts_sig_parser import TSSymbol, format_ts_signatures_json

        symbols = [
            TSSymbol("foo", "function", "function foo(): void", 1),
            TSSymbol("Bar", "class", "class Bar", 5),
        ]
        result = format_ts_signatures_json(symbols, "test.ts")

        assert result["file"] == "test.ts"
        assert len(result["symbols"]) == 2
        assert result["symbols"][0]["name"] == "foo"
        assert result["symbols"][1]["name"] == "Bar"

    def test_format_text(self):
        """Text formatter produces readable output."""
        from invar.core.ts_sig_parser import TSSymbol, format_ts_signatures_text

        symbols = [
            TSSymbol("foo", "function", "function foo(): void", 1),
        ]
        result = format_ts_signatures_text(symbols, "test.ts")

        assert "foo" in result
        assert "function" in result
        assert "test.ts" in result
