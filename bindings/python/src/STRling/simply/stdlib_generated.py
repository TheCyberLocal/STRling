"""Generated canonical standard-library wrappers for the Simply 1.1 Preview adapter."""

from __future__ import annotations

from typing import Final, Optional, Tuple

from STRling.simply.preview import SimplyPreviewBuilder, SimplyPreviewValue

STDLIB_SURFACE_SOURCE_SHA256: Final = (
    "01e11b07b902e18fd2b2e1f55a90ef8207350f4dc113174d04310b4dad525f16"
)
STDLIB_REGISTRY_VERSION: Final = "1.0.0"
STDLIB_HELPER_IDS: Final[Tuple[str, ...]] = (
    "stdlib.date_time",
    "stdlib.email",
    "stdlib.ip",
    "stdlib.url",
    "stdlib.uuid",
)


def date_time(
    builder: SimplyPreviewBuilder,
    step_id: str,
) -> SimplyPreviewValue:
    return builder.stdlib_helper(step_id, "stdlib.date_time", {})


def email(
    builder: SimplyPreviewBuilder,
    step_id: str,
) -> SimplyPreviewValue:
    return builder.stdlib_helper(step_id, "stdlib.email", {})


def ip(
    builder: SimplyPreviewBuilder,
    step_id: str,
    version: Optional[int] = None,
) -> SimplyPreviewValue:
    return builder.stdlib_helper(
        step_id,
        "stdlib.ip",
        {
            "version": version,
        },
    )


def url(
    builder: SimplyPreviewBuilder,
    step_id: str,
) -> SimplyPreviewValue:
    return builder.stdlib_helper(step_id, "stdlib.url", {})


def uuid(
    builder: SimplyPreviewBuilder,
    step_id: str,
    version: Optional[int] = None,
) -> SimplyPreviewValue:
    return builder.stdlib_helper(
        step_id,
        "stdlib.uuid",
        {
            "version": version,
        },
    )


__all__ = [
    "STDLIB_SURFACE_SOURCE_SHA256",
    "STDLIB_REGISTRY_VERSION",
    "STDLIB_HELPER_IDS",
    "date_time",
    "email",
    "ip",
    "url",
    "uuid",
]
