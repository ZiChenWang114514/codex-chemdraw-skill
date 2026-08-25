"""Compatibility proxy for cdxml_toolkit.mcp_runtime.artifact_safety."""

from __future__ import annotations

from importlib import import_module as _import_module
import sys as _sys

_runtime = _import_module("cdxml_toolkit.mcp_runtime.artifact_safety")

if __name__ == "__main__":
    _main = getattr(_runtime, "main", None)
    if _main is None:
        raise SystemExit("This compatibility module has no command-line interface.")
    raise SystemExit(_main())
else:
    _sys.modules[__name__] = _runtime
