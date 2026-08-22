#!/usr/bin/env python3
"""Compatibility entrypoint for the structured product-certification authority.

The historical Omega implementation inferred certification from runner prose.
That scanner has been retired. Existing ``audit`` callers now execute the
governed Full profile and derive both machine and human product evidence from
the resulting structured profile artifact.
"""

from __future__ import annotations

from pathlib import Path
from typing import Sequence

try:
    from tooling.product_certification import main as product_certification_main
except ModuleNotFoundError:  # Direct ``python tooling/audit_omega.py``.
    from product_certification import main as product_certification_main


ROOT = Path(__file__).resolve().parents[1]
ARTIFACT_PATH = ROOT / "target/certification/product-certification.json"
REPORT_PATH = ROOT / "target/certification/product-certification.md"


def delegated_arguments() -> Sequence[str]:
    """Return the single structured-authority invocation used by this shim."""

    return (
        "--run-profile",
        "--artifact",
        str(ARTIFACT_PATH),
        "--report",
        str(REPORT_PATH),
    )


def main() -> int:
    """Delegate without inspecting test names, stdout, stderr, or prose."""

    return product_certification_main(delegated_arguments())


if __name__ == "__main__":
    raise SystemExit(main())
