"""Init command for Invar (DX-91 simplified surface)."""

from __future__ import annotations

import re
import shutil
import tempfile
from pathlib import Path

import typer
import yaml
from rich.console import Console

from invar.core.language import detect_language_from_markers

console = Console()

MANAGED_BEGIN = "<!--invar:begin-->"
MANAGED_END = "<!--invar:end-->"
LEGACY_MARKERS = ("<!--invar:critical-->", "<!--invar:managed")
LEGACY_MANAGED_HEADER = "INVAR-MANAGED FILE - DO NOT EDIT DIRECTLY"

LEGACY_REMOVE_PATHS: tuple[str, ...] = (
    ".claude/skills",
    ".claude/hooks",
    ".pi/hooks",
    ".pi/tools",
    ".invar/examples",
)

PRESERVED_BACKUPS: tuple[tuple[str, str], ...] = (
    (".invar/context.md", "v1-context.md"),
    (".invar/project-additions.md", "v1-project-additions.md"),
)

LANGUAGE_MARKERS: frozenset[str] = frozenset(
    {
        "pyproject.toml",
        "setup.py",
        "Cargo.toml",
        "go.mod",
    }
)

CLAUDE_MANAGED_BLOCK = """<!--invar:begin-->
## Invar

**CRITICAL: Write `@pre`/`@post` contracts and at least one doctest BEFORE implementing a Core function. Guard rejects uncontracted Core code.**

### Architecture

| Zone | Path | Rules |
|------|------|-------|
| Core | `**/core/**` | `@pre` + `@post` + doctest, no I/O imports |
| Shell | `**/shell/**` | returns `Result[T, E]`, handles I/O |

If code touches files, network, env vars, time, randomness, or subprocesses, use Shell.

### Verification

Run `invar guard` after changes. Fix errors before committing.

### Tools

| Tool | Use |
|------|-----|
| `invar guard` | verify architecture and contracts |
| `invar sig <file>` | inspect signatures and contracts |
| `invar map [path]` | inspect entry points |
| `invar refs <file>::<symbol>` | inspect references |

### Contract Traps

```python
# @pre must include all parameters, including defaults
@pre(lambda x, y=0: x >= 0)
def calc(x: int, y: int = 0): ...

# @post only receives result
@post(lambda result: result >= 0)
```

### Escape Hatches

```python
# @invar:allow dead_export: CLI entry point called by framework
```

Exact syntax and repair patterns: `INVAR.md`
<!--invar:end-->
"""

INVAR_MANAGED_CONTENT = '''# Invar Protocol

## Before Writing Code

1. If you are writing a Core function, write `@pre`, `@post`, and at least one doctest BEFORE implementation.
2. If you are unsure whether code belongs in Core or Shell, use Shell.
3. Run `invar guard` after changes. Fix errors before committing.

## Core vs Shell

Use Shell if the code does any of these:
- reads or writes files
- makes network requests
- reads environment variables
- uses current time or randomness without injection
- performs subprocess or system I/O

Use Core for pure logic that only transforms already-available data.

| Zone | Path | Rules |
|------|------|-------|
| Core | `**/core/**` | `@pre` + `@post` + doctest, no I/O imports |
| Shell | `**/shell/**` | returns `Result[T, E]`, performs I/O |

## Contract Syntax Traps

### `@pre` lambda must include all function parameters

```python
# WRONG
@pre(lambda x: x >= 0)
def calc(x: int, y: int = 0): ...

# CORRECT
@pre(lambda x, y=0: x >= 0)
def calc(x: int, y: int = 0): ...
```

### `@post` only receives `result`

```python
# WRONG
@post(lambda result: result > x)

# CORRECT
@post(lambda result: result >= 0)
```

### Contracts must be semantic, not just type checks

```python
# WEAK
@pre(lambda x: isinstance(x, int))

# BETTER
@pre(lambda x: x > 0)
@pre(lambda start, end: start < end)
```

## Canonical Core Example

```python
from invar_runtime import pre, post

@pre(lambda price, discount: price > 0 and 0 <= discount <= 1)
@post(lambda result: result >= 0)
def discounted_price(price: float, discount: float) -> float:
    """
    >>> discounted_price(100, 0.2)
    80.0
    """
    return price * (1 - discount)
```

## Canonical Shell Example

```python
from pathlib import Path
from returns.result import Result, Success, Failure

def read_config(path: Path) -> Result[str, str]:
    try:
        return Success(path.read_text())
    except OSError as exc:
        return Failure(str(exc))
```

## Escape Hatches

```python
# @invar:allow dead_export: CLI entry point called by framework
# @invar:allow shell_complexity: orchestration requires many steps
```

Use escape hatches rarely and always include a reason.

## Minimal Configuration

```toml
[tool.invar.guard]
core_paths = ["src/myapp/core"]
shell_paths = ["src/myapp/shell"]
```

## Common Guard Repairs

| Error | Fix |
|------|-----|
| `missing_contract` | add `@pre`, `@post`, and a doctest before implementation |
| `param_mismatch` | include every function parameter in the `@pre` lambda |
| `shell_result` | return `Result[T, E]` from Shell functions |
| `forbidden_import` | move I/O out of Core or inject the value as a parameter |
'''


def detect_language(path: Path) -> str:
    """Detect project language from marker files (compatibility helper)."""
    present_markers = frozenset(marker for marker in LANGUAGE_MARKERS if (path / marker).exists())
    return detect_language_from_markers(present_markers)


def _resolve_target_file(root: Path, file: str) -> Path:
    target = Path(file)
    if target.is_absolute():
        return target
    return root / target


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.exists() else ""


def _atomic_write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        "w", encoding="utf-8", delete=False, dir=str(path.parent)
    ) as tmp:
        tmp.write(content)
        tmp_path = Path(tmp.name)
    tmp_path.replace(path)


def _strip_legacy_blocks(content: str) -> str:
    pairs = (
        (r"<!--invar:critical-->", r"<!--/invar:critical-->"),
        (r"<!--invar:managed.*?-->", r"<!--/invar:managed-->"),
        (r"<!--invar:project-->", r"<!--/invar:project-->"),
    )
    cleaned = content
    for begin_pattern, end_pattern in pairs:
        pattern = re.compile(begin_pattern + r".*?" + end_pattern, flags=re.DOTALL)
        cleaned = pattern.sub("", cleaned)

    user_pattern = re.compile(
        r"<!--invar:user-->\s*(.*?)\s*<!--/invar:user-->",
        flags=re.DOTALL,
    )
    cleaned = user_pattern.sub(lambda m: m.group(1), cleaned)
    return cleaned.strip("\n")


# @shell_complexity: Handles v1/v2 marker migration and append-safe behavior.
def _upsert_managed_block(existing: str, managed_block: str) -> str:
    begin_idx = existing.find(MANAGED_BEGIN)
    if begin_idx >= 0:
        end_idx = existing.find(MANAGED_END, begin_idx)
        if end_idx >= 0:
            end_idx += len(MANAGED_END)
            return (existing[:begin_idx] + managed_block + existing[end_idx:]).strip("\n") + "\n"

    if any(marker in existing for marker in LEGACY_MARKERS):
        preserved = _strip_legacy_blocks(existing)
        if preserved:
            return f"{preserved}\n\n{managed_block}".strip("\n") + "\n"
        return managed_block.strip("\n") + "\n"

    if existing.strip():
        return f"{existing.rstrip()}\n\n{managed_block}".strip("\n") + "\n"
    return managed_block.strip("\n") + "\n"


# @shell_complexity: Must preserve arbitrary pre-commit YAML while adding local hook.
def _merge_pre_commit(path: Path) -> str:
    config_path = path / ".pre-commit-config.yaml"
    if not config_path.exists():
        return (
            "repos:\n"
            "  - repo: local\n"
            "    hooks:\n"
            "      - id: invar-guard\n"
            "        name: invar guard\n"
            "        entry: invar guard\n"
            "        language: system\n"
            "        pass_filenames: false\n"
            "        always_run: true\n"
        )

    loaded = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    if loaded is None:
        loaded = {}
    if not isinstance(loaded, dict):
        raise ValueError(".pre-commit-config.yaml must be a mapping")

    repos = loaded.setdefault("repos", [])
    if not isinstance(repos, list):
        raise ValueError(".pre-commit-config.yaml field 'repos' must be a list")

    local_repo: dict[str, object] | None = None
    for repo in repos:
        if isinstance(repo, dict) and repo.get("repo") == "local":
            local_repo = repo
            break

    if local_repo is None:
        local_repo = {"repo": "local", "hooks": []}
        repos.append(local_repo)

    hooks = local_repo.setdefault("hooks", [])
    if not isinstance(hooks, list):
        raise ValueError(".pre-commit-config.yaml local repo 'hooks' must be a list")

    for hook in hooks:
        if isinstance(hook, dict) and hook.get("id") == "invar-guard":
            return yaml.safe_dump(loaded, sort_keys=False, allow_unicode=False)

    hooks.append(
        {
            "id": "invar-guard",
            "name": "invar guard",
            "entry": "invar guard",
            "language": "system",
            "pass_filenames": False,
            "always_run": True,
        }
    )
    return yaml.safe_dump(loaded, sort_keys=False, allow_unicode=False)


def _is_v1_layout(root: Path, target_file: Path) -> bool:
    for rel in LEGACY_REMOVE_PATHS:
        if (root / rel).exists():
            return True

    invar_text = _read_text(root / "INVAR.md")
    if LEGACY_MANAGED_HEADER in invar_text:
        return True

    target_text = _read_text(target_file)
    return any(marker in target_text for marker in LEGACY_MARKERS)


# @shell_complexity: Backup is conditional and must abort migration on I/O failures.
def _backup_preserved_files(root: Path) -> list[str]:
    backed_up: list[str] = []
    backup_dir = root / ".invar" / "backup"

    existing_sources = [rel for rel, _ in PRESERVED_BACKUPS if (root / rel).exists()]
    if not existing_sources:
        return backed_up

    try:
        backup_dir.mkdir(parents=True, exist_ok=True)
        for src_rel, backup_name in PRESERVED_BACKUPS:
            src = root / src_rel
            if not src.exists():
                continue
            dst = backup_dir / backup_name
            shutil.copy2(src, dst)
            backed_up.append(f"{src_rel} -> .invar/backup/{backup_name}")
    except OSError as exc:
        raise RuntimeError(f"Backup failed. Migration aborted. {exc}") from exc

    return backed_up


# @shell_complexity: Delete pass must report partial progress on failure.
def _delete_legacy_assets(root: Path) -> list[str]:
    deleted: list[str] = []
    for rel in LEGACY_REMOVE_PATHS:
        path = root / rel
        if not path.exists():
            continue
        try:
            if path.is_dir():
                shutil.rmtree(path)
            else:
                path.unlink()
            deleted.append(rel)
        except OSError as exc:
            detail = ", ".join(deleted) if deleted else "none"
            raise RuntimeError(
                f"Failed deleting legacy assets. Deleted before failure: {detail}. Error: {exc}"
            ) from exc
    return deleted


def _render_migration_preview(target_file: Path) -> None:
    console.print()
    console.print("[bold]⚠ Legacy Invar v1 layout detected. Migration preview follows.[/bold]")
    console.print()

    console.print("[bold][DELETED][/bold] Stale agent config (non-fatal if absent):")
    for rel in LEGACY_REMOVE_PATHS:
        console.print(f"  • {rel}/" if not rel.endswith("/") else f"  • {rel}")

    console.print()
    console.print("[bold][PRESERVED][/bold] User data (backed up before deletion, if present):")
    for src_rel, backup_name in PRESERVED_BACKUPS:
        console.print(f"  • {src_rel} -> .invar/backup/{backup_name} (if present)")

    console.print()
    console.print("[bold][OVERWRITTEN][/bold] Managed files:")
    console.print("  • INVAR.md")
    console.print(f"  • {target_file.name} invar block")
    console.print()


def _write_minimal_state(root: Path, target_file: Path) -> list[str]:
    written: list[str] = []
    target_existing = _read_text(target_file)
    merged_target = _upsert_managed_block(target_existing, CLAUDE_MANAGED_BLOCK)
    _atomic_write(target_file, merged_target)
    written.append(
        str(target_file.relative_to(root)) if target_file.is_relative_to(root) else str(target_file)
    )

    _atomic_write(root / "INVAR.md", INVAR_MANAGED_CONTENT.strip("\n") + "\n")
    written.append("INVAR.md")

    merged_pre_commit = _merge_pre_commit(root)
    _atomic_write(root / ".pre-commit-config.yaml", merged_pre_commit)
    written.append(".pre-commit-config.yaml")
    return written


# @shell_complexity: Single entrypoint orchestrates preview, migration, backup, cleanup, and writes.
def init(
    path: Path = typer.Argument(Path(), help="Project root directory (default: current directory)"),
    file: str = typer.Option(
        "CLAUDE.md", "--file", help="Instruction file target (default: CLAUDE.md)"
    ),
    preview: bool = typer.Option(
        False, "--preview", help="Show migration/create plan without writing"
    ),
) -> None:
    """Initialize Invar with DX-91 minimal generated surface."""
    from invar import __version__

    root = path.resolve() if path != Path() else Path.cwd().resolve()
    target_file = _resolve_target_file(root, file)
    is_migration = _is_v1_layout(root, target_file)

    console.print(f"\n[bold]Invar v{__version__} - Simplified Init[/bold]")
    console.print("=" * 45)
    console.print(f"[dim]Root: {root} | Target: {target_file}[/dim]")

    if is_migration:
        _render_migration_preview(target_file)
        if preview:
            console.print("[dim]Preview only. No changes applied.[/dim]")
            return
        if not typer.confirm("Proceed?", default=False):
            console.print("[yellow]Migration cancelled.[/yellow]")
            raise typer.Exit(1)
    elif preview:
        console.print("\n[bold]Preview[/bold]: would write managed files")
        console.print(f"  • {target_file}")
        console.print("  • INVAR.md")
        console.print("  • .pre-commit-config.yaml")
        return

    backed_up: list[str] = []
    deleted: list[str] = []
    written: list[str] = []

    try:
        if is_migration:
            backed_up = _backup_preserved_files(root)
            deleted = _delete_legacy_assets(root)
        written = _write_minimal_state(root, target_file)
    except (OSError, RuntimeError, ValueError) as exc:
        console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(1) from exc

    console.print("\n[bold green]✓ Invar init complete[/bold green]")
    if deleted:
        console.print("[bold]Deleted:[/bold]")
        for rel in deleted:
            console.print(f"  • {rel}")
    if backed_up:
        console.print("[bold]Backed up:[/bold]")
        for rel in backed_up:
            console.print(f"  • {rel}")
    console.print("[bold]Written:[/bold]")
    for rel in written:
        console.print(f"  • {rel}")
