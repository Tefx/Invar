# python-invar (DEPRECATED)

> **This package is deprecated.** Please migrate to the new packages.

## Migration Guide

`python-invar` has been split into two packages for better modularity:

| Old | New | Purpose |
|-----|-----|---------|
| `python-invar` | `invar-runtime` | Runtime contracts (`@pre`, `@post`, `must_use`, etc.) |
| `python-invar` | `invar-tools` | CLI tools (`guard`, `map`, `sig`, MCP server) |

### For Projects Using Contracts

If your project uses Invar contracts at runtime:

```bash
pip uninstall python-invar
pip install invar-runtime
```

Update imports:
```python
# Old
from invar import pre, post, Contract

# New (recommended)
from invar_runtime import pre, post, Contract

# Or keep using 'invar' (still works via invar-tools)
from invar import pre, post, Contract
```

### For Development Tools

If you use Invar CLI tools:

```bash
pip uninstall python-invar
pip install invar-tools
```

Or use without installing:
```bash
uvx invar-tools guard
```

## Why the Split?

- **`invar-runtime`** (~3MB): Lightweight, only what your project needs at runtime
- **`invar-tools`** (~100MB): Full development tools with Hypothesis, CrossHair, etc.

Projects can now depend on just `invar-runtime` without the heavy verification tools.

## Links

- [Migration Guide](https://github.com/Tefx/Invar/releases/tag/v1.0.0)
- [invar-runtime on PyPI](https://pypi.org/project/invar-runtime/)
- [invar-tools on PyPI](https://pypi.org/project/invar-tools/)
- [GitHub Repository](https://github.com/Tefx/Invar)
