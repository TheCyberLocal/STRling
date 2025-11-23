"""
STRling Intermediate Representation (IR) Node Definitions

This module defines the complete set of IR node classes that represent
language-agnostic regex constructs. The IR serves as an intermediate layer
between the parsed AST and the target-specific emitters (e.g., PCRE2).

IR nodes are designed to be:
  - Simple and composable
  - Easy to serialize (via to_dict methods)
  - Independent of any specific regex flavor
  - Optimized for transformation and analysis

Each IR node corresponds to a fundamental regex operation (alternation,
sequencing, character classes, quantification, etc.) and can be serialized
to a dictionary representation for further processing or debugging.
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import List, Optional, Union, Any, Dict


class IROp:
    """
    Base class for all IR operations.

    All IR nodes extend this base class and must implement the to_dict() method
    for serialization to a dictionary representation.
    """

    def to_dict(self) -> Dict[str, Any]:
        """
        Serialize the IR node to a dictionary representation.

        Returns:
            The dictionary representation of this IR node.

        Raises:
            NotImplementedError: If not implemented by subclass.
        """
        raise NotImplementedError


@dataclass
class IRAlt(IROp):
    """
    Represents an alternation (OR) operation in the IR.

    Matches any one of the provided branches. Equivalent to the | operator
    in traditional regex syntax.
    """

    branches: List["IROp"]

    def to_dict(self) -> Dict[str, Any]:
        return {"ir": "Alt", "branches": [b.to_dict() for b in self.branches]}


@dataclass
class IRSeq(IROp):
    parts: List["IROp"]

    def to_dict(self) -> Dict[str, Any]:
        return {"ir": "Seq", "parts": [p.to_dict() for p in self.parts]}


@dataclass
class IRLit(IROp):
    value: str

    def to_dict(self) -> Dict[str, Any]:
        return {"ir": "Lit", "value": self.value}


@dataclass
class IRDot(IROp):
    def to_dict(self) -> Dict[str, Any]:
        return {"ir": "Dot"}


@dataclass
class IRAnchor(IROp):
    at: str

    def to_dict(self) -> Dict[str, Any]:
        return {"ir": "Anchor", "at": self.at}


@dataclass
class IRClassItem:
    def to_dict(self) -> Dict[str, Any]:
        raise NotImplementedError("Subclasses must implement to_dict method")


@dataclass
class IRClassRange(IRClassItem):
    from_ch: str
    to_ch: str

    def to_dict(self) -> Dict[str, Any]:
        return {"ir": "Range", "from": self.from_ch, "to": self.to_ch}


@dataclass
class IRClassLiteral(IRClassItem):
    ch: str

    def to_dict(self) -> Dict[str, Any]:
        return {"ir": "Char", "char": self.ch}


@dataclass
class IRClassEscape(IRClassItem):
    type: str
    property: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        d = {"ir": "Esc", "type": self.type}
        if self.property:
            d["property"] = self.property
        return d


@dataclass
class IRCharClass(IROp):
    negated: bool
    items: List[IRClassItem]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ir": "CharClass",
            "negated": self.negated,
            "items": [i.to_dict() for i in self.items],
        }


@dataclass
class IRQuant(IROp):
    child: IROp
    min: int
    max: Union[int, str]
    mode: str  # Greedy|Lazy|Possessive

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ir": "Quant",
            "child": self.child.to_dict(),
            "min": self.min,
            "max": self.max,
            "mode": self.mode,
        }


@dataclass
class IRGroup(IROp):
    capturing: bool
    body: IROp
    name: Optional[str] = None
    atomic: Optional[bool] = None

    def to_dict(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {
            "ir": "Group",
            "capturing": self.capturing,
            "body": self.body.to_dict(),
        }
        if self.name is not None:
            d["name"] = self.name
        if self.atomic is not None:
            d["atomic"] = self.atomic
        return d


@dataclass
class IRBackref(IROp):
    byIndex: Optional[int] = None
    byName: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {"ir": "Backref"}
        if self.byIndex is not None:
            d["byIndex"] = self.byIndex
        if self.byName is not None:
            d["byName"] = self.byName
        return d


@dataclass
class IRLook(IROp):
    dir: str
    neg: bool
    body: IROp

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ir": "Look",
            "dir": self.dir,
            "neg": self.neg,
            "body": self.body.to_dict(),
        }
