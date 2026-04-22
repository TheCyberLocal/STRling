import Foundation

/// PCRE2 Emitter
///
/// Compiles the STRling AST/IR into a PCRE2-compatible regular expression string.
public class PCRE2Emitter {

    /// Default upper bound on AST/IR nesting depth before the emitter
    /// aborts. Mirrors `DEFAULT_MAX_DEPTH` in the TypeScript SSOT and
    /// the matching constants in every other binding. Tests may
    /// override via `emit(node:maxDepth:)` / `emitWithDiagnostics`.
    public static let DEFAULT_MAX_DEPTH = 250

    private static let redosMessage =
        "The pattern contains overlapping alternations or nested unbounded "
      + "quantifiers (e.g., (a+)+). This can lead to catastrophic backtracking "
      + "and exponential CPU spikes. Consider using possessive quantifiers "
      + "(++ or *+) or atomic groups to guarantee execution safety."

    /// Mutable per-emit context threaded through `emit(node:context:)`
    /// so the depth, lookbehind, and warning-collection guards can
    /// fire without polluting the public API.
    private final class EmitContext {
        var depth: Int = 0
        let maxDepth: Int
        var inLookbehind: Bool = false
        var warnings: [STRlingWarning] = []

        init(maxDepth: Int) {
            self.maxDepth = maxDepth > 0 ? maxDepth : PCRE2Emitter.DEFAULT_MAX_DEPTH
        }
    }

    public init() {}

    /// Emit PCRE2 pattern from a Node (legacy entry point).
    ///
    /// Discards any non-fatal diagnostics. Use
    /// `emitWithDiagnostics(node:maxDepth:)` to collect warnings.
    public func emit(node: Node) throws -> String {
        return try emitWithDiagnostics(node: node, maxDepth: 0).pattern
    }

    /// Emit PCRE2 pattern from a Node and surface any non-fatal
    /// diagnostics collected during emission. Pass `maxDepth <= 0` to
    /// use `DEFAULT_MAX_DEPTH`.
    public func emitWithDiagnostics(node: Node, maxDepth: Int = 0) throws -> CompileResult {
        let ctx = EmitContext(maxDepth: maxDepth)
        let pattern = try emit(node: node, context: ctx)
        return CompileResult(pattern: pattern, warnings: ctx.warnings)
    }

    // MARK: - Guard predicates (mirror the TS SSOT)

    private func isUnboundedQuant(_ q: Quant) -> Bool {
        if case .inf = q.max { return true }
        return false
    }

    private func isVariableLengthQuant(_ q: Quant) -> Bool {
        switch q.max {
        case .inf:
            return true
        case .count(let n):
            return n != q.min
        }
    }

    /// Mirror of `_isFixedLengthBody` in the TS SSOT.
    private func isFixedLengthBody(_ node: Node) -> Bool {
        switch node {
        case .quant(let q):
            return !isVariableLengthQuant(q) && isFixedLengthBody(q.child)
        case .seq(let s):
            return s.parts.allSatisfy { isFixedLengthBody($0) }
        case .alt(let a):
            return a.branches.allSatisfy { isFixedLengthBody($0) }
        case .group(let g):
            return isFixedLengthBody(g.body)
        case .look:
            return true
        default:
            return true
        }
    }

    /// Mirror of `_hasNestedUnboundedQuant` in the TS SSOT.
    private func hasNestedUnboundedQuant(_ child: Node) -> Bool {
        switch child {
        case .quant(let q):
            return isUnboundedQuant(q)
        case .group(let g):
            return hasNestedUnboundedQuant(g.body)
        case .seq(let s):
            return s.parts.count == 1 && hasNestedUnboundedQuant(s.parts[0])
        case .alt(let a):
            return a.branches.contains(where: { hasNestedUnboundedQuant($0) })
        default:
            return false
        }
    }

    private func pushReDoSWarning(_ ctx: EmitContext) {
        if ctx.warnings.contains(where: { $0.code == "REDOS_RISK" }) { return }
        ctx.warnings.append(STRlingWarning(code: "REDOS_RISK",
                                           message: PCRE2Emitter.redosMessage))
    }

    // MARK: - Depth-tracking dispatch

    private func emit(node: Node, context ctx: EmitContext) throws -> String {
        ctx.depth += 1
        defer { ctx.depth -= 1 }
        if ctx.depth > ctx.maxDepth {
            throw STRlingCompilationError(
                message: "Maximum AST depth exceeded (limit: \(ctx.maxDepth)). "
                       + "This pattern is too deeply nested and risks host stack "
                       + "exhaustion during emission. Refactor the pattern to "
                       + "reduce nesting, or flatten capturing groups where possible.",
                code: "MAX_DEPTH")
        }
        switch node {
        case .alt(let n): return try emitAlt(n, ctx: ctx)
        case .seq(let n): return try emitSeq(n, ctx: ctx)
        case .lit(let n): return emitLit(n)
        case .dot(let n): return emitDot(n)
        case .anchor(let n): return try emitAnchor(n)
        case .charClass(let n): return try emitCharClass(n)
        case .quant(let n): return try emitQuant(n, ctx: ctx)
        case .group(let n): return try emitGroup(n, ctx: ctx)
        case .backref(let n): return try emitBackref(n)
        case .look(let n): return try emitLook(n, ctx: ctx)
        }
    }

    private func emitAlt(_ node: Alt, ctx: EmitContext) throws -> String {
        let branches = try node.branches.map { try emit(node: $0, context: ctx) }
        return branches.joined(separator: "|")
    }

    private func emitSeq(_ node: Seq, ctx: EmitContext) throws -> String {
        let parts = try node.parts.map { try emit(node: $0, context: ctx) }
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
        // --- Single-item shorthand optimization ---------------------------------
        // If the class is exactly one shorthand escape (like \d or \p{Lu}), 
        // prefer the shorthand (with negation flipping) instead of a bracketed class.
        if node.items.count == 1, let escape = node.items[0] as? ClassEscape {
            let k = escape.type
            
            // Handle d, w, s with negation flipping
            if ["d", "w", "s"].contains(k) {
                if node.negated {
                    return "\\" + k.uppercased()
                }
                return "\\" + k
            }
            
            // Handle already-negated shorthands D, W, S
            if ["D", "W", "S"].contains(k) {
                if node.negated {
                    return "\\" + k.lowercased()
                }
                return "\\" + k
            }
            
            // Handle \p{...} and \P{...}
            if ["p", "P"].contains(k), let prop = escape.property {
                let shouldNegate = node.negated != (k == "P")
                let use = shouldNegate ? "P" : "p"
                return "\\\(use){\(prop)}"
            }
        }
        
        // --- General case: build a bracket class --------------------------------
        var parts: [String] = []
        var hasHyphen = false
        
        for item in node.items {
            if let literal = item as? ClassLiteral {
                // Check if this is a hyphen literal - handle specially
                if literal.ch == "-" {
                    hasHyphen = true
                    // Don't add to parts yet - we'll add it at the beginning
                } else {
                    // Escape special characters in character class
                    if "[]\\^".contains(literal.ch) {
                        parts.append("\\" + literal.ch)
                    } else {
                        parts.append(literal.ch)
                    }
                }
            } else if let range = item as? ClassRange {
                // For ranges, we need to escape the endpoints if necessary
                let fromEscaped = "[]\\^".contains(range.fromCh) ? "\\" + range.fromCh : range.fromCh
                let toEscaped = "[]\\^".contains(range.toCh) ? "\\" + range.toCh : range.toCh
                parts.append("\(fromEscaped)-\(toEscaped)")
            } else if let escape = item as? ClassEscape {
                if let prop = escape.property {
                    parts.append("\\\(escape.type){\(prop)}")
                } else {
                    parts.append("\\\(escape.type)")
                }
            }
        }
        
        // Build the inner content with hyphen at the start if present
        let inner = hasHyphen ? "-" + parts.joined() : parts.joined()
        return "[\(node.negated ? "^" : "")\(inner)]"
    }
    
    private func emitQuant(_ node: Quant, ctx: EmitContext) throws -> String {
        // ReDoS guard: only flag when the *outer* quantifier is itself
        // unbounded (e.g. `(a+)+`). A bounded outer like `(a+){0,3}`
        // cannot produce exponential backtracking on its own.
        if isUnboundedQuant(node) && hasNestedUnboundedQuant(node.child) {
            pushReDoSWarning(ctx)
        }
        let childStr = try emit(node: node.child, context: ctx)
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
    
    private func emitGroup(_ node: Group, ctx: EmitContext) throws -> String {
        let bodyStr = try emit(node: node.body, context: ctx)
        
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
    
    private func emitLook(_ node: Look, ctx: EmitContext) throws -> String {
        // Variable-length lookbehind guard: PCRE2 mandates a fixed-width
        // lookbehind body. Detect the violation here so the user sees a
        // Signpost-pattern error rather than an opaque PCRE2 compile
        // failure leaking from the runtime.
        if node.dir == "Behind" && !isFixedLengthBody(node.body) {
            throw STRlingCompilationError(
                message: "PCRE2 does not support variable-length lookbehinds. "
                       + "The lookbehind body contains a quantifier that makes "
                       + "its length unpredictable. Rewrite the assertion using "
                       + "a fixed-length range (e.g. `{1,8}` instead of `+`), "
                       + "or restructure the pattern using a Lookahead, or "
                       + "extract the quantified portion outside the assertion.",
                code: "VLB_NOT_SUPPORTED")
        }
        let wasInLb = ctx.inLookbehind
        if node.dir == "Behind" { ctx.inLookbehind = true }
        defer { ctx.inLookbehind = wasInLb }
        let bodyStr = try emit(node: node.body, context: ctx)
        let prefix = node.dir == "Ahead" ? "" : "<"
        let sign = node.neg ? "!" : "="
        return "(?\(prefix)\(sign)\(bodyStr))"
    }
}

public enum EmitterError: Error {
    case unsupportedAnchor(String)
    case invalidBackref
}
