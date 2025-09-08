from __future__ import annotations
from dataclasses import dataclass
from typing import List, Optional, Union, Any, Dict


class IROp:
    """Base class for IR nodes (language-agnostic regex constructs)."""

    def to_dict(self) -> Dict[str, Any]:
        raise NotImplementedError


@dataclass
class IRAlt(IROp):
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
