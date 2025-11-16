"""
STRling Parser - Recursive Descent Parser for STRling DSL

This module implements a hand-rolled recursive-descent parser that transforms
STRling pattern syntax into Abstract Syntax Tree (AST) nodes. The parser handles:
  - Alternation and sequencing
  - Character classes and ranges
  - Quantifiers (greedy, lazy, possessive)
  - Groups (capturing, non-capturing, named, atomic)
  - Lookarounds (lookahead and lookbehind, positive and negative)
  - Anchors and special escapes
  - Extended/free-spacing mode with comments

The parser produces AST nodes (defined in nodes.py) that can be compiled
to IR and ultimately emitted as target-specific regex patterns. It includes
comprehensive error handling with position tracking for helpful diagnostics.
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
from .errors import STRlingParseError
from .hint_engine import get_hint


# ---------------- Errors ----------------
# Keep ParseError as an alias for backward compatibility
ParseError = STRlingParseError


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
        # Store original text for error reporting
        self._original_text = text
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

    def _raise_error(self, message: str, pos: int) -> None:
        """
        Raise a STRlingParseError with an instructional hint.

        Parameters
        ----------
        message : str
            The error message
        pos : int
            The position where the error occurred

        Raises
        ------
        STRlingParseError
            Always raises with context and hint
        """
        hint = get_hint(message, self.src, pos)
        raise STRlingParseError(message, pos, self.src, hint)

    # -- Directives --

    def _parse_directives(self, text: str) -> Tuple[Flags, str]:
        flags = Flags()
        lines = text.splitlines(keepends=True)
        pattern_lines: List[str] = []
        in_pattern = False  # Track whether we've started the pattern section
        line_num = 0

        for line in lines:
            line_num += 1
            striped = line.strip()
            # Skip leading blank lines or comments
            if not in_pattern and (striped == "" or striped.startswith("#")):
                continue
            # Process directives only before pattern content
            if not in_pattern and striped.startswith("%flags"):
                # Work from the original line so we can preserve any remainder
                # after the flags directive as the beginning of the pattern.
                idx = line.index("%flags")
                after = line[idx + len("%flags") :]
                # Scan the remainder to separate the flags token from any
                # inline pattern content. Accept spaces/tabs, commas, brackets
                # and the known flag letters; stop at the first character that
                # can't be part of the flags token (this is the start of the
                # pattern on the same line).
                allowed = set(list(" ,\t[]imsuxIMSUX"))
                j = 0
                while j < len(after) and after[j] in allowed:
                    j += 1
                flags_token = after[:j]
                remainder = after[j:]
                # Normalize separators and whitespace to single spaces
                letters = re.sub(r"[,\[\]\s]+", " ", flags_token).strip().lower()
                valid_flags = set("imsux")
                # If no valid flag letters were found but something remains on
                # the same line, treat the first non-space char as an
                # invalid-flag error (e.g. "%flags z").
                if letters.replace(" ", "") == "":
                    if remainder.strip() == "":
                        # directive-only line with no flags
                        pass
                    else:
                        ch = remainder.lstrip()[0]
                        leading_ws = len(remainder) - len(remainder.lstrip())
                        pos = (
                            sum(len(l) for l in lines[: line_num - 1])
                            + idx
                            + j
                            + leading_ws
                        )
                        hint = get_hint(
                            f"Invalid flag '{ch}'", self._original_text, pos
                        )
                        raise STRlingParseError(
                            f"Invalid flag '{ch}'", pos, self._original_text, hint
                        )
                else:
                    # Validate and accept the flags we found
                    for ch in letters.replace(" ", ""):
                        if ch and ch not in valid_flags:
                            pos = sum(len(l) for l in lines[: line_num - 1]) + idx
                            hint = get_hint(
                                f"Invalid flag '{ch}'", self._original_text, pos
                            )
                            raise STRlingParseError(
                                f"Invalid flag '{ch}'", pos, self._original_text, hint
                            )
                    flags = Flags.from_letters(letters)
                    # If remainder contains pattern content on the same line,
                    # treat it as the start of the pattern
                    if remainder.strip() != "":
                        in_pattern = True
                        pattern_lines.append(remainder)
                continue
            if not in_pattern and striped.startswith("%"):
                continue
            # This is pattern content
            # Check if %flags appears anywhere in this line (would be misplaced)
            if "%flags" in line:
                pos = sum(len(l) for l in lines[: line_num - 1]) + line.index("%flags")
                hint = get_hint(
                    "Directive after pattern content", self._original_text, pos
                )
                raise STRlingParseError(
                    "Directive after pattern content", pos, self._original_text, hint
                )
            # All other lines are pattern content
            # Once we hit pattern content, we stop processing directives
            in_pattern = True
            pattern_lines.append(line)
        # Join all pattern lines, preserving original whitespace and newlines
        pattern = "".join(pattern_lines)
        # DEBUG
        # print('DEBUG lines:', lines)
        # print('DEBUG pattern_lines:', pattern_lines)
        # print('DEBUG pattern repr:', repr(pattern))
        return flags, pattern

    def parse(self) -> Node:
        """
        Parse the entire STRling pattern into an AST.

        Entry point for parsing. Parses the pattern (after directives have been
        extracted) and validates that the entire input has been consumed.

        Returns
        -------
        Node
            The root AST node representing the entire pattern.

        Raises
        ------
        ParseError
            If there is unexpected trailing input or if the pattern ends with
            an incomplete alternation.
        """
        node = self.parse_alt()
        self.cur.skip_ws_and_comments()
        if not self.cur.eof():
            # If there's an unmatched closing parenthesis at top-level, raise
            # an explicit unmatched-parenthesis error with the instructional hint.
            if self.cur.peek() == ")":
                raise STRlingParseError(
                    "Unmatched ')'",
                    self.cur.i,
                    self.src,
                    "This ')' character does not have a matching opening '('. Did you mean to escape it with '\\)'?",
                )
            if self.cur.peek() == "|":
                # Alternation must have a right-hand side
                self._raise_error("Alternation lacks right-hand side", self.cur.i)
            else:
                self._raise_error("Unexpected trailing input", self.cur.i)
        return node

    # alt := seq ('|' seq)+ | seq
    def parse_alt(self) -> Node:
        # Check if the pattern starts with a pipe (no left-hand side)
        self.cur.skip_ws_and_comments()
        if self.cur.peek() == "|":
            self._raise_error("Alternation lacks left-hand side", self.cur.i)

        branches: List[Node] = [self.parse_seq()]
        self.cur.skip_ws_and_comments()
        while self.cur.peek() == "|":
            pipe_pos = self.cur.i
            self.cur.take()
            self.cur.skip_ws_and_comments()
            # Check if the pipe is followed by end-of-input (no right-hand side)
            if self.cur.peek() == "":
                self._raise_error("Alternation lacks right-hand side", pipe_pos)
            # Check if the pipe is followed by another pipe (empty branch)
            if self.cur.peek() == "|":
                self._raise_error("Empty alternation branch", pipe_pos)
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
            # Invalid quantifier at start of sequence/group (no previous atom)
            if ch != "" and ch in "*+?{" and len(parts) == 0:
                # Raise error with context-aware hint from hint_engine
                self._raise_error(f"Invalid quantifier '{ch}'", self.cur.i)
            # Stop parsing sequence if we hit end, closing paren, or alternation pipe
            if ch == "" or ch in ")|":
                break

            # Parse the fundamental unit (literal, class, group, escape, etc.)
            atom = self.parse_atom()

            # Parse any quantifier (*, +, ?, {m,n}) that might follow the atom
            # This returns (quantified_atom, had_failed_quant_parse)
            # Note: If atom is an Anchor, parse_quant_if_any will raise an error if a quantifier is present
            quantified_atom, had_failed_quant_parse = self.parse_quant_if_any(atom)

            # Coalesce adjacent Lit nodes: if the new atom is a Lit and the last part
            # is also a Lit, merge them into a single Lit with concatenated values.
            # However, don't coalesce if:
            # 1. We're in free-spacing mode (whitespace separation is semantic)
            # 2. The previous atom had a failed quantifier parse (semantic boundary)
            # 3. The current Lit is a digit following a backslash (avoid \digit ambiguity)
            # 4. The previous part is a Backref (keep digit literals separate)
            # 5. Either Lit contains a newline (line boundaries are semantic)
            avoid_digit_after_backslash = (
                isinstance(quantified_atom, Lit)
                and len(quantified_atom.value) == 1
                and quantified_atom.value.isdigit()
                and len(parts) > 0
                and isinstance(parts[-1], Lit)
                and len(parts[-1].value) > 0
                and parts[-1].value[-1] == "\\"
            )

            # Don't coalesce across newlines (line boundaries are semantic)
            contains_newline = (
                isinstance(quantified_atom, Lit) and "\n" in quantified_atom.value
            ) or (
                len(parts) > 0
                and isinstance(parts[-1], Lit)
                and "\n" in parts[-1].value
            )

            # Don't coalesce after a Backref to keep the digit literals separate
            prev_is_backref = len(parts) > 0 and isinstance(parts[-1], Backref)

            should_coalesce = (
                isinstance(quantified_atom, Lit)
                and len(parts) > 0
                and isinstance(parts[-1], Lit)
                and not self.cur.extended_mode  # Don't coalesce in free-spacing mode
                and not prev_had_failed_quant
                and not avoid_digit_after_backslash
                and not contains_newline
                and not prev_is_backref
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
        Parse an optional quantifier following an atom and apply it if present.

        Checks if the next character(s) represent a quantifier (*, +, ?, {m,n}) and
        if so, wraps the child node in a Quant node. Also handles lazy (?) and
        possessive (+) modifiers.

        Parameters
        ----------
        child : Node
            The AST node to potentially quantify (e.g., a Lit, CharClass, or Group).

        Returns
        -------
        tuple[Node, bool]
            A tuple containing:
            - The possibly quantified node (either the original child or a Quant node)
            - A boolean indicating if brace quantifier parsing was attempted but failed
              (used to prevent literal coalescing at semantic boundaries)

        Raises
        ------
        ParseError
            If attempting to quantify an anchor, which is semantically invalid.

        Notes
        -----
        Quantifiers specify repetition:
        - * : 0 or more (greedy)
        - + : 1 or more (greedy)
        - ? : 0 or 1 (greedy)
        - {m,n} : between m and n times (greedy)

        Modifiers can follow quantifiers:
        - ? makes it lazy (non-greedy)
        - + makes it possessive (no backtracking)
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

        # Semantic validation: Cannot quantify anchors
        if isinstance(child, Anchor):
            self._raise_error("Cannot quantify anchor", cur.i)

        # Now check for lazy/possessive modifiers
        nxt = cur.peek()
        if nxt == "?":
            mode = "Lazy"
            cur.take()
        elif nxt == "+":
            mode = "Possessive"
            cur.take()

        return Quant(
            child, min_val, max_val if max_val is not None else "Inf", mode
        ), had_failed_quant_parse

    def parse_brace_quant(self) -> Tuple[Optional[int], Optional[Union[int, str]], str]:
        cur = self.cur
        if not cur.match("{"):
            return None, None, "Greedy"
        quant_start = cur.i - 1  # Save position of '{'
        # Parse integers
        m = self._read_int_optional()
        if m is None:
            # No leading digits. Look ahead (without consuming) to see if a
            # closing '}' exists and whether the content between '{' and '}'
            # contains non-digit/non-comma characters (e.g. {foo}). If so,
            # treat it as an invalid brace quantifier and raise an error so
            # the IEH engine can provide an instructional hint. If no closing
            # '}' is found, treat '{' as a literal (backtrack).
            j = 0
            content = ""
            while True:
                ch = cur.peek(j)
                if ch == "":
                    break
                if ch == "}":
                    break
                if ch in "\r\n":
                    break
                content += ch
                j += 1
            if cur.peek(j) == "}":
                # If content has chars other than digits or commas, reject
                if re.search(r"[^0-9,]", content):
                    # Include a human-friendly prefix so tests that look for
                    # 'Brace quantifier' in the error message succeed, while
                    # still allowing the hint engine to match the
                    # 'Invalid brace quantifier content' pattern.
                    self._raise_error(
                        "Brace quantifier: Invalid brace quantifier content",
                        quant_start,
                    )
            # Otherwise, it's not a quantifier — treat as literal and backtrack.
            return None, None, "Greedy"
        if cur.match(","):
            n = self._read_int_optional()
            if not cur.match("}"):
                # Unterminated brace quantifier -> raise specific instructional hint
                # Use a clear message that matches test expectations while
                # providing an instructional hint explaining the expected syntax.
                raise STRlingParseError(
                    "Incomplete quantifier (closing '}')",
                    cur.i,
                    self.src,
                    "Brace quantifiers use the syntax {m,n} or {n}. Make sure to close the quantifier with '}'.",
                )
            if n is None:
                mmin, mmax = m, "Inf"
            else:
                # Validate that m <= n
                if m > n:
                    self._raise_error(
                        f"Invalid quantifier range {{{m},{n}}}", quant_start
                    )
                mmin, mmax = m, n
        else:
            if not cur.match("}"):
                # Unterminated brace quantifier -> raise specific instructional hint
                # For the form 'a{1' we raise a clear 'Unterminated brace quantifier'.
                raise STRlingParseError(
                    "Incomplete quantifier (closing '}')",
                    cur.i,
                    self.src,
                    "Brace quantifiers use the syntax {m,n} or {n}. Make sure to close the quantifier with '}'.",
                )
            mmin, mmax = m, m
        mode = "Greedy"
        # Note: The lazy/possessive modifier is now handled in parse_quant_if_any
        return mmin, mmax, mode

    def _read_int_optional(self) -> Optional[int]:
        """
        Read an optional integer from the current cursor position.

        Consumes consecutive digit characters and converts them to an integer.
        If no digits are found, returns None without advancing the cursor.

        Returns
        -------
        int or None
            The parsed integer value, or None if no digits were found.
        """
        cur = self.cur
        s = ""
        while cur.peek().isdigit():
            s += cur.take()
        return int(s) if s != "" else None

    # ---- atom ----
    def parse_atom(self) -> Node:
        """
        Parse an atomic pattern element (the most basic building blocks).

        Atoms are the fundamental units of a pattern:
        - Dot (.) for any character
        - Anchors (^ for start, $ for end)
        - Groups and lookarounds (parentheses)
        - Character classes (square brackets)
        - Escapes (backslash sequences)
        - Literal characters

        Returns
        -------
        Node
            An AST node representing the parsed atom (Dot, Anchor, Group, CharClass,
            Lit, etc.).

        Raises
        ------
        ParseError
            If an unexpected token is encountered (e.g., | or ) without proper context).
        """
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
        # If we encounter a closing paren here it means there was no matching
        # opening parenthesis at a higher level -> unmatched parenthesis.
        if ch == ")":
            # Raise STRlingParseError with an explicit instructional hint
            raise STRlingParseError(
                "Unmatched ')'",
                cur.i,
                self.src,
                "This ')' character does not have a matching opening '('. Did you mean to escape it with '\\)'?",
            )
        if ch == "|":
            self._raise_error("Unexpected token", cur.i)
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
        # Consume digits greedily up to the highest valid capture group
        if nxt.isdigit() and nxt != "0":
            saved_pos = cur.i
            num_str = ""

            # Read digits one at a time and check if they form a valid backref
            while cur.peek().isdigit():
                num_str += cur.take()
                num = int(num_str)

                # If this number is valid, remember it
                if num <= self._cap_count:
                    # This is a valid backref, keep consuming
                    continue
                else:
                    # This number is too large, backtrack one digit
                    cur.i -= 1
                    num_str = num_str[:-1]
                    break

            # If we got a valid backref number, use it
            if num_str:
                num = int(num_str)
                if num <= self._cap_count:
                    return Backref(byIndex=num)

            # No valid backref found, reset and raise error
            cur.i = saved_pos
            num = self._read_decimal()
            self._raise_error(f"Backreference to undefined group \\{num}", start_pos)
        # Anchors \b \B \A \Z
        # NOTE: lowercase '\z' is intentionally NOT treated as an anchor; it's
        # handled below as a potential unknown escape sequence per the corpus.
        if nxt in ("b", "B", "A", "Z"):
            ch = cur.take()
            if ch == "b":
                return Anchor("WordBoundary")
            if ch == "B":
                return Anchor("NotWordBoundary")
            if ch == "A":
                return Anchor("AbsoluteStart")
            if ch == "Z":
                return Anchor("EndBeforeFinalNewline")
        # \k<name> named backref
        if nxt == "k":
            cur.take()
            if not cur.match("<"):
                self._raise_error(r"Expected '<' after \k", start_pos)
            name = self._read_ident_until(">")
            if not cur.match(">"):
                self._raise_error("Unterminated named backref", start_pos)
            if name not in self._cap_names:
                self._raise_error(
                    f"Backreference to undefined group <{name}>", start_pos
                )
            return Backref(byName=name)
        # Shorthand classes \d \D \w \W \s \S or property \p{..} \P{..}
        if nxt in "dDwWsS":
            cur.take()
            return CharClass(False, [ClassEscape(nxt)])
        if nxt in "pP":
            tp = cur.take()
            if not cur.match("{"):
                self._raise_error("Expected { after \\p/\\P", cur.i)
            prop = self._read_until("}")
            if not cur.match("}"):
                self._raise_error("Unterminated \\p{...}", cur.i)
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
        # In extended (free-spacing) mode, an escaped space ("\ ") should
        # be treated as a literal space character rather than an unknown
        # escape sequence. Handle that before the identity-escape check.
        if nxt == " " and cur.extended_mode:
            cur.take()
            return Lit(" ")
        # Identity escape: validate allowed identity escapes and treat next
        # char literally. If the escape is not recognized (e.g. \z), raise
        # an instructional STRlingParseError using the corpus hint.
        allowed_identity_escapes = set(list(r".\^$*+?()[]{}|\\") + ["/", "-", ":", ","])
        ch = cur.peek()
        if ch == "":
            self._raise_error("Unexpected end of escape", start_pos)
        if ch not in allowed_identity_escapes:
            # Unknown escape sequence -> raise with context-aware hint from hint_engine
            self._raise_error(f"Unknown escape sequence \\{ch}", start_pos)
        # consume and return literal
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

    def _is_valid_identifier(self, name: str) -> bool:
        """
        Validate that a name conforms to the EBNF IDENTIFIER rule.

        Per the grammar:
        - IDENT_START = LETTER | "_"
        - IDENT_CONT = IDENT_START | DIGIT
        - IDENTIFIER = IDENT_START, { IDENT_CONT }

        Returns False for empty names, names starting with digits, or names
        containing invalid characters like hyphens.
        """
        if not name:
            return False
        # First character must be letter or underscore
        if not (name[0].isalpha() or name[0] == "_"):
            return False
        # Remaining characters must be letter, digit, or underscore
        for ch in name[1:]:
            if not (ch.isalnum() or ch == "_"):
                return False
        return True

    def _parse_hex_escape(self, start_pos: int) -> str:
        cur = self.cur
        assert cur.take() == "x"
        if cur.match("{"):
            hexs = ""
            while re.match(r"[0-9A-Fa-f]", cur.peek() or ""):
                hexs += cur.take()
            if not cur.match("}"):
                # Use start_pos for error reporting
                self._raise_error("Unterminated \\x{...}", start_pos)
            cp = int(hexs or "0", 16)
            return chr(cp)
        # \xHH
        h1 = cur.take()
        h2 = cur.take()
        if not (
            re.match(r"[0-9A-Fa-f]", h1 or "") and re.match(r"[0-9A-Fa-f]", h2 or "")
        ):
            self._raise_error("Invalid \\xHH escape", start_pos)
        return chr(int(h1 + h2, 16))

    def _parse_unicode_escape(self, start_pos: int) -> str:
        cur = self.cur
        tp = cur.take()  # u or U
        if tp == "u" and cur.match("{"):
            hexs = ""
            while re.match(r"[0-9A-Fa-f]", cur.peek() or ""):
                hexs += cur.take()
            if not cur.match("}"):
                self._raise_error("Unterminated \\u{...}", start_pos)
            return chr(int(hexs or "0", 16))
        if tp == "U":
            hexs = ""
            for _ in range(8):
                ch = cur.take()
                if not re.match(r"[0-9A-Fa-f]", ch or ""):
                    self._raise_error("Invalid \\UHHHHHHHH", start_pos)
                hexs += ch
            return chr(int(hexs, 16))
        # \uHHHH
        hexs = ""
        for _ in range(4):
            ch = cur.take()
            if not re.match(r"[0-9A-Fa-f]", ch or ""):
                self._raise_error("Invalid \\uHHHH", start_pos)
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

        # Detect explicit empty character class '[]' (or '[^]') and raise
        # a specific instructional error only when the class truly contains
        # no elements (i.e., the next character is end-of-input or another
        # immediate closing bracket). Do NOT raise for cases like '[]a]' where
        # ']' is intended as a literal at the start of the class.
        if cur.peek() == "]" and (cur.peek(1) == "" or cur.peek(1) == "]"):
            # Raise a message compatible with existing tests while supplying
            # an explicit hint that mentions the class is empty.
            hint = get_hint(
                "Empty character class",
                self._original_text,
                start_pos,
            ) or (
                "Empty character class '[]' detected. Character classes must contain at least one element (e.g., [a-z]) — do not leave them empty. "
                "If you meant a literal '[', escape it with '\\['."
            )
            raise STRlingParseError(
                "Unterminated character class",
                start_pos,
                self.src,
                hint,
            )

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
                        self._raise_error("Expected { after \\p/\\P", escape_start)
                    prop = self._read_until("}")
                    if not cur.match("}"):
                        self._raise_error("Unterminated \\p{...}", escape_start)
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
                self._raise_error("Unterminated character class", cur.i)

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
                dash_pos = cur.i
                cur.take()
                end_item = read_item()
                if isinstance(end_item, ClassLiteral):
                    start_lit = cast(
                        ClassLiteral, items.pop()
                    )  # Explicitly cast for type checker
                    start_ch: str = start_lit.ch
                    end_ch: str = end_item.ch
                    # Validate that start <= end in the range
                    if ord(start_ch) > ord(end_ch):
                        self._raise_error(
                            f"Invalid character range [{start_ch}-{end_ch}]", dash_pos
                        )
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
            self._raise_error("Inline modifiers `(?imsx)` are not supported", cur.i)

        # Non-capturing group
        if cur.match("?:"):
            body = self.parse_alt()
            if not cur.match(")"):
                self._raise_error("Unterminated group", cur.i)
            return Group(False, body)

        # IMPORTANT: Lookbehind tokens must be recognized BEFORE "?<name>"
        if cur.match("?<="):
            body = self.parse_alt()
            if not cur.match(")"):
                self._raise_error("Unterminated lookbehind", cur.i)
            return Look("Behind", False, body)

        if cur.match("?<!"):
            body = self.parse_alt()
            if not cur.match(")"):
                self._raise_error("Unterminated lookbehind", cur.i)
            return Look("Behind", True, body)

        # Named capturing group (?<name>...)
        if cur.match("?<"):
            name_start_pos = cur.i
            name = self._read_until(">")
            if not cur.match(">"):
                self._raise_error("Unterminated group name", cur.i)
            # Validate group name per EBNF: IDENTIFIER = IDENT_START, { IDENT_CONT }
            # IDENT_START = LETTER | "_", IDENT_CONT = IDENT_START | DIGIT
            if not self._is_valid_identifier(name):
                self._raise_error(f"Invalid group name <{name}>", name_start_pos)
            # Check for duplicate group name
            if name in self._cap_names:
                self._raise_error(f"Duplicate group name <{name}>", cur.i)
            self._cap_count += 1
            self._cap_names.add(name)
            body = self.parse_alt()
            if not cur.match(")"):
                # Unclosed named capture group -> raise a specific instructional hint
                raise STRlingParseError(
                    "Incomplete named capture group",
                    cur.i,
                    self.src,
                    "Incomplete named capture group. Expected ')' to close the group.",
                )
            return Group(True, body, name=name)

        # Atomic group (?>...)
        if cur.match("?>"):
            body = self.parse_alt()
            if not cur.match(")"):
                self._raise_error("Unterminated atomic group", cur.i)
            return Group(False, body, atomic=True)

        # Lookahead (?=...) / (?!...)
        if cur.match("?="):
            body = self.parse_alt()
            if not cur.match(")"):
                self._raise_error("Unterminated lookahead", cur.i)
            return Look("Ahead", False, body)

        if cur.match("?!"):
            body = self.parse_alt()
            if not cur.match(")"):
                self._raise_error("Unterminated lookahead", cur.i)
            return Look("Ahead", True, body)

        # Capturing group (...)
        self._cap_count += 1
        body = self.parse_alt()
        if not cur.match(")"):
            self._raise_error("Unterminated group", cur.i)
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
