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
    ClassItem,  # <-- Import ClassItem from nodes.py
)

# Remove local ClassItem alias
# ClassItem = Union[ClassLiteral, ClassRange, ClassEscape]


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
    def parse_seq(self) -> Node:
        parts: List[Node] = []
        while True:
            self.cur.skip_ws_and_comments()
            ch = self.cur.peek()
            if ch == "" or ch in ")|":
                break
            parts.append(self.parse_term())
        if len(parts) == 1:
            return parts[0]
        return Seq(parts)

    # term := atom quant?
    def parse_term(self) -> Node:
        atom = self.parse_atom()
        self.cur.skip_ws_and_comments()
        return self.parse_quant_if_any(atom)

    def parse_quant_if_any(self, child: Node) -> Node:
        cur = self.cur
        ch = cur.peek()
        if ch in "*+?":
            mode = "Greedy"
            if ch == "*":
                q: Tuple[int, Union[int, str]] = (0, "Inf")
            elif ch == "+":
                q = (1, "Inf")
            else:
                q = (0, 1)
            cur.take()
            nxt = cur.peek()
            if nxt in "?+":
                mode = "Lazy" if nxt == "?" else "Possessive"
                cur.take()
            return Quant(child, q[0], q[1], mode)
        if ch == "{":
            save = cur.i
            mmin, mmax, mode = self.parse_brace_quant()
            if mmin is not None:
                assert mmax is not None  # for type checkers
                return Quant(child, mmin, mmax, mode)
            # else fallthrough (no quantifier actually parsed)
            cur.i = save
        return child

    def parse_brace_quant(self) -> Tuple[Optional[int], Optional[Union[int, str]], str]:
        cur = self.cur
        if not cur.match("{"):
            return None, None, "Greedy"
        # Parse integers
        m = self._read_int_optional()
        if m is None:
            raise ParseError("Expected integer in {m,n}", cur.i)
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
        nxt = cur.peek()
        if nxt in "?+":
            mode = "Lazy" if nxt == "?" else "Possessive"
            cur.take()
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
        self.cur.in_class += 1
        neg = False
        items: List[ClassItem] = []
        if cur.peek() == "^":
            neg = True
            cur.take()

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

            # ']' closes only if we've parsed at least one item; at position 0 it's a literal
            if cur.peek() == "]" and len(items) > 0:
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
        if cur.match("?:"):
            body = self.parse_alt()
            if not cur.match(")"):
                raise ParseError("Unterminated group", cur.i)
            return Group(False, body)
        if cur.match("?<"):
            name = self._read_until(">")
            if not cur.match(">"):
                raise ParseError("Unterminated group name", cur.i)
            body = self.parse_alt()
            if not cur.match(")"):
                raise ParseError("Unterminated group", cur.i)
            return Group(True, body, name=name)
        if cur.match("?>"):
            body = self.parse_alt()
            if not cur.match(")"):
                raise ParseError("Unterminated atomic group", cur.i)
            return Group(False, body, atomic=True)
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
        # capturing group
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
