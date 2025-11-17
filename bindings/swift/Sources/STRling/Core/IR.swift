/// STRling Intermediate Representation (IR) Node Definitions
///
/// This module defines the complete set of IR node classes that represent
/// language-agnostic regex constructs. The IR serves as an intermediate layer
/// between the parsed AST and the target-specific emitters (e.g., PCRE2).
///
/// IR nodes are designed to be:
///   - Simple and composable
///   - Easy to serialize (via toDict methods)
///   - Independent of any specific regex flavor
///   - Optimized for transformation and analysis
///
/// Each IR node corresponds to a fundamental regex operation (alternation,
/// sequencing, character classes, quantification, etc.) and can be serialized
/// to a dictionary representation for further processing or debugging.

import Foundation

// MARK: - IR Class Items

/// Base protocol for IR character class items
public protocol IRClassItem {
    /// Convert the class item to dictionary representation
    func toDict() -> [String: Any]
}

/// Represents a character range in IR character class (e.g., a-z)
public struct IRClassRange: IRClassItem {
    /// The starting character of the range
    public let fromCh: String
    
    /// The ending character of the range
    public let toCh: String
    
    /// Initialize an IR character range
    ///
    /// - Parameters:
    ///   - fromCh: The starting character
    ///   - toCh: The ending character
    public init(fromCh: String, toCh: String) {
        self.fromCh = fromCh
        self.toCh = toCh
    }
    
    public func toDict() -> [String: Any] {
        return [
            "ir": "Range",
            "from": fromCh,
            "to": toCh
        ]
    }
}

/// Represents a literal character in IR character class
public struct IRClassLiteral: IRClassItem {
    /// The literal character
    public let ch: String
    
    /// Initialize an IR character literal
    ///
    /// - Parameter ch: The literal character
    public init(ch: String) {
        self.ch = ch
    }
    
    public func toDict() -> [String: Any] {
        return [
            "ir": "Char",
            "char": ch
        ]
    }
}

/// Represents an escape sequence in IR character class (e.g., \d, \w, \s, \p{...})
public struct IRClassEscape: IRClassItem {
    /// The type of escape (d, D, w, W, s, S, p, P)
    public let type: String
    
    /// The Unicode property name (for \p and \P escapes)
    public let property: String?
    
    /// Initialize an IR class escape
    ///
    /// - Parameters:
    ///   - type: The type of escape
    ///   - property: Optional Unicode property name
    public init(type: String, property: String? = nil) {
        self.type = type
        self.property = property
    }
    
    public func toDict() -> [String: Any] {
        var d: [String: Any] = [
            "ir": "Esc",
            "type": type
        ]
        if let property = property {
            d["property"] = property
        }
        return d
    }
}

// MARK: - IR Operations

/// Enum representing all possible IR operation types.
///
/// This enum uses associated values to provide type-safe pattern matching
/// and easy traversal of the IR, following Swift best practices.
public indirect enum IROp {
    /// Alternation operation (OR)
    case alt(IRAlt)
    
    /// Sequence operation (concatenation)
    case seq(IRSeq)
    
    /// Literal string operation
    case lit(IRLit)
    
    /// Dot operation (matches any character)
    case dot(IRDot)
    
    /// Anchor operation (position assertion)
    case anchor(IRAnchor)
    
    /// Character class operation
    case charClass(IRCharClass)
    
    /// Quantifier operation
    case quant(IRQuant)
    
    /// Group operation
    case group(IRGroup)
    
    /// Backreference operation
    case backref(IRBackref)
    
    /// Lookaround operation
    case look(IRLook)
    
    /// Serialize the IR node to a dictionary representation.
    ///
    /// - Returns: The dictionary representation of this IR node
    public func toDict() -> [String: Any] {
        switch self {
        case .alt(let node):
            return node.toDict()
        case .seq(let node):
            return node.toDict()
        case .lit(let node):
            return node.toDict()
        case .dot(let node):
            return node.toDict()
        case .anchor(let node):
            return node.toDict()
        case .charClass(let node):
            return node.toDict()
        case .quant(let node):
            return node.toDict()
        case .group(let node):
            return node.toDict()
        case .backref(let node):
            return node.toDict()
        case .look(let node):
            return node.toDict()
        }
    }
}

/// Represents an alternation (OR) operation in the IR.
///
/// Matches any one of the provided branches. Equivalent to the | operator
/// in traditional regex syntax.
public struct IRAlt {
    /// The alternative branches
    public let branches: [IROp]
    
    /// Initialize an IR alternation
    ///
    /// - Parameter branches: The alternative branches
    public init(branches: [IROp]) {
        self.branches = branches
    }
    
    /// Serialize to dictionary
    public func toDict() -> [String: Any] {
        return [
            "ir": "Alt",
            "branches": branches.map { $0.toDict() }
        ]
    }
}

/// Represents a sequence (concatenation) operation in the IR.
public struct IRSeq {
    /// The parts of the sequence
    public let parts: [IROp]
    
    /// Initialize an IR sequence
    ///
    /// - Parameter parts: The parts to concatenate
    public init(parts: [IROp]) {
        self.parts = parts
    }
    
    /// Serialize to dictionary
    public func toDict() -> [String: Any] {
        return [
            "ir": "Seq",
            "parts": parts.map { $0.toDict() }
        ]
    }
}

/// Represents a literal string operation in the IR.
public struct IRLit {
    /// The literal string value
    public let value: String
    
    /// Initialize an IR literal
    ///
    /// - Parameter value: The literal string
    public init(value: String) {
        self.value = value
    }
    
    /// Serialize to dictionary
    public func toDict() -> [String: Any] {
        return [
            "ir": "Lit",
            "value": value
        ]
    }
}

/// Represents a dot (.) operation in the IR - matches any character.
public struct IRDot {
    /// Initialize an IR dot
    public init() {}
    
    /// Serialize to dictionary
    public func toDict() -> [String: Any] {
        return ["ir": "Dot"]
    }
}

/// Represents an anchor (position assertion) operation in the IR.
public struct IRAnchor {
    /// The anchor type
    public let at: String
    
    /// Initialize an IR anchor
    ///
    /// - Parameter at: The anchor type
    public init(at: String) {
        self.at = at
    }
    
    /// Serialize to dictionary
    public func toDict() -> [String: Any] {
        return [
            "ir": "Anchor",
            "at": at
        ]
    }
}

/// Represents a character class operation in the IR.
public struct IRCharClass {
    /// Whether the character class is negated
    public let negated: Bool
    
    /// The items in the character class
    public let items: [IRClassItem]
    
    /// Initialize an IR character class
    ///
    /// - Parameters:
    ///   - negated: Whether the class is negated
    ///   - items: The items in the class
    public init(negated: Bool, items: [IRClassItem]) {
        self.negated = negated
        self.items = items
    }
    
    /// Serialize to dictionary
    public func toDict() -> [String: Any] {
        return [
            "ir": "CharClass",
            "negated": negated,
            "items": items.map { $0.toDict() }
        ]
    }
}

/// Represents a quantifier operation in the IR.
public struct IRQuant {
    /// The child operation being quantified
    public let child: IROp
    
    /// Minimum number of repetitions
    public let min: Int
    
    /// Maximum number of repetitions
    public let max: IRQuantMax
    
    /// Quantifier mode: "Greedy", "Lazy", or "Possessive"
    public let mode: String
    
    /// Initialize an IR quantifier
    ///
    /// - Parameters:
    ///   - child: The operation to quantify
    ///   - min: Minimum repetitions
    ///   - max: Maximum repetitions
    ///   - mode: The quantifier mode
    public init(child: IROp, min: Int, max: IRQuantMax, mode: String) {
        self.child = child
        self.min = min
        self.max = max
        self.mode = mode
    }
    
    /// Serialize to dictionary
    public func toDict() -> [String: Any] {
        return [
            "ir": "Quant",
            "child": child.toDict(),
            "min": min,
            "max": max.toValue(),
            "mode": mode
        ]
    }
}

/// Represents the maximum value for an IR quantifier
public enum IRQuantMax {
    /// Specific number of repetitions
    case count(Int)
    
    /// Infinite repetitions
    case inf
    
    /// Convert to value (Int or String "Inf")
    func toValue() -> Any {
        switch self {
        case .count(let n):
            return n
        case .inf:
            return "Inf"
        }
    }
}

/// Represents a group operation in the IR.
public struct IRGroup {
    /// Whether the group is capturing
    public let capturing: Bool
    
    /// The body of the group
    public let body: IROp
    
    /// Optional group name (for named captures)
    public let name: String?
    
    /// Whether the group is atomic
    public let atomic: Bool?
    
    /// Initialize an IR group
    ///
    /// - Parameters:
    ///   - capturing: Whether the group captures
    ///   - body: The group body
    ///   - name: Optional group name
    ///   - atomic: Optional atomic flag
    public init(capturing: Bool, body: IROp, name: String? = nil, atomic: Bool? = nil) {
        self.capturing = capturing
        self.body = body
        self.name = name
        self.atomic = atomic
    }
    
    /// Serialize to dictionary
    public func toDict() -> [String: Any] {
        var d: [String: Any] = [
            "ir": "Group",
            "capturing": capturing,
            "body": body.toDict()
        ]
        if let name = name {
            d["name"] = name
        }
        if let atomic = atomic {
            d["atomic"] = atomic
        }
        return d
    }
}

/// Represents a backreference operation in the IR.
public struct IRBackref {
    /// Reference by numeric index
    public let byIndex: Int?
    
    /// Reference by name
    public let byName: String?
    
    /// Initialize an IR backreference
    ///
    /// - Parameters:
    ///   - byIndex: Optional numeric index
    ///   - byName: Optional name
    public init(byIndex: Int? = nil, byName: String? = nil) {
        self.byIndex = byIndex
        self.byName = byName
    }
    
    /// Serialize to dictionary
    public func toDict() -> [String: Any] {
        var d: [String: Any] = ["ir": "Backref"]
        if let byIndex = byIndex {
            d["byIndex"] = byIndex
        }
        if let byName = byName {
            d["byName"] = byName
        }
        return d
    }
}

/// Represents a lookaround operation in the IR.
public struct IRLook {
    /// Direction: "Ahead" or "Behind"
    public let dir: String
    
    /// Whether the assertion is negative
    public let neg: Bool
    
    /// The body of the assertion
    public let body: IROp
    
    /// Initialize an IR lookaround
    ///
    /// - Parameters:
    ///   - dir: The direction ("Ahead" or "Behind")
    ///   - neg: Whether it's negative
    ///   - body: The assertion body
    public init(dir: String, neg: Bool, body: IROp) {
        self.dir = dir
        self.neg = neg
        self.body = body
    }
    
    /// Serialize to dictionary
    public func toDict() -> [String: Any] {
        return [
            "ir": "Look",
            "dir": dir,
            "neg": neg,
            "body": body.toDict()
        ]
    }
}
