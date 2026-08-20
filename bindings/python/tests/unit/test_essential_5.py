"""Registry-linked proof for the five canonical standard-library helpers."""

import json
from pathlib import Path

from STRling import simply


def test_essential_helpers_delegate_to_canonical_simply_requests() -> None:
    essential_5 = json.loads(
        (
            Path(__file__).resolve().parents[4] / "spec" / "stdlib" / "essential_5.json"
        ).read_text(encoding="utf-8")
    )
    helpers = (
        simply.date_time(),
        simply.email(),
        simply.ip(),
        simply.url(),
        simply.uuid(),
    )
    assert simply.STDLIB_HELPER_IDS == (
        "stdlib.date_time",
        "stdlib.email",
        "stdlib.ip",
        "stdlib.url",
        "stdlib.uuid",
    )
    assert [
        helper.build_request(
            {
                "requested_outputs": ["semantic"],
                "compiler_options": {
                    "partial_semantics": "forbid",
                    "diagnostic_policy": {"minimum_severity": "hint"},
                },
            }
        )["steps"][0]["arguments"]["helper_id"]
        for helper in helpers
    ] == list(simply.STDLIB_HELPER_IDS)
    assert set(essential_5["patterns"]) == {"dateTime", "email", "ip", "url", "uuid"}
