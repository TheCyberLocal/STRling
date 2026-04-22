"""Unit tests for the Island Grammar extractor.

These tests exercise the regex-based boundary sweep, the raw literal scanner,
and the coordinate-mirror algebra. They run without any LSP transport so they
are safe to execute under plain ``pytest``.
"""

from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from island_extractor import (  # noqa: E402
    Island,
    HostPosition,
    extract_islands,
    extract_islands_for_uri,
    language_for_uri,
)


# --------------------------------------------------------------------------- #
# Boundary detection                                                          #
# --------------------------------------------------------------------------- #


class TestBoundaryDetection:
    def test_typescript_simply_parse(self):
        src = 'const re = strl.simply.parse("Email()");\n'
        islands = extract_islands(src, "typescript")
        assert len(islands) == 1
        assert islands[0].virtual_content == "Email()"
        assert islands[0].host_start == HostPosition(0, 30)

    def test_typescript_template_literal(self):
        src = "const re = simply.parse(`Word()+`);\n"
        islands = extract_islands(src, "typescript")
        assert len(islands) == 1
        assert islands[0].virtual_content == "Word()+"

    def test_python_s_parse(self):
        src = 'pat = s.parse("Number()")\n'
        islands = extract_islands(src, "python")
        assert len(islands) == 1
        assert islands[0].virtual_content == "Number()"

    def test_python_triple_quoted(self):
        src = 'pat = s.parse("""\nEmail()\n""")\n'
        islands = extract_islands(src, "python")
        assert len(islands) == 1
        # Triple-quoted content keeps the leading newline intact.
        assert islands[0].virtual_content == "\nEmail()\n"

    def test_rust_macro(self):
        src = 'let re = strling::parse!("URL()");\n'
        islands = extract_islands(src, "rust")
        assert len(islands) == 1
        assert islands[0].virtual_content == "URL()"

    def test_java_static_call(self):
        src = 'Pattern p = STRling.parse("Phone()");\n'
        islands = extract_islands(src, "java")
        assert len(islands) == 1
        assert islands[0].virtual_content == "Phone()"

    def test_unknown_language_returns_empty(self):
        assert extract_islands("anything", "cobol") == []

    def test_no_boundary_no_islands(self):
        assert extract_islands("const x = 'plain string';", "typescript") == []

    def test_uri_dispatch(self):
        src = 'const x = s.parse("a")'
        assert extract_islands_for_uri(src, "file:///foo.ts")[0].virtual_content == "a"
        assert extract_islands_for_uri(src, "file:///foo.unknown") == []

    def test_language_for_uri(self):
        assert language_for_uri("file:///x.PY") == "python"
        assert language_for_uri("file:///x.tsx") == "typescript"
        assert language_for_uri("file:///x.rs") == "rust"
        assert language_for_uri("file:///x.java") == "java"
        assert language_for_uri("file:///x.txt") is None


# --------------------------------------------------------------------------- #
# Coordinate mirror                                                           #
# --------------------------------------------------------------------------- #


class TestCoordinateMirror:
    def test_single_line_projection_exact(self):
        src = 'x=s.parse("ab")'
        # `x=s.parse(` = 10 chars, `"` at col 10, content `ab` starts col 11.
        island = extract_islands(src, "typescript")[0]
        assert island.host_start == HostPosition(0, 11)
        assert island.to_host(0, 0) == HostPosition(0, 11)
        assert island.to_host(0, 1) == HostPosition(0, 12)

    def test_multiline_projection(self):
        src = 'x = s.parse("""\nfoo\nbar\n""")\n'
        # Triple-quoted opens at col 12, closing-style. content starts at
        # col 15 of line 0. Then newline → line 1 col 0, etc.
        island = extract_islands(src, "python")[0]
        # virtual content: "\nfoo\nbar\n"
        assert island.host_start == HostPosition(0, 15)
        # vd line 0 corresponds to host line 0 after the """ delimiter
        assert island.to_host(0, 0) == HostPosition(0, 15)
        # vd line 1 char 1 -> host line 1 char 1 (foo)
        assert island.to_host(1, 1) == HostPosition(1, 1)
        # vd line 2 char 2 -> host line 2 char 2 (bar)
        assert island.to_host(2, 2) == HostPosition(2, 2)

    def test_inverse_projection(self):
        src = 'x=s.parse("ab")'
        island = extract_islands(src, "typescript")[0]
        assert island.from_host(0, 11) == (0, 0)
        assert island.from_host(0, 12) == (0, 1)
        # Outside the island
        assert island.from_host(0, 0) is None
        assert island.from_host(5, 0) is None

    def test_contains_host_inclusive(self):
        src = 'x=s.parse("ab")'
        island = extract_islands(src, "typescript")[0]
        assert island.contains_host(0, 11) is True
        assert (
            island.contains_host(0, 13) is True
        )  # one past last char (end-exclusive end)
        assert island.contains_host(0, 14) is False


# --------------------------------------------------------------------------- #
# Robustness                                                                  #
# --------------------------------------------------------------------------- #


class TestRobustness:
    def test_unterminated_literal_skipped(self):
        src = 'x = s.parse("never closed\n'
        assert extract_islands(src, "python") == []

    def test_escape_preserves_length(self):
        # Escape should be skipped for matching purposes but characters
        # remain in the virtual content (no unfolding).
        src = r'x = s.parse("a\"b")'
        islands = extract_islands(src, "python")
        assert len(islands) == 1
        assert islands[0].virtual_content == r"a\"b"

    def test_multiple_islands_in_one_file(self):
        src = 'a = s.parse("one")\nb = s.parse("two")\n'
        islands = extract_islands(src, "python")
        assert [i.virtual_content for i in islands] == ["one", "two"]
        assert islands[0].host_start.line == 0
        assert islands[1].host_start.line == 1


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))
