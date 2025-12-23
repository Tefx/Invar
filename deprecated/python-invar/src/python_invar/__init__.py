"""
DEPRECATED: python-invar has been split into two packages.

Use:
- `pip install invar-runtime` for runtime contracts (@pre, @post, etc.)
- `pip install invar-tools` for CLI tools (guard, map, sig, MCP server)

See: https://github.com/Tefx/Invar/releases/tag/v1.0.0
"""

import warnings

warnings.warn(
    "\n\npython-invar is DEPRECATED.\n\n"
    "The package has been split into:\n"
    "  - invar-runtime: Runtime contracts (@pre, @post, must_use, etc.)\n"
    "  - invar-tools: CLI tools (guard, map, sig, MCP server)\n\n"
    "To migrate:\n"
    "  pip uninstall python-invar\n"
    "  pip install invar-tools  # For development tools\n"
    "  pip install invar-runtime  # For runtime contracts in your project\n\n"
    "See: https://github.com/Tefx/Invar/releases/tag/v1.0.0\n",
    DeprecationWarning,
    stacklevel=2,
)

# Re-export everything from invar for backwards compatibility
from invar import *  # noqa: F401, F403
from invar import __all__  # noqa: F401
