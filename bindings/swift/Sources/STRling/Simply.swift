/// STRling Simply API
///
/// This module provides the Simply API for building regex patterns using a fluent,
/// chainable interface. It provides static wrapper functions on the Simply struct
/// to match the specification format s.capture(...) and s.digit(...).
///
/// The Simply API is designed to be intuitive and self-documenting, replacing
/// cryptic regex syntax with readable function calls.

import Foundation

// MARK: - SimplyPattern Class

/// Represents a regex pattern in STRling's Simply API.
///
/// This is the core class that wraps internal AST nodes and provides a fluent,
/// chainable interface for pattern construction. SimplyPattern objects are immutable -
/// all modifier methods return new SimplyPattern instances rather than mutating the
/// original.
public class SimplyPattern {
    /// The internal AST node
    public let node: Node
    
    /// List of named capture groups in this pattern
    public let namedGroups: [String]
    
    /// Initialize a new SimplyPattern
    ///
    /// - Parameters:
    ///   - node: The AST node representing this pattern
    ///   - namedGroups: Named capture groups in this pattern
    public init(node: Node, namedGroups: [String] = []) {
        self.node = node
        self.namedGroups = namedGroups
    }
    
    /// Apply repetition to this pattern
    ///
    /// - Parameters:
    ///   - minRep: Minimum number of repetitions
    ///   - maxRep: Maximum number of repetitions (0 means unlimited, nil means exactly minRep)
    /// - Returns: A new SimplyPattern with the repetition applied
    public func rep(_ minRep: Int, _ maxRep: Int? = nil) -> SimplyPattern {
        let actualMax: QuantMax
        if let maxRep = maxRep {
            actualMax = maxRep == 0 ? .inf : .count(maxRep)
        } else {
            actualMax = .count(minRep)
        }
        
        let quantNode = Quant(child: self.node, min: minRep, max: actualMax, mode: "Greedy")
        return SimplyPattern(node: .quant(quantNode), namedGroups: self.namedGroups)
    }
    
    /// Compile this pattern to a regex string
    ///
    /// - Returns: The compiled PCRE2 regex string
    /// - Throws: CompilerError if compilation fails
    public func compile() throws -> String {
        return try PCRE2Emitter().emit(node: self.node)
    }
}

// MARK: - Simply Namespace

/// The Simply API namespace providing static methods for pattern construction.
///
/// This struct provides a clean namespace for all Simply API functions,
/// ensuring alignment with the core specification format (e.g., Simply.capture(...)).
public struct Simply {
    
    // Prevent instantiation
    private init() {}
    
    // MARK: - Atoms
    
    /// Match a specified number of digits
    ///
    /// - Parameter n: Number of digits to match
    /// - Returns: A SimplyPattern matching n digits
    public static func digit(_ n: Int) -> SimplyPattern {
        let charClass = CharClass(negated: false, items: [ClassEscape(type: "d")])
        let node = Quant(child: .charClass(charClass), min: n, max: .count(n), mode: "Greedy")
        return SimplyPattern(node: .quant(node))
    }
    
    /// Match any one of the provided characters
    ///
    /// - Parameter chars: String containing characters to match
    /// - Returns: A SimplyPattern matching any of the characters
    /// - Note: Special regex characters are automatically escaped by the emitter
    public static func anyOf(_ chars: String) -> SimplyPattern {
        let items = chars.map { ClassLiteral(ch: String($0)) as ClassItem }
        let charClass = CharClass(negated: false, items: items)
        return SimplyPattern(node: .charClass(charClass))
    }
    
    /// Match the start of the string
    ///
    /// - Returns: A SimplyPattern matching the start anchor
    public static func start() -> SimplyPattern {
        let anchor = Anchor(at: "Start")
        return SimplyPattern(node: .anchor(anchor))
    }
    
    /// Match the end of the string
    ///
    /// - Returns: A SimplyPattern matching the end anchor
    public static func end() -> SimplyPattern {
        let anchor = Anchor(at: "End")
        return SimplyPattern(node: .anchor(anchor))
    }
    
    // MARK: - Wrappers
    
    /// Merge multiple patterns into a sequence
    ///
    /// - Parameter patterns: Array of patterns to merge
    /// - Returns: A SimplyPattern representing the concatenated sequence
    public static func merge(_ patterns: [SimplyPattern]) -> SimplyPattern {
        let nodes = patterns.map { $0.node }
        let allNamedGroups = patterns.flatMap { $0.namedGroups }
        
        if nodes.count == 1 {
            return patterns[0]
        }
        
        let seq = Seq(parts: nodes)
        return SimplyPattern(node: .seq(seq), namedGroups: allNamedGroups)
    }
    
    /// Create a numbered capture group
    ///
    /// - Parameter pattern: The pattern to capture
    /// - Returns: A SimplyPattern representing the capture group
    public static func capture(_ pattern: SimplyPattern) -> SimplyPattern {
        let group = Group(capturing: true, body: pattern.node, name: nil)
        return SimplyPattern(node: .group(group), namedGroups: pattern.namedGroups)
    }
    
    /// Make a pattern optional (0 or 1 occurrences)
    ///
    /// - Parameter pattern: The pattern to make optional
    /// - Returns: A SimplyPattern that is optional
    public static func may(_ pattern: SimplyPattern) -> SimplyPattern {
        let quantNode = Quant(child: pattern.node, min: 0, max: .count(1), mode: "Greedy")
        return SimplyPattern(node: .quant(quantNode), namedGroups: pattern.namedGroups)
    }
}
