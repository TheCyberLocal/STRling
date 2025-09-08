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

    # -- Directives --

    def _parse_directives(self, text: str) -> Tuple[Flags, str]:
        flags = Flags()
        consumed = 0
        for line in text.splitlines(keepends=True):
            striped = line.strip()
            # Skip leading blank lines or comments
            if striped == "" or striped.startswith("#"):
                consumed += len(line)
                continue
            if striped.startswith("%flags"):
                consumed += len(line)
                rest = striped[6:].strip()
                letters = rest.replace(",", " ").replace("[", "").replace("]", "")
                flags = Flags.from_letters(letters)
                continue
            if striped.startswith("%"):
                consumed += len(line)
                continue
            # First non-directive content line -> stop
            break
        return flags, text[consumed:]

    def parse(self) -> Node:
        node = self.parse_alt()
        self.cur.skip_ws_and_comments()
        if not self.cur.eof():
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
        while True:
            self.cur.skip_ws_and_comments()
            ch = self.cur.peek()
            if ch == "" or ch in ")|":
                break

            atom = self.parse_atom()

            # Don't apply quantifiers to anchors
            if isinstance(atom, Anchor):
                parts.append(atom)
                continue

            quantified_atom = self.parse_quant_if_any(atom)
            parts.append(quantified_atom)

        if len(parts) == 1:
            return parts[0]
        return Seq(parts)

    def parse_quant_if_any(self, child: Node) -> Node:
        cur = self.cur
        ch = cur.peek()

        min_val, max_val, mode = None, None, "Greedy"

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
                cur.i = save  # Backtrack if it wasn't a quantifier

        # If we didn't parse a quantifier, we're done
        if min_val is None:
            return child

        # Now check for lazy/possessive modifiers
        nxt = cur.peek()
        if nxt == "?":
            mode = "Lazy"
            cur.take()
        elif nxt == "+":
            mode = "Possessive"
            cur.take()

        return Quant(child, min_val, max_val if max_val is not None else "Inf", mode)

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
        assert cur.take() == "\\"
        nxt = cur.peek()
        # Backref by index \1.. (but not \0)
        if nxt.isdigit() and nxt != "0":
            num = self._read_decimal()
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
                raise ParseError(r"Expected '<' after \k", cur.i)
            name = self._read_ident_until(">")
            if not cur.match(">"):
                raise ParseError("Unterminated named backref", cur.i)
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
        # Escaped literal or hex/unicode/null escapes -> literal
        if nxt == "x":
            return Lit(self._parse_hex_escape())
        if nxt == "u" or nxt == "U":
            return Lit(self._parse_unicode_escape())
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

    def _parse_hex_escape(self) -> str:
        cur = self.cur
        assert cur.take() == "x"
        if cur.match("{"):
            hexs = ""
            while re.match(r"[0-9A-Fa-f]", cur.peek() or ""):
                hexs += cur.take()
            if not cur.match("}"):
                raise ParseError("Unterminated \\x{...}", cur.i)
            cp = int(hexs or "0", 16)
            return chr(cp)
        # \xHH
        h1 = cur.take()
        h2 = cur.take()
        if not (
            re.match(r"[0-9A-Fa-f]", h1 or "") and re.match(r"[0-9A-Fa-f]", h2 or "")
        ):
            raise ParseError("Invalid \\xHH escape", cur.i)
        return chr(int(h1 + h2, 16))

    def _parse_unicode_escape(self) -> str:
        cur = self.cur
        tp = cur.take()  # u or U
        if tp == "u" and cur.match("{"):
            hexs = ""
            while re.match(r"[0-9A-Fa-f]", cur.peek() or ""):
                hexs += cur.take()
            if not cur.match("}"):
                raise ParseError("Unterminated \\u{...}", cur.i)
            return chr(int(hexs or "0", 16))
        if tp == "U":
            hexs = ""
            for _ in range(8):
                ch = cur.take()
                if not re.match(r"[0-9A-Fa-f]", ch or ""):
                    raise ParseError("Invalid \\UHHHHHHHH", cur.i)
                hexs += ch
            return chr(int(hexs, 16))
        # \uHHHH
        hexs = ""
        for _ in range(4):
            ch = cur.take()
            if not re.match(r"[0-9A-Fa-f]", ch or ""):
                raise ParseError("Invalid \\uHHHH", cur.i)
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
                cur.take()
                nxt = cur.peek()
                if nxt in "dDwWsS":
                    return ClassEscape(cur.take())
                if nxt in "pP":
                    tp = cur.take()
                    if not cur.match("{"):
                        raise ParseError("Expected { after \\p/\\P", cur.i)
                    prop = self._read_until("}")
                    if not cur.match("}"):
                        raise ParseError("Unterminated \\p{...}", cur.i)
                    return ClassEscape(tp, prop)
                if nxt in ("x", "u", "U", "0"):
                    if nxt == "x":
                        ch = self._parse_hex_escape()
                    elif nxt in ("u", "U"):
                        ch = self._parse_unicode_escape()
                    else:
                        cur.take()
                        ch = "\x00"
                    return ClassLiteral(ch)
                # identity escape -> literal
                return ClassLiteral(cur.take())
            # regular literal
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

        # FIX: Explicitly reject inline modifiers like `(?i)` which are not supported.
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
