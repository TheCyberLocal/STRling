"""
Compatibility shim.

The Island Grammar extractor moved into the canonical Python core at
``STRling.core.islands`` (re-exported by ``STRling.core.intelligence``).
This module remains only so any external callers that imported
``island_extractor`` directly continue to work. New code should import
from ``STRling.core.intelligence`` instead.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Ensure the in-tree Python binding is importable when this shim is used
# from the lsp-server tree without the package being installed.
_REPO_ROOT = Path(__file__).resolve().parents[2]
_PY_SRC = _REPO_ROOT / "bindings" / "python" / "src"
if _PY_SRC.is_dir() and str(_PY_SRC) not in sys.path:
    sys.path.insert(0, str(_PY_SRC))

from STRling.core.islands import (  # noqa: E402,F401  (re-export)
    HostPosition,
    Island,
    boundary_calls,
    extract_islands,
    extract_islands_for_uri,
    language_for_uri,
    language_suffixes,
    reload_boundary_spec,
)

__all__ = [
    "HostPosition",
    "Island",
    "boundary_calls",
    "extract_islands",
    "extract_islands_for_uri",
    "language_for_uri",
    "language_suffixes",
    "reload_boundary_spec",
]
