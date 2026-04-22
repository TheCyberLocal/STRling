"""
STRling PCRE2 Emitter - IR to PCRE2 Pattern String

This module implements the emitter that transforms STRling's Intermediate
Representation (IR) into PCRE2-compatible regex pattern strings. The emitter:
  - Converts IR operations to PCRE2 syntax
  - Handles proper escaping of metacharacters
  - Manages character classes and ranges
  - Emits quantifiers, groups, and lookarounds
  - Applies regex flags as needed

The emitter is the final stage of the compilation pipeline, producing actual
regex patterns that can be used with PCRE2-compatible regex engines (which
includes most modern regex implementations).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional, Literal, Protocol, Union, runtime_checkable
import re

from STRling.core.errors import STRlingCompilationError, STRlingWarning
from STRling.core.ir import (
    IROp,
    IRAlt,
    IRSeq,
    IRLit,
    IRDot,
    IRAnchor,
    IRCharClass,
    IRClassItem,
    IRClassLiteral,
    IRClassRange,
    IRClassEscape,
    IRQuant,
    IRGroup,
    IRBackref,
    IRLook,
)

# ---- Safety guards ---------------------------------------------------------

#: Default upper bound on AST/IR nesting depth before the emitter aborts.
#: Mirrors ``DEFAULT_MAX_DEPTH`` in the TypeScript reference (and the C/C++
#: ``STRLING_DEFAULT_MAX_DEPTH``). Tests may override this via
#: ``emit_with_diagnostics(..., max_depth=N)``.
DEFAULT_MAX_DEPTH: int = 250


@dataclass
class _EmitContext:
    """Mutable state threaded through ``_emit_node`` so the depth, lookbehind,
    and warning-collection guards can fire without polluting the public API.
    Kept module-private; the top-level ``emit()``/``emit_with_diagnostics()``
    entry points remain pure functions.
    """

    depth: int = 0
    max_depth: int = DEFAULT_MAX_DEPTH
    in_lookbehind: bool = False
    warnings: List[STRlingWarning] = field(default_factory=list)


def _new_context(max_depth: Optional[int] = None) -> _EmitContext:
    return _EmitContext(
        max_depth=max_depth
        if (max_depth is not None and max_depth > 0)
        else DEFAULT_MAX_DEPTH
    )


def _is_unbounded_quant(q: IRQuant) -> bool:
    """True iff a quantifier has an unbounded upper bound."""
    # IRMaxBound sentinel in TS is the string ``"Inf"``; Python keeps the
    # same wire format. Be lenient with negative ints (legacy callers).
    return q.max == "Inf" or (isinstance(q.max, int) and q.max < 0)


def _is_variable_length_quant(q: IRQuant) -> bool:
    """True iff a quantifier matches a variable number of characters."""
    return q.min != q.max


def _is_fixed_length_body(node: IROp) -> bool:
    """Mirror of ``_isFixedLengthBody`` in the TS SSOT.

    Returns ``True`` when ``node`` consumes a fixed (statically known)
    number of characters and is therefore safe inside a PCRE2 lookbehind.
    """
    if isinstance(node, IRQuant):
        return (not _is_variable_length_quant(node)) and _is_fixed_length_body(
            node.child
        )
    if isinstance(node, IRSeq):
        return all(_is_fixed_length_body(p) for p in node.parts)
    if isinstance(node, IRAlt):
        # Conservative parity with TS: every branch must be fixed-length;
        # the per-branch length-equality check is delegated to PCRE2.
        return all(_is_fixed_length_body(b) for b in node.branches)
    if isinstance(node, IRGroup):
        return _is_fixed_length_body(node.body)
    if isinstance(node, IRLook):
        # Lookarounds are zero-width, hence safe inside a lookbehind.
        return True
    # Lit, Dot, CharClass, Anchor, Backref are single- or zero-width.
    return True


def _has_nested_unbounded_quant(child: IROp) -> bool:
    """Mirror of ``_hasNestedUnboundedQuant`` in the TS SSOT.

    Detects an unbounded quantifier reachable from ``child`` via single-child
    wrappers (``IRGroup``, single-element ``IRSeq``) or any branch of an
    ``IRAlt``. Used to flag the canonical ``(a+)+`` ReDoS shape *only*
    when the outer quantifier is itself unbounded.
    """
    if isinstance(child, IRQuant):
        return _is_unbounded_quant(child)
    if isinstance(child, IRGroup):
        return _has_nested_unbounded_quant(child.body)
    if isinstance(child, IRSeq) and len(child.parts) == 1:
        return _has_nested_unbounded_quant(child.parts[0])
    if isinstance(child, IRAlt):
        return any(_has_nested_unbounded_quant(b) for b in child.branches)
    return False


_REDOS_MESSAGE = (
    "The pattern contains overlapping alternations or nested unbounded "
    "quantifiers (e.g., (a+)+). This can lead to catastrophic backtracking "
    "and exponential CPU spikes. Consider using possessive quantifiers "
    "(++ or *+) or atomic groups to guarantee execution safety."
)


def _push_redos_warning(ctx: _EmitContext) -> None:
    """Append a single REDOS_RISK warning, deduplicated per emit pass."""
    if any(w.code == "REDOS_RISK" for w in ctx.warnings):
        return
    ctx.warnings.append(STRlingWarning("REDOS_RISK", _REDOS_MESSAGE))


def _escape_literal(s: str) -> str:
    """Escape PCRE2 metacharacters outside character classes, but do NOT escape dashes (-)."""
    # Use re.escape, then unescape any escaped dashes.
    escaped = re.escape(s)
    # Remove unnecessary escaping for dashes
    escaped = escaped.replace(r"\-", "-")
    # Unescape whitespace to match expected output format (literal newlines etc)
    # re.escape escapes these with a backslash (e.g. \ + newline), but we want the literal char
    escaped = escaped.replace("\\\n", "\n")
    escaped = escaped.replace("\\\r", "\r")
    escaped = escaped.replace("\\\t", "\t")
    escaped = escaped.replace("\\\f", "\f")
    escaped = escaped.replace("\\\v", "\v")
    return escaped


def _escape_class_char(ch: str) -> str:
    """Escape a char for use inside [...] per PCRE2 rules."""
    # Inside [], ], \, -, and ^ are special and need escaping for safety.
    # ] and \ ALWAYS need escaping.
    # - and ^ should be escaped to avoid ambiguity (even though context matters).
    if ch == "\\" or ch == "]":
        return "\\" + ch
    if ch == "-":
        return "\\-"
    if ch == "^":
        return "\\^"

    # Handle non-printable chars / whitespace for clarity
    if ch == "\n":
        return r"\n"
    if ch == "\r":
        return r"\r"
    if ch == "\t":
        return r"\t"
    if ch == "\f":
        return r"\f"
    if ch == "\v":
        return r"\v"
    if not ch.isprintable() or ord(ch) < 32:
        code = ord(ch)
        if code > 255:
            return f"\\x{{{code:x}}}"
        return f"\\x{code:02x}"

    # All other characters are literal within [] including ., *, ?, [, etc.
    return ch


def _emit_class(cc: IRCharClass) -> str:
    r"""
    Emit a PCRE2 character class. If the class is exactly one shorthand escape
    (like \d or \p{Lu}), prefer the shorthand (with negation flipping) instead
    of a bracketed class.
    """
    parts: List[str] = []
    items: List[IRClassItem] = cc.items

    # --- Single-item shorthand optimization ---------------------------------
    if len(items) == 1 and isinstance(items[0], IRClassEscape):
        k = items[0].type  # 'd','D','w','W','s','S','p','P'
        prop = items[0].property

        if k in ("d", "w", "s"):
            # Flip to uppercase negated forms when the entire class is negated.
            return (
                r"\D"
                if (cc.negated and k == "d")
                else r"\W"
                if (cc.negated and k == "w")
                else r"\S"
                if (cc.negated and k == "s")
                else "\\" + k
            )

        if k in ("D", "W", "S"):
            # Already-negated shorthands; flip back if the class itself is negated.
            base = k.lower()
            return ("\\" + base) if cc.negated else ("\\" + k)

        if k in ("p", "P") and prop:
            # For \p{..}/\P{..}, flip p<->P iff exactly-negated class.
            use = "P" if (cc.negated ^ (k == "P")) else "p"
            return f"\\{use}{{{prop}}}"

    # --- General case: build a bracket class --------------------------------
    parts: List[str] = []
    for it in items:
        if isinstance(it, IRClassLiteral):
            parts.append(_escape_class_char(it.ch))
        elif isinstance(it, IRClassRange):
            # Escape ends of range appropriately, use unescaped - for the range operator
            parts.append(
                f"{_escape_class_char(it.from_ch)}-{_escape_class_char(it.to_ch)}"
            )
        elif isinstance(it, IRClassEscape):
            # Shorthands like \d, \p{L} are used directly
            if it.type in ("d", "D", "w", "W", "s", "S"):
                parts.append("\\" + it.type)
            elif it.type in ("p", "P") and it.property:
                parts.append(f"\\{it.type}{{{it.property}}}")
            # Fallback for potentially unknown escapes (shouldn't happen with valid IR)
            else:
                parts.append("\\" + it.type)
        else:
            raise NotImplementedError(f"class item {type(it)}")

    # Assemble the inner part
    inner = "".join(parts)

    return f"[{'^' if cc.negated else ''}{inner}]"


def _emit_quant_suffix(
    minv: int | Literal[0, 1] | str,
    maxv: int | Literal[0, 1] | str,
    mode: str,
) -> str:
    """Emit *, +, ?, {m}, {m,}, {m,n} plus optional lazy/possessive suffix."""
    if minv == 0 and maxv == "Inf":
        q = "*"
    elif minv == 1 and maxv == "Inf":
        q = "+"
    elif minv == 0 and maxv == 1:
        q = "?"
    elif minv == maxv:
        q = "{" + str(minv) + "}"
    elif maxv == "Inf":
        q = "{" + str(minv) + ",}"
    else:
        q = "{" + str(minv) + "," + str(maxv) + "}"

    if mode == "Lazy":
        q += "?"
    elif mode == "Possessive":
        q += "+"
    return q


def _needs_group_for_quant(child: IROp) -> bool:
    """
    Return True if 'child' needs a non-capturing group when quantifying.
    Literals of length > 1, Seq, Alt, and Look typically require grouping.
    """
    if isinstance(child, (IRCharClass, IRDot, IRGroup, IRBackref, IRAnchor)):
        return False
    if isinstance(child, IRLit):
        return len(child.value) > 1
    # Group Alt/Look, but only group Seq if it's > 1 part
    if isinstance(child, (IRAlt, IRLook)):
        return True
    if isinstance(child, IRSeq):
        return len(child.parts) > 1
    return False


def _emit_group_open(g: IRGroup) -> str:
    if g.atomic:
        return "(?>"
    if g.capturing:
        if g.name is not None:
            return f"(?<{g.name}>"
        return "("
    return "(?:"


def _emit_node(
    node: IROp, parent_kind: str = "", ctx: Optional[_EmitContext] = None
) -> str:
    # ``ctx`` is optional so legacy callers (and the few internal helpers
    # that reach into ``_emit_node`` without state) keep working without
    # the depth/VLB/ReDoS guards. Only the top-level ``emit*()`` entry
    # points construct a real context.
    if ctx is None:
        ctx = _new_context()

    # Depth tracking surfaces the offending depth as a Signpost-pattern
    # error rather than letting the host stack overflow. Increment on
    # entry, decrement in ``finally`` so every return path is balanced.
    ctx.depth += 1
    try:
        if ctx.depth > ctx.max_depth:
            raise STRlingCompilationError(
                f"Maximum AST depth exceeded (limit: {ctx.max_depth}). "
                "This pattern is too deeply nested and risks host stack "
                "exhaustion during emission. Refactor the pattern to "
                "reduce nesting, or flatten capturing groups where possible.",
                "MAX_DEPTH",
                "pcre2",
            )

        if isinstance(node, IRLit):
            return _escape_literal(node.value)

        if isinstance(node, IRDot):
            return "."

        if isinstance(node, IRAnchor):
            mapping = {
                "Start": "^",
                "End": "$",
                "WordBoundary": r"\b",
                "NotWordBoundary": r"\B",
                "NonWordBoundary": r"\B",
                "AbsoluteStart": r"\A",
                "EndBeforeFinalNewline": r"\Z",
                "AbsoluteEnd": r"\z",
            }
            return mapping.get(node.at, "")

        if isinstance(node, IRBackref):
            if node.byName is not None:
                return rf"\k<{node.byName}>"
            if node.byIndex is not None:
                return "\\" + str(node.byIndex)
            return ""

        if isinstance(node, IRCharClass):
            return _emit_class(node)

        if isinstance(node, IRSeq):
            return "".join(
                _emit_node(p, parent_kind="Seq", ctx=ctx) for p in node.parts
            )

        if isinstance(node, IRAlt):
            body = "|".join(
                _emit_node(b, parent_kind="Alt", ctx=ctx) for b in node.branches
            )
            # Alt inside sequence/quant should be grouped
            return "(?:" + body + ")" if parent_kind in ("Seq", "Quant") else body

        if isinstance(node, IRQuant):
            # ReDoS guard: only flag when the *outer* quantifier is itself
            # unbounded (e.g. ``(a+)+``). A bounded outer like ``(a+){0,3}``
            # cannot produce exponential backtracking on its own.
            if _is_unbounded_quant(node) and _has_nested_unbounded_quant(node.child):
                _push_redos_warning(ctx)

            child_str = _emit_node(node.child, parent_kind="Quant", ctx=ctx)
            if _needs_group_for_quant(node.child) and not isinstance(
                node.child, IRGroup
            ):
                child_str = "(?:" + child_str + ")"
            return child_str + _emit_quant_suffix(node.min, node.max, node.mode)

        if isinstance(node, IRGroup):
            return (
                _emit_group_open(node)
                + _emit_node(node.body, parent_kind="Group", ctx=ctx)
                + ")"
            )

        if isinstance(node, IRLook):
            # Variable-length lookbehind guard: PCRE2 mandates a fixed-width
            # lookbehind body. Detect the violation here so the user sees a
            # Signpost-pattern error rather than an opaque PCRE2 compile
            # failure leaking from the runtime.
            if node.dir == "Behind" and not _is_fixed_length_body(node.body):
                raise STRlingCompilationError(
                    "PCRE2 does not support variable-length lookbehinds. "
                    "The lookbehind body contains a quantifier that makes "
                    "its length unpredictable. Rewrite the assertion using "
                    "a fixed-length range (e.g. `{1,8}` instead of `+`), "
                    "or restructure the pattern using a Lookahead, or "
                    "extract the quantified portion outside the assertion.",
                    "VLB_NOT_SUPPORTED",
                    "pcre2",
                )

            was_in_lb = ctx.in_lookbehind
            if node.dir == "Behind":
                ctx.in_lookbehind = True
            try:
                if node.dir == "Ahead" and not node.neg:
                    op = "?="
                elif node.dir == "Ahead" and node.neg:
                    op = "?!"
                elif node.dir == "Behind" and not node.neg:
                    op = "?<="
                else:
                    op = "?<!"
                return (
                    "(" + op + _emit_node(node.body, parent_kind="Look", ctx=ctx) + ")"
                )
            finally:
                ctx.in_lookbehind = was_in_lb

        raise NotImplementedError(f"Emitter missing for {type(node)}")
    finally:
        ctx.depth -= 1


# Accept either a plain dict of flags or a Flags dataclass with .to_dict()
@runtime_checkable
class _SupportsToDictFlags(Protocol):
    def to_dict(self) -> dict[str, bool]: ...


def _emit_prefix_from_flags(flags: dict[str, bool]) -> str:
    # Build the inline **prefix** form expected by tests, e.g. "(?imx)"
    letters = ""
    if flags.get("ignoreCase"):
        letters += "i"
    if flags.get("multiline"):
        letters += "m"
    if flags.get("dotAll"):
        letters += "s"
    if flags.get("unicode"):
        letters += "u"
    if flags.get("extended"):
        letters += "x"
    return f"(?{letters})" if letters else ""


def emit(
    ir_root: IROp,
    flags: Optional[Union[dict[str, bool], _SupportsToDictFlags]] = None,
    max_depth: Optional[int] = None,
) -> str:
    """
    Emit a PCRE2 pattern string from IR.

    If 'flags' is provided, it can be a plain dict (keys: ignoreCase, multiline,
    dotAll, unicode, extended) or a Flags object with .to_dict().

    Raises ``STRlingCompilationError`` when an emitter safety guard rejects
    the IR (variable-length lookbehind, AST depth exceeded). Diagnostic
    warnings (e.g. ``REDOS_RISK``) are silently dropped from this back-compat
    entry point; callers that need them must use ``emit_with_diagnostics``.
    """
    return emit_with_diagnostics(ir_root, flags, max_depth=max_depth).pattern


@dataclass
class EmitResult:
    """Result of :func:`emit_with_diagnostics`: the produced pattern plus
    any non-fatal warnings collected during emission."""

    pattern: str
    warnings: List[STRlingWarning] = field(default_factory=list)


def emit_with_diagnostics(
    ir_root: IROp,
    flags: Optional[Union[dict[str, bool], _SupportsToDictFlags]] = None,
    max_depth: Optional[int] = None,
) -> EmitResult:
    """
    Like :func:`emit`, but also returns the list of
    :class:`STRlingWarning`s collected during emission. Used by the
    conformance test runner and any caller that wants to surface
    ``REDOS_RISK`` (or future) warnings to the end user.
    """
    flag_dict: Optional[dict[str, bool]] = None
    if flags is not None:
        if isinstance(flags, dict):
            flag_dict = flags
        elif hasattr(flags, "to_dict"):
            flag_dict = flags.to_dict()
        else:
            flag_dict = None

    ctx = _new_context(max_depth)
    prefix = _emit_prefix_from_flags(flag_dict) if flag_dict else ""
    body = _emit_node(ir_root, parent_kind="", ctx=ctx)
    return EmitResult(pattern=prefix + body, warnings=ctx.warnings)
