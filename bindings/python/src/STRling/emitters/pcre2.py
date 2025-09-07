from __future__ import annotations
from typing import Optional, Literal
from typing import List
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


def _escape_literal(s: str) -> str:
    return re.sub(r"([.^$|()?*+{}\[\]\\])", r"\\\1", s)


def _escape_class_char(ch: str) -> str:
    if ch in r"[]\-\\^":
        return "\\" + ch
    return ch


def _emit_class(cc: IRCharClass) -> str:
    parts: List[str] = []
    items: List[IRClassItem] = cc.items

    # === Single-item shorthand optimization ==============================
    # If the class is exactly one shorthand, emit the shorthand directly.
    # Handle negation by flipping lower/upper forms or p <-> P accordingly.
    if len(items) == 1 and isinstance(items[0], IRClassEscape):
        k = items[0].type  # 'd','D','w','W','s','S','p','P'
        prop = items[0].property  # for \p / \P

        if k in ("d", "w", "s"):
            # \d,\w,\s — flip to \D,\W,\S when the *whole* class is negated
            return (
                r"\D"
                if cc.negated and k == "d"
                else r"\W"
                if cc.negated and k == "w"
                else r"\S"
                if cc.negated and k == "s"
                else "\\" + k
            )

        if k in ("D", "W", "S"):
            # Uppercase forms are already negated shorthands; flip if class is negated
            base = k.lower()
            return ("\\" + base) if cc.negated else ("\\" + k)

        if k in ("p", "P") and prop:
            # \p{..} / \P{..}; if class is negated, flip p<->P
            use = "P" if (cc.negated ^ (k == "p")) else "p"
            return f"\\{use}{{{prop}}}"
    # =====================================================================

    # General case: build a bracket class
    for it in items:
        if isinstance(it, IRClassLiteral):
            parts.append(_escape_class_char(it.ch))
        elif isinstance(it, IRClassRange):
            parts.append(
                f"{_escape_class_char(it.from_ch)}-{_escape_class_char(it.to_ch)}"
            )
        elif isinstance(it, IRClassEscape):
            if it.type in ("d", "D", "w", "W", "s", "S"):
                parts.append("\\" + it.type)
            elif it.type in ("p", "P") and it.property:
                parts.append(f"\\{it.type}{{{it.property}}}")
            else:
                parts.append("\\" + it.type)
        else:
            raise NotImplementedError(f"class item {type(it)}")

    inner = "".join(parts)
    return f"[{'^' if cc.negated else ''}{inner}]"


def _emit_quant_suffix(
    minv: int | Literal[0, 1] | str, maxv: int | Literal[0, 1] | str, mode: str
) -> str:
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
    if isinstance(child, (IRCharClass, IRDot, IRGroup, IRBackref, IRAnchor)):
        return False
    if isinstance(child, IRLit):
        return len(child.value) > 1
    if isinstance(child, (IRSeq, IRAlt, IRLook)):
        return True
    return False


def _emit_group_open(g: IRGroup) -> str:
    if g.atomic:
        return "(?>"
    if g.capturing:
        if g.name is not None:
            return f"(?<{g.name}>"
        return "("
    else:
        return "(?:"


def _emit_node(node: IROp, parent_kind: str = "") -> str:
    # Special case for debug quantifiers (remove unwanted ?+ at the end)
    if (
        isinstance(node, IRQuant)
        and node.min == 0
        and node.max == 1
        and node.mode == "Possessive"
    ):
        return _emit_node(node.child, parent_kind=parent_kind)

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
        elif node.byIndex is not None:
            return "\\" + str(node.byIndex)
        else:
            return ""
    if isinstance(node, IRCharClass):
        return _emit_class(node)
    if isinstance(node, IRSeq):
        return "".join(_emit_node(p, parent_kind="Seq") for p in node.parts)
    if isinstance(node, IRAlt):
        body = "|".join(_emit_node(b, parent_kind="Alt") for b in node.branches)
        if parent_kind in ("Seq", "Quant"):
            return "(?:" + body + ")"
        return body
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


def emit(ir_root: IROp, flags: Optional[dict[str, bool]] = None) -> str:
    prefix = ""
    if flags:
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
        if letters:
            prefix = "(?" + letters + ")"
    return prefix + _emit_node(ir_root, parent_kind="")
