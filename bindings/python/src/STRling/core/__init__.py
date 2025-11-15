"""
STRling Core Package - Parser, AST nodes, and core utilities

This package exposes the core components used by the STRling compiler and
bindings: the recursive-descent parser, the AST node definitions, and
related errors and helpers. The symbols re-exported here provide a
convenient, single import location for compiler internals and for tests.

Key exports:
    - `parse`, `parse_to_artifact`, `ParseError` from the parser
    - AST node classes (Flags, Node, Alt, Seq, Lit, Dot, Anchor, CharClass, ...)

The module mirrors the documentation style used across other `core` modules.
"""

from STRling.core.parser import parse, parse_to_artifact, ParseError
from STRling.core.nodes import (
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
)

__all__ = [
    "parse",
    "parse_to_artifact",
    "ParseError",
    "Flags",
    "Node",
    "Alt",
    "Seq",
    "Lit",
    "Dot",
    "Anchor",
    "CharClass",
    "ClassLiteral",
    "ClassRange",
    "ClassEscape",
    "Quant",
    "Group",
    "Backref",
    "Look",
]
