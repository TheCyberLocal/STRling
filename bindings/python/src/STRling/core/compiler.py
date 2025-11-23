"""
STRling Compiler - AST to IR Transformation

This module implements the compiler that transforms Abstract Syntax Tree (AST)
nodes from the parser into an optimized Intermediate Representation (IR). The
compilation process includes:
  - Lowering AST nodes to IR operations
  - Flattening nested sequences and alternations
  - Coalescing adjacent literal nodes for efficiency
  - Ensuring quantifier children are properly grouped
  - Analyzing and tracking regex features used

The IR is designed to be easily consumed by target emitters (e.g., PCRE2)
while maintaining semantic accuracy and enabling optimizations.
"""

from __future__ import annotations
from STRling.core import nodes as N, ir as IR
from typing import cast


class Compiler:
    """
    Compiler for transforming AST nodes into optimized IR.

    The Compiler class handles the complete transformation pipeline from parsed
    AST to normalized IR, including feature detection for metadata generation.

    AST -> IR lowering with normalization:
      - Flatten nested Seq/Alt
      - Coalesce adjacent Lit nodes
      - Ensure quantifier children are grouped appropriately
    """

    def __init__(self) -> None:
        self.features_used: set[str] = set()

    def compile_with_metadata(self, root_node: N.Node) -> dict[str, object]:
        """
        Compile an AST node and return IR with metadata.

        This is the main entry point for compilation with full metadata tracking.
        It performs lowering, normalization, and feature analysis.

        Args:
            root_node: The root AST node to compile.

        Returns:
            Dictionary containing the compiled IR and metadata about features used.
        """
        ir_root = self._lower(root_node)
        ir_root = self._normalize(ir_root)

        # New step: Analyze the final IR tree for special features
        self._analyze_features(ir_root)

        return {
            "ir": ir_root,  # Return the IR object, not a dict
            "metadata": {"features_used": sorted(list(self.features_used))},
        }

    def _analyze_features(self, node: IR.IROp) -> None:
        """Recursively walk the IR tree and log features used."""
        if isinstance(node, IR.IRGroup):
            if node.atomic:
                self.features_used.add("atomic_group")
            if node.name is not None:
                self.features_used.add("named_group")
        if isinstance(node, IR.IRQuant) and node.mode == "Possessive":
            self.features_used.add("possessive_quantifier")
        if isinstance(node, IR.IRLook):
            if node.dir == "Behind":
                self.features_used.add("lookbehind")
            elif node.dir == "Ahead":
                self.features_used.add("lookahead")
        if isinstance(node, IR.IRBackref):
            self.features_used.add("backreference")
        if isinstance(node, IR.IRCharClass):
            # Check for Unicode property escapes in character class items
            for item in node.items:
                if (
                    isinstance(item, IR.IRClassEscape)
                    and item.type == "UnicodeProperty"
                ):
                    self.features_used.add("unicode_property")

        # --- Recurse into children ---
        if isinstance(node, (IR.IRSeq, IR.IRAlt)):
            for child in node.parts if isinstance(node, IR.IRSeq) else node.branches:
                self._analyze_features(child)
        elif isinstance(node, IR.IRQuant):
            self._analyze_features(node.child)
        elif isinstance(node, (IR.IRGroup, IR.IRLook)):
            self._analyze_features(node.body)

    def compile(self, root: N.Node) -> IR.IROp:
        ir = self._lower(root)
        ir = self._normalize(ir)
        return ir

    # ---------- Lowering (AST -> IR) ----------
    def _lower(self, node: N.Node) -> IR.IROp:
        t = type(node).__name__
        if t == "Sequence":
            return IR.IRSeq([self._lower(p) for p in node.parts])  # type: ignore
        if t == "Alternation":
            return IR.IRAlt([self._lower(b) for b in node.branches])  # type: ignore
        if t == "Literal":
            return IR.IRLit(node.value)  # type: ignore
        if t == "Dot":
            return IR.IRDot()
        if t == "Anchor":
            return IR.IRAnchor(node.at)  # type: ignore
        if t == "CharacterClass":
            items = []
            for it in node.items:  # type: ignore
                it = cast(N.Node, it)  # Cast to Node type to satisfy the type checker
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
        if t == "Quantifier":
            return IR.IRQuant(self._lower(node.child), node.min, node.max, node.mode)  # type: ignore
        if t == "Group":
            group_node = cast(N.Group, node)
            return IR.IRGroup(
                group_node.capturing,
                self._lower(group_node.body),
                getattr(group_node, "name", None),
                getattr(group_node, "atomic", None),
            )  # type: ignore
        if t == "BackReference":
            return IR.IRBackref(
                getattr(node, "byIndex", None), getattr(node, "byName", None)
            )  # type: ignore
        if t == "Lookaround":
            look_node = cast(N.Lookaround, node)
            return IR.IRLook(look_node.dir, look_node.neg, self._lower(look_node.body))  # type: ignore
        raise NotImplementedError(f"No lowering for AST node {t}")

    # ---------- Normalization ----------
    def _normalize(self, node: IR.IROp) -> IR.IROp:
        """Flatten alt/seq and fuse adjacent literals."""
        if isinstance(node, IR.IRSeq):
            parts: list[IR.IROp] = []
            for p in node.parts:
                p_norm = self._normalize(p)
                if isinstance(p_norm, IR.IRSeq):
                    parts.extend(p_norm.parts)
                else:
                    parts.append(p_norm)
            fused: list[IR.IROp] = []
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
            return fused[0] if len(fused) == 1 else IR.IRSeq(fused)
        if isinstance(node, IR.IRAlt):
            branches: list[IR.IROp] = []
            for b in node.branches:
                b_norm = self._normalize(b)
                if isinstance(b_norm, IR.IRAlt):
                    branches.extend(b_norm.branches)
                else:
                    branches.append(b_norm)
            return branches[0] if len(branches) == 1 else IR.IRAlt(branches)
        if isinstance(node, IR.IRQuant):
            child = self._normalize(node.child)
            return IR.IRQuant(child, node.min, node.max, node.mode)
        if isinstance(node, IR.IRGroup):
            return IR.IRGroup(
                node.capturing, self._normalize(node.body), node.name, node.atomic
            )
        if isinstance(node, IR.IRLook):
            return IR.IRLook(node.dir, node.neg, self._normalize(node.body))
        return node
