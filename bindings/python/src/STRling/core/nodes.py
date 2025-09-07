"""
STRling v3 — AST node definitions (Sprint 3)
The AST serializes to the Base TargetArtifact schema's Node defs.
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import List, Optional, Union, Dict, Any


# ---- Flags container ----
@dataclass
class Flags:
    ignoreCase: bool = False
    multiline: bool = False
    dotAll: bool = False
    unicode: bool = False
    extended: bool = False

    def to_dict(self) -> Dict[str, bool]:
        return {
            "ignoreCase": self.ignoreCase,
            "multiline": self.multiline,
            "dotAll": self.dotAll,
            "unicode": self.unicode,
            "extended": self.extended,
        }

    @staticmethod
    def from_letters(letters: str) -> "Flags":
        f = Flags()
        for ch in letters.replace(",", "").replace(" ", ""):
            if ch == "i":
                f.ignoreCase = True
            elif ch == "m":
                f.multiline = True
            elif ch == "s":
                f.dotAll = True
            elif ch == "u":
                f.unicode = True
            elif ch == "x":
                f.extended = True
            elif ch == "":
                pass
            else:
                # Unknown flags are ignored at parser stage; may be warned later
                pass
        return f


# ---- Base node ----
class Node:
    def to_dict(self) -> Dict[str, Union[str, int]]:
        raise NotImplementedError()


# ---- Concrete nodes matching Base Schema ----
@dataclass
class Alt(Node):
    branches: List[Node]

    def to_dict(self) -> Dict[str, Any]:
        return {"kind": "Alt", "branches": [b.to_dict() for b in self.branches]}


@dataclass
class Seq(Node):
    parts: List[Node]

    def to_dict(self) -> Dict[str, Any]:
        return {"kind": "Seq", "parts": [p.to_dict() for p in self.parts]}


@dataclass
class Lit(Node):
    value: str

    def to_dict(self) -> Dict[str, Any]:
        return {"kind": "Lit", "value": self.value}


@dataclass
class Dot(Node):
    def to_dict(self) -> Dict[str, Any]:
        return {"kind": "Dot"}


@dataclass
class Anchor(Node):
    at: str  # "Start"|"End"|"WordBoundary"|"NotWordBoundary"|Absolute* variants

    def to_dict(self) -> Dict[str, Any]:
        return {"kind": "Anchor", "at": self.at}


# --- CharClass --
@dataclass
class ClassItem:
    def to_dict(self) -> Dict[str, Any]:
        raise NotImplementedError("Subclasses must implement the to_dict method.")


@dataclass
class ClassRange(ClassItem):
    from_ch: str
    to_ch: str

    def to_dict(self) -> Dict[str, Any]:
        return {"kind": "Range", "from": self.from_ch, "to": self.to_ch}


@dataclass
class ClassLiteral(ClassItem):
    ch: str

    def to_dict(self) -> Dict[str, Any]:
        return {"kind": "Char", "char": self.ch}


@dataclass
class ClassEscape(ClassItem):
    type: str  # d D w W s S p P
    property: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        data = {"kind": "Esc", "type": self.type}
        if self.type in ("p", "P") and self.property:
            data["property"] = self.property
        return data


@dataclass
class CharClass(Node):
    negated: bool
    items: List[ClassItem]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "kind": "CharClass",
            "negated": self.negated,
            "items": [it.to_dict() for it in self.items],
        }


@dataclass
class Quant(Node):
    child: Node
    min: int
    max: Union[int, str]  # "Inf" for unbounded
    mode: str  # "Greedy" | "Lazy" | "Possessive"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "kind": "Quant",
            "child": self.child.to_dict(),
            "min": self.min,
            "max": self.max,
            "mode": self.mode,
        }


@dataclass
class Group(Node):
    capturing: bool
    body: Node
    name: Optional[str] = None
    atomic: Optional[bool] = None  # extension

    def to_dict(self) -> Dict[str, Any]:
        data: Dict[str, Any] = {
            "kind": "Group",
            "capturing": self.capturing,
            "body": self.body.to_dict(),
        }
        if self.name is not None:
            data["name"] = self.name
        if self.atomic is not None:
            data["atomic"] = self.atomic
        return data


@dataclass
class Backref(Node):
    byIndex: Optional[int] = None
    byName: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        data = {"kind": "Backref"}
        if self.byIndex is not None:
            data["byIndex"] = str(self.byIndex)
        if self.byName is not None:
            data["byName"] = self.byName
        return data


@dataclass
class Look(Node):
    dir: str  # "Ahead" | "Behind"
    neg: bool
    body: Node

    def to_dict(self) -> Dict[str, Any]:
        return {
            "kind": "Look",
            "dir": self.dir,
            "neg": self.neg,
            "body": self.body.to_dict(),
        }
