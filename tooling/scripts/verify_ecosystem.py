#!/usr/bin/env python3
"""
Shim wrapper for backwards compatibility.

This module ensures the script is available at both
`tooling/verify_ecosystem.py` and `tooling/scripts/verify_ecosystem.py` as
expected by unit tests.  It loads the primary implementation from the
parent `tooling/verify_ecosystem.py` file and re-exports its public
symbols into this module's namespace.

The approach avoids duplicating implementation and keeps a single
source-of-truth in `tooling/verify_ecosystem.py`.
"""

from __future__ import annotations

import importlib.util
import os
import sys

# Resolve the canonical implementation file one level up
HERE = os.path.dirname(__file__)
PARENT_IMPL = os.path.abspath(os.path.join(HERE, "..", "verify_ecosystem.py"))

if not os.path.exists(PARENT_IMPL):
    # If the parent implementation is missing, raise a clear error
    raise FileNotFoundError(
        f"Expected implementation at {PARENT_IMPL} but it was not found."
    )

spec = importlib.util.spec_from_file_location("verify_ecosystem", PARENT_IMPL)
_impl = importlib.util.module_from_spec(spec)
# Register module early so dataclass/type lookups that consult sys.modules
# can find the module while it is being executed.
sys.modules[spec.name] = _impl
# Execute the implementation module in its own namespace
spec.loader.exec_module(_impl)

# Re-export all non-dunder attributes from the implementation module
for _name, _val in vars(_impl).items():
    if not _name.startswith("__"):
        globals()[_name] = _val

# Make the implementation module available as an attribute if callers want it
implementation = _impl

# Expose a helpful module-level __doc__ to callers
__doc__ = (
    (__doc__ or "")
    + "\n\nThis module re-exports the implementation found at: "
    + PARENT_IMPL
)

if __name__ == "__main__":
    # Delegate to the canonical implementation's main() when run as script
    raise SystemExit(main())
