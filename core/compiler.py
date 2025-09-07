from __future__ import annotations
from typing import List
from . import nodes as N
from . import ir as IR

class Compiler:
    """
    AST -> IR lowering with normalization:
      - Flatten nested Seq/Alt
      - Coalesce adjacent Lit nodes
      - Ensure quantifier children are grouped appropriately
    """
    def compile(self, root: N.Node) -> IR.IROp:
        ir = self._lower(root)
        ir = self._normalize(ir)
        return ir

    # ---------- Lowering (AST -> IR) ----------
    def _lower(self, node: N.Node) -> IR.IROp:
        t = type(node).__name__
        if t == "Seq":
            return IR.IRSeq([self._lower(p) for p in node.parts])  # type: ignore
        if t == "Alt":
            return IR.IRAlt([self._lower(b) for b in node.branches])  # type: ignore
        if t == "Lit":
            return IR.IRLit(node.value)  # type: ignore
        if t == "Dot":
            return IR.IRDot()
        if t == "Anchor":
            return IR.IRAnchor(node.at)  # type: ignore
        if t == "CharClass":
            items = []
            for it in node.items:  # type: ignore
                it_t = type(it).__name__
                if it_t == "ClassRange":
                    items.append(IR.IRClassRange(it.from_ch, it.to_ch))  # type: ignore
                elif it_t == "ClassLiteral":
                    items.append(IR.IRClassLiteral(it.ch))  # type: ignore
                elif it_t == "ClassEscape":
                    items.append(IR.IRClassEscape(it.type, it.property))  # type: ignore
                else:
                    raise NotImplementedError(f"Unknown class item {it_t}")
            return IR.IRCharClass(node.negated, items)  # type: ignore
        if t == "Quant":
            return IR.IRQuant(self._lower(node.child), node.min, node.max, node.mode)  # type: ignore
        if t == "Group":
            return IR.IRGroup(node.capturing, self._lower(node.body), getattr(node, "name", None), getattr(node, "atomic", None))  # type: ignore
        if t == "Backref":
            return IR.IRBackref(getattr(node, "byIndex", None), getattr(node, "byName", None))  # type: ignore
        if t == "Look":
            return IR.IRLook(node.dir, node.neg, self._lower(node.body))  # type: ignore
        raise NotImplementedError(f"No lowering for AST node {t}")

    # ---------- Normalization ----------
    def _normalize(self, node: IR.IROp) -> IR.IROp:
        """Flatten alt/seq and fuse adjacent literals."""
        if isinstance(node, IR.IRSeq):
            parts = []
            for p in node.parts:
                p_norm = self._normalize(p)
                if isinstance(p_norm, IR.IRSeq):
                    parts.extend(p_norm.parts)
                else:
                    parts.append(p_norm)
            fused = []
            buf = ""
            for p in parts:
                if isinstance(p, IR.IRLit):
                    buf += p.value
                else:
                    if buf:
                        fused.append(IR.IRLit(buf))
                        buf = ""
                    fused.append(p)
            if buf:
                fused.append(IR.IRLit(buf))
            return fused[0] if len(fused)==1 else IR.IRSeq(fused)
        if isinstance(node, IR.IRAlt):
            branches = []
            for b in node.branches:
                b_norm = self._normalize(b)
                if isinstance(b_norm, IR.IRAlt):
                    branches.extend(b_norm.branches)
                else:
                    branches.append(b_norm)
            return branches[0] if len(branches)==1 else IR.IRAlt(branches)
        if isinstance(node, IR.IRQuant):
            child = self._normalize(node.child)
            return IR.IRQuant(child, node.min, node.max, node.mode)
        if isinstance(node, IR.IRGroup):
            return IR.IRGroup(node.capturing, self._normalize(node.body), node.name, node.atomic)
        if isinstance(node, IR.IRLook):
            return IR.IRLook(node.dir, node.neg, self._normalize(node.body))
        return node
