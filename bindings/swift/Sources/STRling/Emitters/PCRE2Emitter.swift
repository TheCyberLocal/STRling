import Foundation

/// PCRE2 Emitter
///
/// Compiles the STRling IR (AST) into a PCRE2-compatible regular expression string.
public class PCRE2Emitter {
    
    public init() {}
    
    /// Emit PCRE2 pattern from a Node
    ///
    /// - Parameter node: The root node of the AST
    /// - Returns: The compiled PCRE2 string
    public func emit(node: Node) throws -> String {
        switch node {
        case .alt(let n): return try emitAlt(n)
        case .seq(let n): return try emitSeq(n)
        case .lit(let n): return emitLit(n)
        case .dot(let n): return emitDot(n)
        case .anchor(let n): return try emitAnchor(n)
        case .charClass(let n): return try emitCharClass(n)
        case .quant(let n): return try emitQuant(n)
        case .group(let n): return try emitGroup(n)
        case .backref(let n): return try emitBackref(n)
        case .look(let n): return try emitLook(n)
        }
    }
    
    private func emitAlt(_ node: Alt) throws -> String {
        let branches = try node.branches.map { try emit(node: $0) }
        return branches.joined(separator: "|")
    }
    
    private func emitSeq(_ node: Seq) throws -> String {
        let parts = try node.parts.map { try emit(node: $0) }
        return parts.joined()
    }
    
    private func emitLit(_ node: Lit) -> String {
        // Escape special PCRE2 characters
        // Note: The list of special characters might need to be comprehensive
        let specialChars = "[\\]^$.|?*+(){}"
        return node.value.map { ch in
            if specialChars.contains(ch) {
                return "\\" + String(ch)
            }
            return String(ch)
        }.joined()
    }
    
    private func emitDot(_ node: Dot) -> String {
        return "."
    }
    
    private func emitAnchor(_ node: Anchor) throws -> String {
        switch node.at {
        case "Start", "AbsoluteStart": return "^"
        case "End", "AbsoluteEnd": return "$"
        case "WordBoundary": return "\\b"
        case "NotWordBoundary": return "\\B"
        default:
            throw EmitterError.unsupportedAnchor(node.at)
        }
    }
    
    private func emitCharClass(_ node: CharClass) throws -> String {
        var result = "["
        if node.negated {
            result += "^"
        }
        
        for item in node.items {
            if let range = item as? ClassRange {
                result += "\(range.fromCh)-\(range.toCh)"
            } else if let literal = item as? ClassLiteral {
                // Simple escaping for char class
                if "[]\\-^".contains(literal.ch) {
                    result += "\\" + literal.ch
                } else {
                    result += literal.ch
                }
            } else if let escape = item as? ClassEscape {
                if let prop = escape.property {
                    result += "\\\(escape.type){\(prop)}"
                } else {
                    result += "\\\(escape.type)"
                }
            }
        }
        
        result += "]"
        return result
    }
    
    private func emitQuant(_ node: Quant) throws -> String {
        let childStr = try emit(node: node.child)
        // Wrap child in non-capturing group if it's a sequence or alternation to ensure correct precedence
        let needsParens: Bool
        switch node.child {
        case .seq(let s): needsParens = s.parts.count > 1
        case .alt: needsParens = true
        case .lit(let l): needsParens = l.value.count > 1
        case .quant: needsParens = true
        default: needsParens = false
        }
        
        let target = needsParens ? "(?:\(childStr))" : childStr
        
        var quantStr = ""
        switch (node.min, node.max) {
        case (0, .inf): quantStr = "*"
        case (1, .inf): quantStr = "+"
        case (0, .count(1)): quantStr = "?"
        case (let n, .count(let m)) where n == m: quantStr = "{\(n)}"
        case (let n, .inf): quantStr = "{\(n),}"
        case (let n, .count(let m)): quantStr = "{\(n),\(m)}"
        }
        
        switch node.mode {
        case "Lazy": quantStr += "?"
        case "Possessive": quantStr += "+"
        default: break
        }
        
        return target + quantStr
    }
    
    private func emitGroup(_ node: Group) throws -> String {
        let bodyStr = try emit(node: node.body)
        
        if let atomic = node.atomic, atomic {
            return "(?>\(bodyStr))"
        }
        
        if node.capturing {
            if let name = node.name {
                return "(?<\(name)>\(bodyStr))"
            }
            return "(\(bodyStr))"
        } else {
            return "(?:\(bodyStr))"
        }
    }
    
    private func emitBackref(_ node: Backref) throws -> String {
        if let name = node.byName {
            return "\\k<\(name)>"
        } else if let index = node.byIndex {
            return "\\\(index)"
        }
        throw EmitterError.invalidBackref
    }
    
    private func emitLook(_ node: Look) throws -> String {
        let bodyStr = try emit(node: node.body)
        let prefix = node.dir == "Ahead" ? "" : "<"
        let sign = node.neg ? "!" : "="
        return "(?\(prefix)\(sign)\(bodyStr))"
    }
}

public enum EmitterError: Error {
    case unsupportedAnchor(String)
    case invalidBackref
}
