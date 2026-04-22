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

    def test_string_and_comment_noise_is_ignored(self):
        src = (
            '# s.parse("noise")\n'
            'prefix = "const x = s.parse(\\"noise\\");"\n'
            'value = s.parse("ok")\n'
        )
        islands = extract_islands(src, "python")
        assert [island.virtual_content for island in islands] == ["ok"]

    def test_template_literal_noise_is_ignored(self):
        src = (
            'const template = `const x = s.parse("noise")`;\n'
            'const value = s.parse("ok");\n'
        )
        islands = extract_islands(src, "typescript")
        assert [island.virtual_content for island in islands] == ["ok"]

    def test_rust_raw_string_noise_is_ignored(self):
        src = (
            'let noise = r#"strling::parse!("noise")"#;\n'
            'let value = strling::parse!("ok");\n'
        )
        islands = extract_islands(src, "rust")
        assert [island.virtual_content for island in islands] == ["ok"]

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

    def test_language_for_uri_extended_suffixes(self):
        # Phase 1-3 polyglot expansion: every newly registered host language
        # must be discoverable by suffix without code changes.
        assert language_for_uri("file:///x.c") == "c"
        assert language_for_uri("file:///x.h") == "c"
        assert language_for_uri("file:///x.cpp") == "cpp"
        assert language_for_uri("file:///x.hpp") == "cpp"
        assert language_for_uri("file:///x.cc") == "cpp"
        assert language_for_uri("file:///x.cs") == "csharp"
        assert language_for_uri("file:///x.fs") == "fsharp"
        assert language_for_uri("file:///x.go") == "go"
        assert language_for_uri("file:///x.kt") == "kotlin"
        assert language_for_uri("file:///x.swift") == "swift"
        assert language_for_uri("file:///x.dart") == "dart"
        assert language_for_uri("file:///x.php") == "php"
        assert language_for_uri("file:///x.rb") == "ruby"
        assert language_for_uri("file:///x.pl") == "perl"
        assert language_for_uri("file:///x.lua") == "lua"
        assert language_for_uri("file:///x.R") == "r"


# --------------------------------------------------------------------------- #
# Polyglot expansion — Phase 1-3 host languages                               #
# --------------------------------------------------------------------------- #


class TestPolyglotBoundaries:
    """Per-language extraction smoke tests for the 13 new host languages."""

    def test_c_strling_parse(self):
        src = 'STRlingParseResult* r = strling_parse("Email()");\n'
        islands = extract_islands(src, "c")
        assert [i.virtual_content for i in islands] == ["Email()"]

    def test_cpp_namespaced_parse(self):
        src = 'auto p = strling::parse("Phone()");\n'
        islands = extract_islands(src, "cpp")
        assert [i.virtual_content for i in islands] == ["Phone()"]

    def test_cpp_raw_string_noise_is_ignored(self):
        src = (
            'const char* fixture = R"json(strling::parse("noise"))json";\n'
            'auto value = strling::parse("ok");\n'
        )
        islands = extract_islands(src, "cpp")
        assert [i.virtual_content for i in islands] == ["ok"]

    def test_cpp_pattern_inside_raw_string_extracts(self):
        src = 'auto p = strling::parse(R"dsl(Email())dsl");\n'
        islands = extract_islands(src, "cpp")
        assert [i.virtual_content for i in islands] == ["Email()"]

    def test_csharp_parse(self):
        src = 'var p = STRling.Parse("URL()");\n'
        islands = extract_islands(src, "csharp")
        assert [i.virtual_content for i in islands] == ["URL()"]

    def test_fsharp_nested_block_comment_is_ignored(self):
        src = (
            '(* outer (* inner STRling.parse("noise") *) still in *)\n'
            'let p = STRling.parse("ok")\n'
        )
        islands = extract_islands(src, "fsharp")
        assert [i.virtual_content for i in islands] == ["ok"]

    def test_go_backtick_raw_string_noise_is_ignored(self):
        src = 'var fixture = `strling.Parse("noise")`\np, _ := strling.Parse("ok")\n'
        islands = extract_islands(src, "go")
        assert [i.virtual_content for i in islands] == ["ok"]

    def test_kotlin_parse(self):
        src = 'val p = STRling.parse("Word()+")\n'
        islands = extract_islands(src, "kotlin")
        assert [i.virtual_content for i in islands] == ["Word()+"]

    def test_swift_hashed_string_noise_is_ignored(self):
        src = (
            'let noise = #"STRling.parse(\\"noise\\")"#\n'
            'let value = STRling.parse("ok")\n'
        )
        islands = extract_islands(src, "swift")
        assert [i.virtual_content for i in islands] == ["ok"]

    def test_dart_parse(self):
        src = 'final p = STRling.parse("Email()");\n'
        islands = extract_islands(src, "dart")
        assert [i.virtual_content for i in islands] == ["Email()"]

    def test_php_hash_comment_noise_is_ignored(self):
        src = (
            "<?php\n"
            '# STRling::parse("noise")\n'
            '// STRling::parse("noise")\n'
            '$p = STRling::parse("ok");\n'
        )
        islands = extract_islands(src, "php")
        assert [i.virtual_content for i in islands] == ["ok"]

    def test_ruby_hash_comment_noise_is_ignored(self):
        src = '# STRling.parse("noise")\np = STRling.parse("ok")\n'
        islands = extract_islands(src, "ruby")
        assert [i.virtual_content for i in islands] == ["ok"]

    def test_perl_arrow_form(self):
        src = 'my $p = STRling->parse("Number()");\n'
        islands = extract_islands(src, "perl")
        assert [i.virtual_content for i in islands] == ["Number()"]

    def test_lua_long_bracket_comment_is_ignored(self):
        src = '--[[ strling.parse("noise") ]]\nlocal p = strling.parse("ok")\n'
        islands = extract_islands(src, "lua")
        assert [i.virtual_content for i in islands] == ["ok"]

    def test_lua_long_bracket_string_extracts(self):
        src = "local p = strling.parse([[Email()]])\n"
        islands = extract_islands(src, "lua")
        assert [i.virtual_content for i in islands] == ["Email()"]

    def test_r_parse(self):
        src = 'pat <- strling_parse("URL()")\n'
        islands = extract_islands(src, "r")
        assert [i.virtual_content for i in islands] == ["URL()"]

    def test_polyglot_clamping_holds_for_all_new_languages(self):
        cases = [
            ("c", 'p = strling_parse("ab");'),
            ("cpp", 'p = strling::parse("ab");'),
            ("csharp", 'var p = STRling.Parse("ab");'),
            ("fsharp", 'let p = STRling.parse("ab")'),
            ("go", 'p, _ := strling.Parse("ab")'),
            ("kotlin", 'val p = STRling.parse("ab")'),
            ("swift", 'let p = STRling.parse("ab")'),
            ("dart", 'final p = STRling.parse("ab");'),
            ("php", '$p = STRling::parse("ab");'),
            ("ruby", 'p = STRling.parse("ab")'),
            ("perl", 'my $p = STRling::parse("ab");'),
            ("lua", 'local p = strling.parse("ab")'),
            ("r", 'pat <- strling_parse("ab")'),
        ]
        for lang, src in cases:
            islands = extract_islands(src, lang)
            assert len(islands) == 1, f"no island extracted for {lang}: {src!r}"
            island = islands[0]
            assert island.virtual_content == "ab", f"bad content for {lang}"
            # Clamp past EOL → land on the last raw character index.
            clamped = island.to_host(0, 999)
            assert clamped.character == island.host_start.character + 2, (
                f"clamp failed for {lang}: got {clamped!r}"
            )


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

    def test_projection_clamps_past_end(self):
        src = 'x=s.parse("ab")'
        island = extract_islands(src, "typescript")[0]
        assert island.to_host(0, 99) == HostPosition(0, 13)

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

    def test_multiline_projection_clamps_to_line_end(self):
        src = 'x = s.parse("""\nfoo\nbar\n""")\n'
        island = extract_islands(src, "python")[0]
        assert island.to_host(1, 99) == HostPosition(1, 3)

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
