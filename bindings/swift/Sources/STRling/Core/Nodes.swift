/// STRling AST Node Definitions
///
/// This module defines the complete set of Abstract Syntax Tree (AST) node classes
/// that represent the parsed structure of STRling patterns. The AST is the direct
/// output of the parser and represents the syntactic structure of the pattern before
/// optimization and lowering to IR.
///
/// AST nodes are designed to:
///   - Closely mirror the source pattern syntax
///   - Be easily serializable to the Base TargetArtifact schema
///   - Provide a clean separation between parsing and compilation
///   - Support multiple target regex flavors through the compilation pipeline
///
/// Each AST node type corresponds to a syntactic construct in the STRling DSL
/// (alternation, sequencing, character classes, anchors, etc.) and can be
/// serialized to a dictionary representation for debugging or storage.

import Foundation

// MARK: - Flags Container

/// Container for regex flags/modifiers.
///
/// Flags control the behavior of pattern matching (case sensitivity, multiline
/// mode, etc.). This struct encapsulates all standard regex flags.
public struct Flags {
    /// Case-insensitive matching
    public var ignoreCase: Bool
    
    /// Multiline mode (^ and $ match line boundaries)
    public var multiline: Bool
    
    /// Dot matches all characters including newlines
    public var dotAll: Bool
    
    /// Unicode-aware matching
    public var unicode: Bool
    
    /// Extended mode (ignore whitespace and allow comments)
    public var extended: Bool
    
    /// Initialize with default values (all flags disabled)
    public init(
        ignoreCase: Bool = false,
        multiline: Bool = false,
        dotAll: Bool = false,
        unicode: Bool = false,
        extended: Bool = false
    ) {
        self.ignoreCase = ignoreCase
        self.multiline = multiline
        self.dotAll = dotAll
        self.unicode = unicode
        self.extended = extended
    }
    
    /// Convert flags to dictionary representation
    ///
    /// - Returns: Dictionary with flag names as keys and their values
    public func toDict() -> [String: Bool] {
        return [
            "ignoreCase": ignoreCase,
            "multiline": multiline,
            "dotAll": dotAll,
            "unicode": unicode,
            "extended": extended
        ]
    }
    
    /// Create flags from letter string (e.g., "ims" for ignoreCase, multiline, dotAll)
    ///
    /// - Parameter letters: String containing flag letters (i, m, s, u, x)
    /// - Returns: Flags instance with appropriate flags enabled
    public static func fromLetters(_ letters: String) -> Flags {
        var flags = Flags()
        let cleanedLetters = letters.replacingOccurrences(of: ",", with: "")
                                   .replacingOccurrences(of: " ", with: "")
        
        for ch in cleanedLetters {
            switch ch {
            case "i":
                flags.ignoreCase = true
            case "m":
                flags.multiline = true
            case "s":
                flags.dotAll = true
            case "u":
                flags.unicode = true
            case "x":
                flags.extended = true
            default:
                // Unknown flags are ignored at parser stage; may be warned later
                break
            }
        }
        
        return flags
    }
}

// MARK: - Character Class Items

/// Base protocol for character class items
public protocol ClassItem {
    /// Convert the class item to dictionary representation
    func toDict() -> [String: Any]
}

/// Represents a character range in a character class (e.g., a-z)
public struct ClassRange: ClassItem {
    /// The starting character of the range
    public let fromCh: String
    
    /// The ending character of the range
    public let toCh: String
    
    /// Initialize a character range
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
            "kind": "Range",
            "from": fromCh,
            "to": toCh
        ]
    }
}

/// Represents a literal character in a character class
public struct ClassLiteral: ClassItem {
    /// The literal character
    public let ch: String
    
    /// Initialize a character literal
    ///
    /// - Parameter ch: The literal character
    public init(ch: String) {
        self.ch = ch
    }
    
    public func toDict() -> [String: Any] {
        return [
            "kind": "Char",
            "char": ch
        ]
    }
}

/// Represents an escape sequence in a character class (e.g., \d, \w, \s, \p{...})
public struct ClassEscape: ClassItem {
    /// The type of escape (d, D, w, W, s, S, p, P)
    public let type: String
    
    /// The Unicode property name (for \p and \P escapes)
    public let property: String?
    
    /// Initialize a class escape
    ///
    /// - Parameters:
    ///   - type: The type of escape
    ///   - property: Optional Unicode property name
    public init(type: String, property: String? = nil) {
        self.type = type
        self.property = property
    }
    
    public func toDict() -> [String: Any] {
        var data: [String: Any] = [
            "kind": "Esc",
            "type": type
        ]
        if let property = property, ["p", "P"].contains(type) {
            data["property"] = property
        }
        return data
    }
}

// MARK: - AST Nodes

/// Enum representing all possible AST node types.
///
/// This enum uses associated values to provide type-safe pattern matching
/// and easy traversal of the AST, following Swift best practices.
public indirect enum Node {
    /// Alternation node (branches separated by |)
    case alt(Alt)
    
    /// Sequence node (concatenation of parts)
    case seq(Seq)
    
    /// Literal string node
    case lit(Lit)
    
    /// Dot (.) - matches any character
    case dot(Dot)
    
    /// Anchor node (^, $, \b, \B)
    case anchor(Anchor)
    
    /// Character class node ([...])
    case charClass(CharClass)
    
    /// Quantifier node (*, +, ?, {n,m})
    case quant(Quant)
    
    /// Group node (capturing or non-capturing)
    case group(Group)
    
    /// Backreference node
    case backref(Backref)
    
    /// Lookaround assertion node
    case look(Look)
    
    /// Convert the node to dictionary representation
    ///
    /// - Returns: Dictionary representation of the node
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

/// Alternation node - represents a choice between multiple branches
public struct Alt {
    /// The alternative branches
    public let branches: [Node]
    
    /// Initialize an alternation node
    ///
    /// - Parameter branches: The alternative branches
    public init(branches: [Node]) {
        self.branches = branches
    }
    
    /// Convert to dictionary representation
    public func toDict() -> [String: Any] {
        return [
            "kind": "Alt",
            "branches": branches.map { $0.toDict() }
        ]
    }
}

/// Sequence node - represents concatenation of parts
public struct Seq {
    /// The parts of the sequence
    public let parts: [Node]
    
    /// Initialize a sequence node
    ///
    /// - Parameter parts: The parts to concatenate
    public init(parts: [Node]) {
        self.parts = parts
    }
    
    /// Convert to dictionary representation
    public func toDict() -> [String: Any] {
        return [
            "kind": "Seq",
            "parts": parts.map { $0.toDict() }
        ]
    }
}

/// Literal node - represents a literal string
public struct Lit {
    /// The literal string value
    public let value: String
    
    /// Initialize a literal node
    ///
    /// - Parameter value: The literal string
    public init(value: String) {
        self.value = value
    }
    
    /// Convert to dictionary representation
    public func toDict() -> [String: Any] {
        return [
            "kind": "Lit",
            "value": value
        ]
    }
}

/// Dot node - represents the . wildcard (matches any character)
public struct Dot {
    /// Initialize a dot node
    public init() {}
    
    /// Convert to dictionary representation
    public func toDict() -> [String: Any] {
        return ["kind": "Dot"]
    }
}

/// Anchor node - represents position assertions
public struct Anchor {
    /// The anchor type: "Start", "End", "WordBoundary", "NotWordBoundary", or Absolute* variants
    public let at: String
    
    /// Initialize an anchor node
    ///
    /// - Parameter at: The anchor type
    public init(at: String) {
        self.at = at
    }
    
    /// Convert to dictionary representation
    public func toDict() -> [String: Any] {
        return [
            "kind": "Anchor",
            "at": at
        ]
    }
}

/// Character class node - represents [...] constructs
public struct CharClass {
    /// Whether the character class is negated ([^...])
    public let negated: Bool
    
    /// The items in the character class
    public let items: [ClassItem]
    
    /// Initialize a character class node
    ///
    /// - Parameters:
    ///   - negated: Whether the class is negated
    ///   - items: The items in the class
    public init(negated: Bool, items: [ClassItem]) {
        self.negated = negated
        self.items = items
    }
    
    /// Convert to dictionary representation
    public func toDict() -> [String: Any] {
        return [
            "kind": "CharClass",
            "negated": negated,
            "items": items.map { $0.toDict() }
        ]
    }
}

/// Quantifier node - represents repetition (*, +, ?, {n,m})
public struct Quant {
    /// The child node being quantified
    public let child: Node
    
    /// Minimum number of repetitions
    public let min: Int
    
    /// Maximum number of repetitions ("Inf" for unbounded)
    public let max: QuantMax
    
    /// Quantifier mode: "Greedy", "Lazy", or "Possessive"
    public let mode: String
    
    /// Initialize a quantifier node
    ///
    /// - Parameters:
    ///   - child: The node to quantify
    ///   - min: Minimum repetitions
    ///   - max: Maximum repetitions
    ///   - mode: The quantifier mode
    public init(child: Node, min: Int, max: QuantMax, mode: String) {
        self.child = child
        self.min = min
        self.max = max
        self.mode = mode
    }
    
    /// Convert to dictionary representation
    public func toDict() -> [String: Any] {
        return [
            "kind": "Quant",
            "child": child.toDict(),
            "min": min,
            "max": max.toValue(),
            "mode": mode
        ]
    }
}

/// Represents the maximum value for a quantifier
public enum QuantMax {
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

/// Group node - represents capturing or non-capturing groups
public struct Group {
    /// Whether the group is capturing
    public let capturing: Bool
    
    /// The body of the group
    public let body: Node
    
    /// Optional group name (for named captures)
    public let name: String?
    
    /// Whether the group is atomic (extension)
    public let atomic: Bool?
    
    /// Initialize a group node
    ///
    /// - Parameters:
    ///   - capturing: Whether the group captures
    ///   - body: The group body
    ///   - name: Optional group name
    ///   - atomic: Optional atomic flag
    public init(capturing: Bool, body: Node, name: String? = nil, atomic: Bool? = nil) {
        self.capturing = capturing
        self.body = body
        self.name = name
        self.atomic = atomic
    }
    
    /// Convert to dictionary representation
    public func toDict() -> [String: Any] {
        var data: [String: Any] = [
            "kind": "Group",
            "capturing": capturing,
            "body": body.toDict()
        ]
        if let name = name {
            data["name"] = name
        }
        if let atomic = atomic {
            data["atomic"] = atomic
        }
        return data
    }
}

/// Backreference node - references a previous capturing group
public struct Backref {
    /// Reference by numeric index
    public let byIndex: Int?
    
    /// Reference by name
    public let byName: String?
    
    /// Initialize a backreference node
    ///
    /// - Parameters:
    ///   - byIndex: Optional numeric index
    ///   - byName: Optional name
    public init(byIndex: Int? = nil, byName: String? = nil) {
        self.byIndex = byIndex
        self.byName = byName
    }
    
    /// Convert to dictionary representation
    public func toDict() -> [String: Any] {
        var data: [String: Any] = ["kind": "Backref"]
        if let byIndex = byIndex {
            data["byIndex"] = byIndex
        }
        if let byName = byName {
            data["byName"] = byName
        }
        return data
    }
}

/// Lookaround assertion node - represents lookahead/lookbehind
public struct Look {
    /// Direction: "Ahead" or "Behind"
    public let dir: String
    
    /// Whether the assertion is negative
    public let neg: Bool
    
    /// The body of the assertion
    public let body: Node
    
    /// Initialize a lookaround node
    ///
    /// - Parameters:
    ///   - dir: The direction ("Ahead" or "Behind")
    ///   - neg: Whether it's negative
    ///   - body: The assertion body
    public init(dir: String, neg: Bool, body: Node) {
        self.dir = dir
        self.neg = neg
        self.body = body
    }
    
    /// Convert to dictionary representation
    public func toDict() -> [String: Any] {
        return [
            "kind": "Look",
            "dir": dir,
            "neg": neg,
            "body": body.toDict()
        ]
    }
}
