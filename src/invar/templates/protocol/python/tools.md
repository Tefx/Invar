## Commands (Python)

```bash
invar guard              # Check git-modified files (fast, default)
invar guard --all        # Check entire project (CI, release)
invar guard --static     # Static only (quick debug, ~0.5s)
invar guard --coverage   # Collect branch coverage
invar guard -c           # Contract coverage only (DX-63)
invar sig <file>         # Show contracts + signatures
invar map --top 10       # Most-referenced symbols
invar rules              # List all rules with detection/hints (JSON)
```

**Default behavior**: Checks git-modified files for fast feedback during development.
Use `--all` for comprehensive checks before release.

## Configuration (Python)

```toml
# pyproject.toml or invar.toml
[tool.invar.guard]
core_paths = ["src/myapp/core"]    # Default: ["src/core", "core"]
shell_paths = ["src/myapp/shell"]  # Default: ["src/shell", "shell"]
max_file_lines = 500               # Default: 500 (warning at 80%)
max_function_lines = 50            # Default: 50
# Doctest lines are excluded from size calculations
```
