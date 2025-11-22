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

// MARK: - Codable Conformance

extension IRQuantMax: Codable {
    public init(from decoder: Decoder) throws {
        let container = try decoder.singleValueContainer()
        if let intVal = try? container.decode(Int.self) {
            self = .count(intVal)
        } else if let strVal = try? container.decode(String.self), strVal == "Inf" {
            self = .inf
        } else {
            throw DecodingError.dataCorruptedError(in: container, debugDescription: "Invalid IRQuantMax value")
        }
    }

    public func encode(to encoder: Encoder) throws {
        var container = encoder.singleValueContainer()
        switch self {
        case .count(let n): try container.encode(n)
        case .inf: try container.encode("Inf")
        }
    }
}

extension IROp: Codable {
    enum CodingKeys: String, CodingKey {
        case ir
    }

    public init(from decoder: Decoder) throws {
        let container = try decoder.container(keyedBy: CodingKeys.self)
        let type = try container.decode(String.self, forKey: .ir)

        switch type {
        case "Alt":
            self = .alt(try IRAlt(from: decoder))
        case "Seq":
            self = .seq(try IRSeq(from: decoder))
        case "Lit":
            self = .lit(try IRLit(from: decoder))
        case "Dot":
            self = .dot(try IRDot(from: decoder))
        case "Anchor":
            self = .anchor(try IRAnchor(from: decoder))
        case "CharClass":
            self = .charClass(try IRCharClass(from: decoder))
        case "Quant":
            self = .quant(try IRQuant(from: decoder))
        case "Group":
            self = .group(try IRGroup(from: decoder))
        case "Backref":
            self = .backref(try IRBackref(from: decoder))
        case "Look":
            self = .look(try IRLook(from: decoder))
        default:
            throw DecodingError.dataCorruptedError(forKey: .ir, in: container, debugDescription: "Unknown IR op type: \(type)")
        }
    }

    public func encode(to encoder: Encoder) throws {
        // Encoding implementation omitted
    }
}

extension IRAlt: Codable {
    enum CodingKeys: String, CodingKey {
        case branches
    }
}

extension IRSeq: Codable {
    enum CodingKeys: String, CodingKey {
        case parts
    }
}

extension IRLit: Codable {
    enum CodingKeys: String, CodingKey {
        case value
    }
}

extension IRDot: Codable {
    public init(from decoder: Decoder) throws {
        self.init()
    }

    public func encode(to encoder: Encoder) throws {
        // Omitted
    }
}

extension IRAnchor: Codable {
    enum CodingKeys: String, CodingKey {
        case at
    }
}

// Helper for decoding IRClassItems
struct AnyIRClassItem: Codable {
    let item: IRClassItem

    enum CodingKeys: String, CodingKey {
        case ir
    }

    init(from decoder: Decoder) throws {
        let container = try decoder.container(keyedBy: CodingKeys.self)
        let type = try container.decode(String.self, forKey: .ir)

        switch type {
        case "Range":
            self.item = try IRClassRange(from: decoder)
        case "Char":
            self.item = try IRClassLiteral(from: decoder)
        case "Esc":
            self.item = try IRClassEscape(from: decoder)
        default:
            throw DecodingError.dataCorruptedError(forKey: .ir, in: container, debugDescription: "Unknown IR class item type: \(type)")
        }
    }

    func encode(to encoder: Encoder) throws {
        // Omitted
    }
}

extension IRClassRange: Codable {
    enum CodingKeys: String, CodingKey {
        case fromCh = "from"
        case toCh = "to"
    }
}

extension IRClassLiteral: Codable {
    enum CodingKeys: String, CodingKey {
        case ch = "char"
    }
}

extension IRClassEscape: Codable {
    enum CodingKeys: String, CodingKey {
        case type
        case property
    }
}

extension IRCharClass: Codable {
    enum CodingKeys: String, CodingKey {
        case negated
        case items
    }

    public init(from decoder: Decoder) throws {
        let container = try decoder.container(keyedBy: CodingKeys.self)
        self.negated = try container.decode(Bool.self, forKey: .negated)
        let anyItems = try container.decode([AnyIRClassItem].self, forKey: .items)
        self.items = anyItems.map { -bash.item }
    }

    public func encode(to encoder: Encoder) throws {
        // Omitted
    }
}

extension IRQuant: Codable {
    enum CodingKeys: String, CodingKey {
        case child
        case min
        case max
        case mode
    }
}

extension IRGroup: Codable {
    enum CodingKeys: String, CodingKey {
        case capturing
        case body
        case name
        case atomic
    }
}

extension IRBackref: Codable {
    enum CodingKeys: String, CodingKey {
        case byIndex
        case byName
    }
}

extension IRLook: Codable {
    enum CodingKeys: String, CodingKey {
        case dir
        case neg
        case body
    }
}

// Equatable conformance for testing
extension IROp: Equatable {
    public static func == (lhs: IROp, rhs: IROp) -> Bool {
        switch (lhs, rhs) {
        case (.alt(let l), .alt(let r)): return l == r
        case (.seq(let l), .seq(let r)): return l == r
        case (.lit(let l), .lit(let r)): return l == r
        case (.dot, .dot): return true
        case (.anchor(let l), .anchor(let r)): return l == r
        case (.charClass(let l), .charClass(let r)): return l == r
        case (.quant(let l), .quant(let r)): return l == r
        case (.group(let l), .group(let r)): return l == r
        case (.backref(let l), .backref(let r)): return l == r
        case (.look(let l), .look(let r)): return l == r
        default: return false
        }
    }
}

extension IRAlt: Equatable {
    public static func == (lhs: IRAlt, rhs: IRAlt) -> Bool {
        return lhs.branches == rhs.branches
    }
}

extension IRSeq: Equatable {
    public static func == (lhs: IRSeq, rhs: IRSeq) -> Bool {
        return lhs.parts == rhs.parts
    }
}

extension IRLit: Equatable {
    public static func == (lhs: IRLit, rhs: IRLit) -> Bool {
        return lhs.value == rhs.value
    }
}

extension IRAnchor: Equatable {
    public static func == (lhs: IRAnchor, rhs: IRAnchor) -> Bool {
        return lhs.at == rhs.at
    }
}

extension IRCharClass: Equatable {
    public static func == (lhs: IRCharClass, rhs: IRCharClass) -> Bool {
        guard lhs.negated == rhs.negated else { return false }
        guard lhs.items.count == rhs.items.count else { return false }
        // Simple check, assuming order matters or items are comparable
        // Since IRClassItem is a protocol, we can't easily equate arrays of them without type erasure or casting
        // For now, let's rely on string representation or assume they are same type and order
        for (i, item) in lhs.items.enumerated() {
            if !areEqual(item, rhs.items[i]) { return false }
        }
        return true
    }
}

func areEqual(_ lhs: IRClassItem, _ rhs: IRClassItem) -> Bool {
    if let l = lhs as? IRClassRange, let r = rhs as? IRClassRange { return l == r }
    if let l = lhs as? IRClassLiteral, let r = rhs as? IRClassLiteral { return l == r }
    if let l = lhs as? IRClassEscape, let r = rhs as? IRClassEscape { return l == r }
    return false
}

extension IRClassRange: Equatable {}
extension IRClassLiteral: Equatable {}
extension IRClassEscape: Equatable {}

extension IRQuant: Equatable {
    public static func == (lhs: IRQuant, rhs: IRQuant) -> Bool {
        return lhs.child == rhs.child && lhs.min == rhs.min && lhs.max == rhs.max && lhs.mode == rhs.mode
    }
}

extension IRQuantMax: Equatable {}

extension IRGroup: Equatable {
    public static func == (lhs: IRGroup, rhs: IRGroup) -> Bool {
        return lhs.capturing == rhs.capturing && lhs.body == rhs.body && lhs.name == rhs.name && lhs.atomic == rhs.atomic
    }
}

extension IRBackref: Equatable {
    public static func == (lhs: IRBackref, rhs: IRBackref) -> Bool {
        return lhs.byIndex == rhs.byIndex && lhs.byName == rhs.byName
    }
}

extension IRLook: Equatable {
    public static func == (lhs: IRLook, rhs: IRLook) -> Bool {
        return lhs.dir == rhs.dir && lhs.neg == rhs.neg && lhs.body == rhs.body
    }
}
