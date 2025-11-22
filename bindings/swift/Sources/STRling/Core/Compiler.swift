import Foundation

/// Compiler
///
/// Compiles the STRling AST (Node) into the Intermediate Representation (IR).
/// This step performs lowering and normalization of the AST.
public class Compiler {

    public init() {}

    /// Compile AST Node to IR
    ///
    /// - Parameter node: The root node of the AST
    /// - Returns: The compiled IR operation
    public func compile(node: Node) throws -> IROp {
        switch node {
        case .alt(let n): return .alt(try compileAlt(n))
        case .seq(let n): return .seq(try compileSeq(n))
        case .lit(let n): return .lit(compileLit(n))
        case .dot(let n): return .dot(compileDot(n))
        case .anchor(let n): return .anchor(try compileAnchor(n))
        case .charClass(let n): return .charClass(try compileCharClass(n))
        case .quant(let n): return .quant(try compileQuant(n))
        case .group(let n): return .group(try compileGroup(n))
        case .backref(let n): return .backref(try compileBackref(n))
        case .look(let n): return .look(try compileLook(n))
        }
    }

    private func compileAlt(_ node: Alt) throws -> IRAlt {
        let branches = try node.branches.map { try compile(node: $0) }
        return IRAlt(branches: branches)
    }

    private func compileSeq(_ node: Seq) throws -> IRSeq {
        let parts = try node.parts.map { try compile(node: $0) }
        return IRSeq(parts: parts)
    }

    private func compileLit(_ node: Lit) -> IRLit {
        return IRLit(value: node.value)
    }

    private func compileDot(_ node: Dot) -> IRDot {
        return IRDot()
    }

    private func compileAnchor(_ node: Anchor) throws -> IRAnchor {
        return IRAnchor(at: node.at)
    }

    private func compileCharClass(_ node: CharClass) throws -> IRCharClass {
        let items = node.items.map { item -> IRClassItem in
            if let range = item as? ClassRange {
                return IRClassRange(fromCh: range.fromCh, toCh: range.toCh)
            } else if let literal = item as? ClassLiteral {
                return IRClassLiteral(ch: literal.ch)
            } else if let escape = item as? ClassEscape {
                return IRClassEscape(type: escape.type, property: escape.property)
            } else {
                // Should not happen if AST is well-formed
                fatalError("Unknown ClassItem type")
            }
        }
        return IRCharClass(negated: node.negated, items: items)
    }

    private func compileQuant(_ node: Quant) throws -> IRQuant {
        let child = try compile(node: node.child)
        let max: IRQuantMax
        switch node.max {
        case .count(let n): max = .count(n)
        case .inf: max = .inf
        }
        return IRQuant(child: child, min: node.min, max: max, mode: node.mode)
    }

    private func compileGroup(_ node: Group) throws -> IRGroup {
        let body = try compile(node: node.body)
        return IRGroup(capturing: node.capturing, body: body, name: node.name, atomic: node.atomic)
    }

    private func compileBackref(_ node: Backref) throws -> IRBackref {
        return IRBackref(byIndex: node.byIndex, byName: node.byName)
    }

    private func compileLook(_ node: Look) throws -> IRLook {
        let body = try compile(node: node.body)
        return IRLook(dir: node.dir, neg: node.neg, body: body)
    }
}
