"""
STRling v3 — Parser (Sprint 3)
Hand-rolled recursive-descent parser for the STRling regex-like DSL.
Produces AST nodes defined in nodes.py and a Base TargetArtifact.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple, Union, cast
import re

from .nodes import (
    Flags,
    Node,
    Alt,
    Seq,
    Lit,
    Dot,
    Anchor,
    CharClass,
    ClassLiteral,
    ClassRange,
    ClassEscape,
    Quant,
    Group,
    Backref,
    Look,
    ClassItem,
)


# ---------------- Errors ----------------
class ParseError(Exception):
    def __init__(self, message: str, pos: int):
        super().__init__(f"{message} at {pos}")
        self.message = message
        self.pos = pos


# ---------------- Lexer helpers ----------------
@dataclass
class Cursor:
    text: str
    i: int = 0
    extended_mode: bool = False
    in_class: int = 0  # nesting count for char classes

    def eof(self) -> bool:
        return self.i >= len(self.text)

    def peek(self, n: int = 0) -> str:
        j = self.i + n
        return "" if j >= len(self.text) else self.text[j]

    def take(self) -> str:
        if self.eof():
            return ""
        ch = self.text[self.i]
        self.i += 1
        return ch

    def match(self, s: str) -> bool:
        if self.text.startswith(s, self.i):
            self.i += len(s)
            return True
        return False

    def skip_ws_and_comments(self) -> None:
        if not self.extended_mode or self.in_class > 0:
            return
        # In free-spacing mode, ignore spaces/tabs/newlines and #-to-EOL comments
        while not self.eof():
            ch = self.peek()
            if ch in " \t\r\n":
                self.i += 1
                continue
            if ch == "#":
                # skip comment to end of line
                while not self.eof() and self.peek() not in "\r\n":
                    self.i += 1
                continue
            break


# ---------------- Parser ----------------
class Parser:
    def __init__(self, text: str):
        # Extract directives first
        self.flags, self.src = self._parse_directives(text)
        self.cur = Cursor(self.src, 0, self.flags.extended, 0)
        self._cap_count: int = 0
        self._cap_names: set[str] = set()
        self.CONTROL_ESCAPES = {
            "n": "\n",
            "r": "\r",
            "t": "\t",
            "f": "\f",
            "v": "\v",
        }

    # -- Directives --

    def _parse_directives(self, text: str) -> Tuple[Flags, str]:
        flags = Flags()
        lines = text.splitlines(keepends=True)
        pattern_lines: List[str] = []
        for line in lines:
            striped = line.strip()
            # Skip leading blank lines or comments
            if striped == "" or striped.startswith("#"):
                continue
            if striped.startswith("%flags"):
                rest = striped[6:].strip()
                letters = rest.replace(",", " ").replace("[", "").replace("]", "")
                flags = Flags.from_letters(letters)
                continue
            if striped.startswith("%"):
                continue
            # All other lines are pattern content
            pattern_lines.append(line)
        # Join all pattern lines, preserving original whitespace and newlines
        pattern = "".join(pattern_lines)
        return flags, pattern

    def parse(self) -> Node:
        node = self.parse_alt()
        self.cur.skip_ws_and_comments()
        if not self.cur.eof():
            if self.cur.peek() == "|":
                # Alternation must have a right-hand side
                raise ParseError("Alternation lacks right-hand side", self.cur.i)
            else:
                raise ParseError("Unexpected trailing input", self.cur.i)
        return node

    # alt := seq ('|' seq)+ | seq
    def parse_alt(self) -> Node:
        branches: List[Node] = [self.parse_seq()]
        self.cur.skip_ws_and_comments()
        while self.cur.peek() == "|":
            self.cur.take()
            self.cur.skip_ws_and_comments()
            branches.append(self.parse_seq())
            self.cur.skip_ws_and_comments()
        if len(branches) == 1:
            return branches[0]
        return Alt(branches)

    # seq := { term }
    # FIX #1: The logic from the old `parse_term` was moved directly into `parse_seq`.
    # This resolves the core bug where the parser was incorrectly associating
    # quantifiers with entire sequences instead of individual atoms.
    def parse_seq(self) -> Node:
        parts: List[Node] = []
        # Track whether the previous atom had a failed quantifier parse to prevent coalescing across that boundary
        prev_had_failed_quant = False
        
        while True:
            self.cur.skip_ws_and_comments()
            ch = self.cur.peek()
            # Stop parsing sequence if we hit end, closing paren, or alternation pipe
            if ch == "" or ch in ")|":
                break

            # Parse the fundamental unit (literal, class, group, escape, etc.)
            atom = self.parse_atom()

            # Anchors cannot be quantified, add directly and continue
            if isinstance(atom, Anchor):
                parts.append(atom)
                prev_had_failed_quant = False
                continue

            # Parse any quantifier (*, +, ?, {m,n}) that might follow the atom
            # This returns (quantified_atom, had_failed_quant_parse)
            quantified_atom, had_failed_quant_parse = self.parse_quant_if_any(atom)
            
            # Coalesce adjacent Lit nodes: if the new atom is a Lit and the last part
            # is also a Lit, merge them into a single Lit with concatenated values.
            # However, don't coalesce if:
            # 1. The previous atom had a failed quantifier parse (semantic boundary)
            # 2. The current Lit is a digit and previous Lit ends with backslash (to avoid \digit ambiguity)
            # 3. The previous part is a Backref (keep digit literals separate)
            avoid_digit_after_backslash = (
                isinstance(quantified_atom, Lit) and
                len(quantified_atom.value) == 1 and
                quantified_atom.value.isdigit() and
                len(parts) > 0 and
                isinstance(parts[-1], Lit) and
                len(parts[-1].value) > 0 and
                parts[-1].value[-1] == "\\"
            )
            
            # Don't coalesce after a Backref to keep the digit literals separate
            prev_is_backref = len(parts) > 0 and isinstance(parts[-1], Backref)
            
            should_coalesce = (
                isinstance(quantified_atom, Lit) and 
                len(parts) > 0 and 
                isinstance(parts[-1], Lit) and
                not prev_had_failed_quant and
                not avoid_digit_after_backslash and
                not prev_is_backref
            )
            
            if should_coalesce:
                parts[-1] = Lit(parts[-1].value + quantified_atom.value)
            else:
                parts.append(quantified_atom)
            
            prev_had_failed_quant = had_failed_quant_parse

        # If the sequence ended up being just one (potentially quantified) atom, return it directly
        if len(parts) == 1:
            return parts[0]
        # Otherwise, return a Sequence node containing all parts
        return Seq(parts)

    def parse_quant_if_any(self, child: Node) -> Tuple[Node, bool]:
        """
        Parse a quantifier if present and return (quantified_node, had_failed_quant_parse).
        had_failed_quant_parse is True if we started parsing a brace quantifier but had to backtrack.
        """
        cur = self.cur
        ch = cur.peek()

        min_val, max_val, mode = None, None, "Greedy"
        had_failed_quant_parse = False

        if ch == "*":
            min_val, max_val = 0, "Inf"
            cur.take()
        elif ch == "+":
            min_val, max_val = 1, "Inf"
            cur.take()
        elif ch == "?":
            min_val, max_val = 0, 1
            cur.take()
        elif ch == "{":
            save = cur.i
            # This function returns (min, max, mode)
            m, n, parsed_mode = self.parse_brace_quant()
            if m is not None:
                min_val, max_val, mode = m, n, parsed_mode
            else:
                # We attempted to parse a brace quantifier but failed
                had_failed_quant_parse = True
                cur.i = save  # Backtrack if it wasn't a quantifier

        # If we didn't parse a quantifier, we're done
        if min_val is None:
            return child, had_failed_quant_parse

        # Now check for lazy/possessive modifiers
        nxt = cur.peek()
        if nxt == "?":
            mode = "Lazy"
            cur.take()
        elif nxt == "+":
            mode = "Possessive"
            cur.take()

        return Quant(child, min_val, max_val if max_val is not None else "Inf", mode), had_failed_quant_parse

    def parse_brace_quant(self) -> Tuple[Optional[int], Optional[Union[int, str]], str]:
        cur = self.cur
        if not cur.match("{"):
            return None, None, "Greedy"
        # Parse integers
        m = self._read_int_optional()
        if m is None:
            # This is not a quantifier, it's a literal '{'. Backtrack.
            return None, None, "Greedy"
        if cur.match(","):
            n = self._read_int_optional()
            if not cur.match("}"):
                raise ParseError("Unterminated {m,n}", cur.i)
            if n is None:
                mmin, mmax = m, "Inf"
            else:
                mmin, mmax = m, n
        else:
            if not cur.match("}"):
                raise ParseError("Unterminated {n}", cur.i)
            mmin, mmax = m, m
        mode = "Greedy"
        # Note: The lazy/possessive modifier is now handled in parse_quant_if_any
        return mmin, mmax, mode

    def _read_int_optional(self) -> Optional[int]:
        cur = self.cur
        s = ""
        while cur.peek().isdigit():
            s += cur.take()
        return int(s) if s != "" else None

    # ---- atom ----
    def parse_atom(self) -> Node:
        cur = self.cur
        cur.skip_ws_and_comments()
        ch = cur.peek()
        if ch == ".":
            cur.take()
            return Dot()
        if ch == "^":
            cur.take()
            return Anchor("Start")
        if ch == "$":
            cur.take()
            return Anchor("End")
        if ch == "(":
            return self.parse_group_or_look()
        if ch == "[":
            return self.parse_char_class()
        if ch == "\\":
            return self.parse_escape_atom()
        # literal
        if ch in "|)":
            raise ParseError("Unexpected token", cur.i)
        return Lit(self._take_literal_char())

    # literal character outside special set
    def _take_literal_char(self) -> str:
        return self.cur.take()

    # ---- escapes and atoms formed by escapes ----
    def parse_escape_atom(self) -> Node:
        cur = self.cur
        start_pos = cur.i  # Save position at start of escape
        assert cur.take() == "\\"
        nxt = cur.peek()
        # Backref by index \1.. (but not \0)
        if nxt.isdigit() and nxt != "0":
            num = self._read_decimal()
            if num > self._cap_count:
                raise ParseError(f"Backreference to undefined group \\{num}", start_pos)
            return Backref(byIndex=num)
        # Anchors \b \B \A \Z \z
        if nxt in ("b", "B", "A", "Z", "z"):
            ch = cur.take()
            if ch == "b":
                return Anchor("WordBoundary")
            if ch == "B":
                return Anchor("NotWordBoundary")
            if ch == "A":
                return Anchor("AbsoluteStart")
            if ch == "Z":
                return Anchor("EndBeforeFinalNewline")
            if ch == "z":
                return Anchor("AbsoluteEnd")
        # \k<name> named backref
        if nxt == "k":
            cur.take()
            if not cur.match("<"):
                raise ParseError(r"Expected '<' after \k", start_pos)
            name = self._read_ident_until(">")
            if not cur.match(">"):
                raise ParseError("Unterminated named backref", start_pos)
            if name not in self._cap_names:
                raise ParseError(f"Backreference to undefined group <{name}>", start_pos)
            return Backref(byName=name)
        # Shorthand classes \d \D \w \W \s \S or property \p{..} \P{..}
        if nxt in "dDwWsS":
            cur.take()
            return CharClass(False, [ClassEscape(nxt)])
        if nxt in "pP":
            tp = cur.take()
            if not cur.match("{"):
                raise ParseError("Expected { after \\p/\\P", cur.i)
            prop = self._read_until("}")
            if not cur.match("}"):
                raise ParseError("Unterminated \\p{...}", cur.i)
            return CharClass(False, [ClassEscape(tp, prop)])
        # Core control escapes \n \t \r \f \v
        if nxt in self.CONTROL_ESCAPES:
            ch = cur.take()
            return Lit(self.CONTROL_ESCAPES[ch])
        # Escaped literal or hex/unicode/null escapes -> literal
        if nxt == "x":
            return Lit(self._parse_hex_escape(start_pos))
        if nxt == "u" or nxt == "U":
            return Lit(self._parse_unicode_escape(start_pos))
        if nxt == "0":
            cur.take()
            return Lit("\x00")
        # Identity escape: treat next char literally
        ch = cur.take()
        return Lit(ch)

    def _read_decimal(self) -> int:
        cur = self.cur
        s = ""
        while cur.peek().isdigit():
            s += cur.take()
        return int(s) if s else 0

    def _read_ident_until(self, end: str) -> str:
        cur = self.cur
        s = ""
        while not cur.eof() and cur.peek() != end:
            s += cur.take()
        return s

    def _read_until(self, end: str) -> str:
        return self._read_ident_until(end)

    def _parse_hex_escape(self, start_pos: int) -> str:
        cur = self.cur
        assert cur.take() == "x"
        if cur.match("{"):
            hexs = ""
            while re.match(r"[0-9A-Fa-f]", cur.peek() or ""):
                hexs += cur.take()
            if not cur.match("}"):
                # Use start_pos for error reporting
                raise ParseError("Unterminated \\x{...}", start_pos)
            cp = int(hexs or "0", 16)
            return chr(cp)
        # \xHH
        h1 = cur.take()
        h2 = cur.take()
        if not (
            re.match(r"[0-9A-Fa-f]", h1 or "") and re.match(r"[0-9A-Fa-f]", h2 or "")
        ):
            raise ParseError("Invalid \\xHH escape", start_pos)
        return chr(int(h1 + h2, 16))

    def _parse_unicode_escape(self, start_pos: int) -> str:
        cur = self.cur
        tp = cur.take()  # u or U
        if tp == "u" and cur.match("{"):
            hexs = ""
            while re.match(r"[0-9A-Fa-f]", cur.peek() or ""):
                hexs += cur.take()
            if not cur.match("}"):
                raise ParseError("Unterminated \\u{...}", start_pos)
            return chr(int(hexs or "0", 16))
        if tp == "U":
            hexs = ""
            for _ in range(8):
                ch = cur.take()
                if not re.match(r"[0-9A-Fa-f]", ch or ""):
                    raise ParseError("Invalid \\UHHHHHHHH", start_pos)
                hexs += ch
            return chr(int(hexs, 16))
        # \uHHHH
        hexs = ""
        for _ in range(4):
            ch = cur.take()
            if not re.match(r"[0-9A-Fa-f]", ch or ""):
                raise ParseError("Invalid \\uHHHH", start_pos)
            hexs += ch
        return chr(int(hexs, 16))

    # ---- Character class ----
    def parse_char_class(self) -> CharClass:
        cur = self.cur
        assert cur.take() == "["
        start_pos = cur.i
        self.cur.in_class += 1
        neg = False
        items: List[ClassItem] = []
        if cur.peek() == "^":
            neg = True
            cur.take()
            start_pos = cur.i

        # helper: read one class item (escape or literal)
        def read_item() -> ClassItem:
            if cur.peek() == "\\":
                escape_start = cur.i  # Save position at start of escape
                cur.take()  # Consume the backslash
                nxt = cur.peek()
                # Handle standard shorthands \d \D etc.
                if nxt in "dDwWsS":
                    return ClassEscape(cur.take())
                # Handle unicode properties \p{...} \P{...}
                if nxt in "pP":
                    tp = cur.take()
                    if not cur.match("{"):
                        raise ParseError("Expected { after \\p/\\P", escape_start)
                    prop = self._read_until("}")
                    if not cur.match("}"):
                        raise ParseError("Unterminated \\p{...}", escape_start)
                    return ClassEscape(tp, prop)
                # Handle hex, unicode, null escapes -> literal char
                if nxt == "x":
                    ch = self._parse_hex_escape(escape_start)
                    return ClassLiteral(ch)
                if nxt in ("u", "U"):
                    ch = self._parse_unicode_escape(escape_start)
                    return ClassLiteral(ch)
                if nxt == "0":
                    cur.take()
                    return ClassLiteral("\x00")
                # Handle core control escapes \n, \t, \r, \f, \v
                # AND handle \b as backspace (0x08) INSIDE a class
                if nxt in self.CONTROL_ESCAPES:
                    ch_val = self.CONTROL_ESCAPES[cur.take()]
                    return ClassLiteral(ch_val)
                if nxt == "b":  # Special case: \b inside class is backspace
                    cur.take()
                    return ClassLiteral("\x08")
                # Identity escape: treat next char literally (e.g., \-, \^, \])
                return ClassLiteral(cur.take())
            # Regular literal character (not preceded by \)
            # Need special handling for ] and - if they aren't escaped
            ch = cur.peek()
            # If ] is encountered *after* the first char and *not* escaped, it closes the class.
            # This is handled in the main loop, so here we just take the literal.
            # If - is encountered *not* at start/end and *not* escaped, it denotes a range.
            # This is handled in the main loop, so here we just take the literal.
            return ClassLiteral(cur.take())

        while True:
            if cur.eof():
                self.cur.in_class -= 1
                raise ParseError("Unterminated character class", cur.i)

            # FIX #2: Correctly handle ']' as a literal at the start of a class.
            if cur.peek() == "]" and cur.i > start_pos:
                cur.take()
                self.cur.in_class -= 1
                return CharClass(neg, items)

            # Range handling: '-' makes a range only if previous is a literal and next isn't ']'
            if (
                cur.peek() == "-"
                and items
                and isinstance(items[-1], ClassLiteral)
                and cur.peek(1) != "]"
            ):
                # consume '-' and read the end item
                cur.take()
                end_item = read_item()
                if isinstance(end_item, ClassLiteral):
                    start_lit = cast(
                        ClassLiteral, items.pop()
                    )  # Explicitly cast for type checker
                    start_ch: str = start_lit.ch
                    end_ch: str = end_item.ch
                    items.append(ClassRange(start_ch, end_ch))
                else:
                    # Can't form range with a class escape; degrade to literals (“-” + end_item)
                    items.append(ClassLiteral("-"))
                    items.append(end_item)
                continue

            # General case: read one item
            items.append(read_item())

    # ---- Groups, lookarounds ----
    def parse_group_or_look(self) -> Node:
        cur = self.cur
        assert cur.take() == "("

        # Explicitly reject inline modifiers like `(?i)` which are not supported.
        if cur.peek() == "?" and cur.peek(1) in "imsx":
            raise ParseError("Inline modifiers `(?imsx)` are not supported", cur.i)

        # Non-capturing group
        if cur.match("?:"):
            body = self.parse_alt()
            if not cur.match(")"):
                raise ParseError("Unterminated group", cur.i)
            return Group(False, body)

        # IMPORTANT: Lookbehind tokens must be recognized BEFORE "?<name>"
        if cur.match("?<="):
            body = self.parse_alt()
            if not cur.match(")"):
                raise ParseError("Unterminated lookbehind", cur.i)
            return Look("Behind", False, body)

        if cur.match("?<!"):
            body = self.parse_alt()
            if not cur.match(")"):
                raise ParseError("Unterminated lookbehind", cur.i)
            return Look("Behind", True, body)

        # Named capturing group (?<name>...)
        if cur.match("?<"):
            name = self._read_until(">")
            if not cur.match(">"):
                raise ParseError("Unterminated group name", cur.i)
            self._cap_count += 1
            self._cap_names.add(name)
            body = self.parse_alt()
            if not cur.match(")"):
                raise ParseError("Unterminated group", cur.i)
            return Group(True, body, name=name)

        # Atomic group (?>...)
        if cur.match("?>"):
            body = self.parse_alt()
            if not cur.match(")"):
                raise ParseError("Unterminated atomic group", cur.i)
            return Group(False, body, atomic=True)

        # Lookahead (?=...) / (?!...)
        if cur.match("?="):
            body = self.parse_alt()
            if not cur.match(")"):
                raise ParseError("Unterminated lookahead", cur.i)
            return Look("Ahead", False, body)

        if cur.match("?!"):
            body = self.parse_alt()
            if not cur.match(")"):
                raise ParseError("Unterminated lookahead", cur.i)
            return Look("Ahead", True, body)

        # Capturing group (...)
        self._cap_count += 1
        body = self.parse_alt()
        if not cur.match(")"):
            raise ParseError("Unterminated group", cur.i)
        return Group(True, body)


# ---------------- Public API ----------------
def parse(src: str) -> Tuple[Flags, Node]:
    p = Parser(src)
    return p.flags, p.parse()


def parse_to_artifact(src: str) -> Dict[str, Any]:
    flags, root = parse(src)
    artifact: Dict[str, Any] = {
        "version": "1.0.0",
        "flags": flags.to_dict(),
        "root": root.to_dict(),
        "warnings": [],  # type: List[str]
        "errors": [],  # type: List[str]
    }
    return artifact
