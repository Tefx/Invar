#!/usr/bin/env python3
# @invar:allow shell_result: Standalone build script, not part of invar package
"""Build TypeScript packages and embed into Python package.

This script:
1. Builds all @invar/* TypeScript packages (pnpm build)
2. Copies the dist/ output to src/invar/node_tools/
3. Creates a manifest of embedded tools

Run this before `python -m build` to include Node tools in the wheel.

Usage:
    python scripts/embed_node_tools.py [--skip-build] [--clean]

Options:
    --skip-build    Skip pnpm build, only copy existing dist/
    --clean         Remove existing node_tools content before copying
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

# Tools to embed (package names in typescript/packages/)
TOOLS = ["ts-analyzer", "fc-runner", "quick-check", "eslint-plugin"]


# @invar:allow shell_result: Standalone script helper
def get_paths() -> tuple[Path, Path, Path]:
    """Get project paths."""
    script_dir = Path(__file__).parent
    root = script_dir.parent
    ts_dir = root / "typescript"
    target = root / "src" / "invar" / "node_tools"
    return root, ts_dir, target


# @invar:allow shell_result: Standalone script helper
def check_prerequisites(ts_dir: Path) -> bool:
    """Check if TypeScript workspace exists and has pnpm."""
    if not ts_dir.exists():
        print(f"ERROR: TypeScript directory not found: {ts_dir}")
        return False

    if not (ts_dir / "pnpm-workspace.yaml").exists():
        print(f"ERROR: Not a pnpm workspace: {ts_dir}")
        return False

    return True


# @invar:allow shell_result: Standalone script helper
def build_typescript(ts_dir: Path) -> bool:
    """Run pnpm install, build, and bundle.

    Validates pnpm binary location to prevent PATH manipulation attacks.
    """
    print("Building TypeScript packages...")

    # Validate pnpm binary location to prevent command injection
    pnpm_path = shutil.which("pnpm")
    if not pnpm_path:
        print("ERROR: pnpm not found in PATH")
        return False

    print(f"  Using pnpm: {pnpm_path}")

    # Install dependencies
    print("  pnpm install...")
    result = subprocess.run(
        [pnpm_path, "install"],
        cwd=ts_dir,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        print(f"ERROR: pnpm install failed:\n{result.stderr}")
        return False

    # Build and bundle all packages
    print("  pnpm build:all (compile + bundle)...")
    result = subprocess.run(
        [pnpm_path, "build:all"],
        cwd=ts_dir,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        print(f"ERROR: pnpm build:all failed:\n{result.stderr}")
        return False

    print("  Build complete.")
    return True


def clean_target(target: Path) -> None:
    """Remove existing tool directories (preserve __init__.py).

    Uses scandir with proper error handling to avoid TOCTOU race conditions.
    """
    print("Cleaning existing embedded tools...")
    import os

    with os.scandir(target) as entries:
        for entry in entries:
            if entry.is_dir(follow_symlinks=False):
                try:
                    shutil.rmtree(entry.path)
                    print(f"  Removed {entry.name}/")
                except FileNotFoundError:
                    # Already deleted by another process - OK
                    pass
                except PermissionError as e:
                    print(f"  WARNING: Cannot remove {entry.name}/: {e}")


# @invar:allow shell_result: Standalone script helper
# @shell_complexity: File copy with validation and size reporting
def copy_tool(ts_dir: Path, target: Path, tool_name: str) -> bool:
    """Copy a single tool's CLI to target.

    Special handling:
    - eslint-plugin: Copy entire dist/ directory (unbundled, 632 KB)
    - Others: Prefer bundle.js (standalone with deps) over cli.js
    """
    src = ts_dir / "packages" / tool_name / "dist"
    src_pkg = ts_dir / "packages" / tool_name
    dst = target / tool_name

    if not src.exists():
        print(f"  WARNING: {tool_name}/dist not found, skipping")
        return False

    # Special case: eslint-plugin needs unbundled dist/ for ESLint module resolution
    if tool_name == "eslint-plugin":
        # Remove existing directory if present
        if dst.exists():
            shutil.rmtree(dst)

        # Copy entire dist/ directory
        shutil.copytree(src, dst)

        # Get total size for reporting
        total_size = sum(f.stat().st_size for f in dst.rglob('*') if f.is_file())
        size_kb = total_size / 1024

        print(f"  Embedded {tool_name} (unbundled: {size_kb:.1f} KB)")

        # Copy package.json for dependencies
        pkg_json = src_pkg / "package.json"
        if pkg_json.exists():
            with open(pkg_json) as f:
                pkg_data = json.load(f)
            safe_pkg = {
                "name": pkg_data.get("name", "unknown"),
                "version": pkg_data.get("version", "0.0.0"),
                "type": pkg_data.get("type"),  # Keep "module" for ESM compatibility
                "dependencies": pkg_data.get("dependencies", {}),
                "engines": pkg_data.get("engines", {}),
            }
            # Remove None values
            safe_pkg = {k: v for k, v in safe_pkg.items() if v is not None}
            with open(dst / "package.json", "w") as f:
                json.dump(safe_pkg, f, indent=2)

        return True

    # Other tools: use bundled approach
    bundle_js = src / "bundle.js"
    cli_js = src / "cli.js"

    if bundle_js.exists():
        source_file = bundle_js
    elif cli_js.exists():
        source_file = cli_js
        print(f"  WARNING: {tool_name} using unbundled cli.js (may need deps)")
    else:
        print(f"  WARNING: {tool_name}/dist has no cli.js or bundle.js, skipping")
        return False

    # Create target directory
    dst.mkdir(parents=True, exist_ok=True)

    # Copy the CLI bundle as cli.js (standardized name)
    dest_cli = dst / "cli.js"
    shutil.copy2(source_file, dest_cli)

    # Copy package.json if it exists (for tools with runtime dependencies)
    # Strip "type": "module" since bundles are CommonJS
    # Only copy required fields to prevent injection of malicious scripts
    pkg_json = src_pkg / "package.json"
    if pkg_json.exists():
        with open(pkg_json) as f:
            pkg_data = json.load(f)

        # Sanitized package.json: only copy safe fields needed for npm install
        safe_pkg = {
            "name": pkg_data.get("name", "unknown"),
            "version": pkg_data.get("version", "0.0.0"),
            "dependencies": pkg_data.get("dependencies", {}),
            "engines": pkg_data.get("engines", {}),
        }
        # Explicitly exclude: type, scripts, bin, devDependencies

        with open(dst / "package.json", "w") as f:
            json.dump(safe_pkg, f, indent=2)

    # Get size for reporting
    size_kb = dest_cli.stat().st_size / 1024

    print(f"  Embedded {tool_name} ({size_kb:.1f} KB)")
    return True


def write_manifest(target: Path, embedded: list[str]) -> None:
    """Write manifest of embedded tools."""
    manifest = target / "MANIFEST"
    with open(manifest, "w") as f:
        f.write("# Embedded Node.js tools\n")
        f.write("# Auto-generated by scripts/embed_node_tools.py\n")
        f.write("# Do not edit manually\n\n")
        for tool in sorted(embedded):
            f.write(f"{tool}\n")
    print(f"  Wrote MANIFEST ({len(embedded)} tools)")


# @invar:allow shell_result: Standalone script helper
def install_dependencies(target: Path, embedded: list[str]) -> bool:
    """Install runtime dependencies for tools that need them.

    Runs npm install --production in each tool directory that has package.json.
    Uses --ignore-scripts to prevent malicious postinstall scripts.
    """
    print("Installing runtime dependencies...")
    for tool in embedded:
        tool_dir = target / tool
        pkg_json = tool_dir / "package.json"

        if not pkg_json.exists():
            continue

        print(f"  Installing deps for {tool}...")
        node_modules = tool_dir / "node_modules"

        result = subprocess.run(
            ["npm", "install", "--production", "--no-save", "--ignore-scripts"],
            cwd=tool_dir,
            capture_output=True,
            text=True,
        )

        if result.returncode != 0:
            print(f"  ERROR: npm install failed for {tool}:")
            print(result.stderr)
            # Clean up partial install
            if node_modules.exists():
                print(f"  Cleaning up partial install...")
                shutil.rmtree(node_modules)
            return False

        # Report installed packages
        if node_modules.exists():
            pkg_count = len(list(node_modules.iterdir()))
            print(f"    Installed {pkg_count} packages")

    return True


# @invar:allow shell_result: Standalone script entry point
# @shell_complexity: CLI entry point with argument parsing and workflow orchestration
def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--skip-build",
        action="store_true",
        help="Skip pnpm build, only copy existing dist/",
    )
    parser.add_argument(
        "--clean",
        action="store_true",
        help="Remove existing node_tools content before copying",
    )
    args = parser.parse_args()

    root, ts_dir, target = get_paths()

    print(f"Invar root: {root}")
    print(f"TypeScript: {ts_dir}")
    print(f"Target: {target}")
    print()

    # Check prerequisites
    if not check_prerequisites(ts_dir):
        return 1

    # Build TypeScript (unless skipped)
    if not args.skip_build:
        if not build_typescript(ts_dir):
            return 1
    else:
        print("Skipping TypeScript build (--skip-build)")

    print()

    # Clean if requested
    if args.clean and target.exists():
        clean_target(target)

    # Copy tools
    print("Embedding tools...")
    embedded: list[str] = []
    for tool in TOOLS:
        if copy_tool(ts_dir, target, tool):
            embedded.append(tool)

    print()

    if not embedded:
        print("WARNING: No tools were embedded!")
        return 1

    # Write manifest
    write_manifest(target, embedded)

    print()

    # Install runtime dependencies
    if not install_dependencies(target, embedded):
        return 1

    print()
    print(f"Done! Embedded {len(embedded)}/{len(TOOLS)} tools.")
    print()
    print("Next steps:")
    print("  1. Test: python -c 'from invar.node_tools import list_available_tools; print(list_available_tools())'")
    print("  2. Build: python -m build")
    print("  3. Install: pip install dist/*.whl")

    return 0


if __name__ == "__main__":
    sys.exit(main())
