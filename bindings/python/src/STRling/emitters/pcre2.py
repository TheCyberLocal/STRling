from __future__ import annotations

from typing import List, Optional, Literal, Protocol, Union, runtime_checkable
import re

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

# ---- helpers ----------------------------------------------------------------


def _escape_literal(s: str) -> str:
    """Escape PCRE2 metacharacters outside character classes, but do NOT escape dashes (-)."""
    # Use re.escape, then unescape any escaped dashes.
    escaped = re.escape(s)
    # Remove unnecessary escaping for dashes
    escaped = escaped.replace(r'\-', '-')
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
        return f"\\x{ord(ch):02x}"

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


def _emit_node(node: IROp, parent_kind: str = "") -> str:
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
        return "".join(_emit_node(p, parent_kind="Seq") for p in node.parts)

    if isinstance(node, IRAlt):
        body = "|".join(_emit_node(b, parent_kind="Alt") for b in node.branches)
        # Alt inside sequence/quant should be grouped
        return "(?:" + body + ")" if parent_kind in ("Seq", "Quant") else body

    if isinstance(node, IRQuant):
        child_str = _emit_node(node.child, parent_kind="Quant")
        if _needs_group_for_quant(node.child) and not isinstance(node.child, IRGroup):
            child_str = "(?:" + child_str + ")"
        return child_str + _emit_quant_suffix(node.min, node.max, node.mode)

    if isinstance(node, IRGroup):
        return _emit_group_open(node) + _emit_node(node.body, parent_kind="Group") + ")"

    if isinstance(node, IRLook):
        if node.dir == "Ahead" and not node.neg:
            op = "?="
        elif node.dir == "Ahead" and node.neg:
            op = "?!"
        elif node.dir == "Behind" and not node.neg:
            op = "?<="
        else:
            op = "?<!"
        return "(" + op + _emit_node(node.body, parent_kind="Look") + ")"

    raise NotImplementedError(f"Emitter missing for {type(node)}")


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
) -> str:
    """
    Emit a PCRE2 pattern string from IR.

    If 'flags' is provided, it can be a plain dict (keys: ignoreCase, multiline,
    dotAll, unicode, extended) or a Flags object with .to_dict().
    """
    flag_dict: Optional[dict[str, bool]] = None
    if flags is not None:
        if isinstance(flags, dict):
            flag_dict = flags
        elif hasattr(flags, "to_dict"):
            flag_dict = flags.to_dict()
        else:
            # Unknown flag carrier: ignore rather than raise in the emitter
            flag_dict = None

    prefix = _emit_prefix_from_flags(flag_dict) if flag_dict else ""
    body = _emit_node(ir_root, parent_kind="")
    # IMPORTANT: Always return prefix + body (no localized "(?imx:...)" groups)
    return prefix + body
