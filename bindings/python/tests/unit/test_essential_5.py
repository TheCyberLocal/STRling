"""Conformance tests for the Simply standard library "Essential 5" patterns.

The fixtures defined in ``spec/stdlib/essential_5.json`` are the cross-binding
source of truth — every binding's implementation must satisfy the same
valid/invalid expectations.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

import STRling.simply as s

SPEC_PATH = Path(__file__).resolve().parents[4] / "spec" / "stdlib" / "essential_5.json"
SPEC = json.loads(SPEC_PATH.read_text())


def _full(pattern) -> re.Pattern[str]:
    return re.compile("^(?:" + str(pattern) + ")$")


@pytest.mark.parametrize("text", SPEC["patterns"]["email"]["fixtures"]["valid"])
def test_email_accepts_valid(text: str) -> None:
    assert _full(s.email()).match(text)


@pytest.mark.parametrize("text", SPEC["patterns"]["email"]["fixtures"]["invalid"])
def test_email_rejects_invalid(text: str) -> None:
    assert not _full(s.email()).match(text)


@pytest.mark.parametrize("text", SPEC["patterns"]["url"]["fixtures"]["valid"])
def test_url_accepts_valid(text: str) -> None:
    assert _full(s.url()).match(text)


@pytest.mark.parametrize("text", SPEC["patterns"]["url"]["fixtures"]["invalid"])
def test_url_rejects_invalid(text: str) -> None:
    assert not _full(s.url()).match(text)


@pytest.mark.parametrize("text", SPEC["patterns"]["uuid"]["fixtures"]["valid_default"])
def test_uuid_accepts_valid(text: str) -> None:
    assert _full(s.uuid()).match(text)


@pytest.mark.parametrize(
    "text", SPEC["patterns"]["uuid"]["fixtures"]["invalid_default"]
)
def test_uuid_rejects_invalid(text: str) -> None:
    assert not _full(s.uuid()).match(text)


@pytest.mark.parametrize("text", SPEC["patterns"]["uuid"]["fixtures"]["valid_v4"])
def test_uuid_v4_accepts_valid(text: str) -> None:
    assert _full(s.uuid(4)).match(text)


@pytest.mark.parametrize("text", SPEC["patterns"]["uuid"]["fixtures"]["invalid_v4"])
def test_uuid_v4_rejects_invalid(text: str) -> None:
    assert not _full(s.uuid(4)).match(text)


@pytest.mark.parametrize("text", SPEC["patterns"]["ip"]["fixtures"]["valid_v4"])
def test_ip_v4_accepts_valid(text: str) -> None:
    assert _full(s.ip(4)).match(text)


@pytest.mark.parametrize("text", SPEC["patterns"]["ip"]["fixtures"]["invalid_v4"])
def test_ip_v4_rejects_invalid(text: str) -> None:
    assert not _full(s.ip(4)).match(text)


@pytest.mark.parametrize("text", SPEC["patterns"]["ip"]["fixtures"]["valid_v6"])
def test_ip_v6_accepts_valid(text: str) -> None:
    assert _full(s.ip(6)).match(text)


@pytest.mark.parametrize("text", SPEC["patterns"]["ip"]["fixtures"]["invalid_v6"])
def test_ip_v6_rejects_invalid(text: str) -> None:
    assert not _full(s.ip(6)).match(text)


@pytest.mark.parametrize(
    "text",
    SPEC["patterns"]["ip"]["fixtures"]["valid_v4"]
    + SPEC["patterns"]["ip"]["fixtures"]["valid_v6"],
)
def test_ip_default_accepts_either(text: str) -> None:
    assert _full(s.ip()).match(text)


@pytest.mark.parametrize("text", SPEC["patterns"]["dateTime"]["fixtures"]["valid"])
def test_date_time_accepts_valid(text: str) -> None:
    assert _full(s.date_time()).match(text)


@pytest.mark.parametrize("text", SPEC["patterns"]["dateTime"]["fixtures"]["invalid"])
def test_date_time_rejects_invalid(text: str) -> None:
    assert not _full(s.date_time()).match(text)
