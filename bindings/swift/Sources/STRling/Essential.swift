// STRling Essential — compatibility lexical-shape patterns for common string
// formats. They do not establish semantic validity or standards conformance.
//
// Each helper composes existing AST primitives so the compiled output
// flows through the standard pipeline and no raw regex leaks into the
// public API.

import Foundation

private func letterItems() -> [ClassItem] {
    return [
        ClassRange(fromCh: "A", toCh: "Z"),
        ClassRange(fromCh: "a", toCh: "z"),
    ]
}

private func digitItems() -> [ClassItem] {
    return [ClassEscape(type: "d")]
}

private func hexItems() -> [ClassItem] {
    return [
        ClassRange(fromCh: "A", toCh: "F"),
        ClassRange(fromCh: "a", toCh: "f"),
        ClassRange(fromCh: "0", toCh: "9"),
    ]
}

private func charsItems(_ s: String) -> [ClassItem] {
    return s.map { ClassLiteral(ch: String($0)) }
}

private func classOf(_ items: [ClassItem], min: Int, max: QuantMax) -> Node {
    let cc = Node.charClass(CharClass(negated: false, items: items))
    return .quant(Quant(child: cc, min: min, max: max, mode: "Greedy"))
}

private func digN(_ min: Int, _ max: QuantMax) -> Node { classOf(digitItems(),  min: min, max: max) }
private func hexN(_ min: Int, _ max: QuantMax) -> Node { classOf(hexItems(),    min: min, max: max) }
private func lettN(_ min: Int, _ max: QuantMax) -> Node { classOf(letterItems(), min: min, max: max) }

private func lit(_ s: String) -> Node { .lit(Lit(value: s)) }

private func opt(_ node: Node) -> Node {
    let grouped = Node.group(Group(capturing: false, body: node))
    return .quant(Quant(child: grouped, min: 0, max: .count(1), mode: "Greedy"))
}

private func seq(_ parts: [Node]) -> Node { .seq(Seq(parts: parts)) }
private func alt(_ branches: [Node]) -> Node { .alt(Alt(branches: branches)) }

/// Public Essential 5 facade.
public enum Essential {
    /// Email-like lexical shape; RFC 5322 conformance is not claimed.
    public static func email() -> Node {
        let local  = classOf(letterItems() + digitItems() + charsItems("._%+-"), min: 1, max: .inf)
        let domain = classOf(letterItems() + digitItems() + charsItems(".-"),    min: 1, max: .inf)
        let tld    = lettN(2, .inf)
        return seq([local, lit("@"), domain, lit("."), tld])
    }

    /// HTTP(S) URL-like lexical shape; RFC 3986 conformance is not claimed.
    public static func url() -> Node {
        let base     = letterItems() + digitItems() + charsItems("/_-.~%&=:@!$'()*+,;")
        let withQ    = base + charsItems("?")
        let withFrag = withQ + charsItems("#")

        let scheme   = seq([lit("http"), opt(lit("s"))])
        let host     = classOf(letterItems() + digitItems() + charsItems(".-"), min: 1, max: .inf)
        let port     = opt(seq([lit(":"), digN(1, .inf)]))
        let path     = opt(seq([lit("/"), classOf(base,     min: 0, max: .inf)]))
        let query    = opt(seq([lit("?"), classOf(withQ,    min: 0, max: .inf)]))
        let fragment = opt(seq([lit("#"), classOf(withFrag, min: 0, max: .inf)]))
        return seq([scheme, lit("://"), host, port, path, query, fragment])
    }

    /// RFC 9562 UUID text shape; version 4 constrains version/variant nibbles.
    public static func uuid(version: Int = 0) -> Node {
        if version == 4 {
            let variant = classOf(charsItems("89ABab"), min: 1, max: .count(1))
            return seq([
                hexN(8, .count(8)), lit("-"),
                hexN(4, .count(4)), lit("-"),
                lit("4"), hexN(3, .count(3)), lit("-"),
                variant, hexN(3, .count(3)), lit("-"),
                hexN(12, .count(12)),
            ])
        }
        return seq([
            hexN(8, .count(8)), lit("-"),
            hexN(4, .count(4)), lit("-"),
            hexN(4, .count(4)), lit("-"),
            hexN(4, .count(4)), lit("-"),
            hexN(12, .count(12)),
        ])
    }

    private static func ipv4() -> Node {
        return seq([
            digN(1, .count(3)), lit("."),
            digN(1, .count(3)), lit("."),
            digN(1, .count(3)), lit("."),
            digN(1, .count(3)),
        ])
    }

    private static func ipv6() -> Node {
        return seq([
            hexN(1, .count(4)), lit(":"),
            hexN(1, .count(4)), lit(":"),
            hexN(1, .count(4)), lit(":"),
            hexN(1, .count(4)), lit(":"),
            hexN(1, .count(4)), lit(":"),
            hexN(1, .count(4)), lit(":"),
            hexN(1, .count(4)), lit(":"),
            hexN(1, .count(4)),
        ])
    }

    /// IP-like lexical shape. Version 4 selects four digit groups and version 6
    /// selects eight hex groups; complete address validity is not claimed.
    public static func ip(version: Int = 0) -> Node {
        if version == 4 { return ipv4() }
        if version == 6 { return ipv6() }
        return alt([ipv4(), ipv6()])
    }

    /// Timestamp-like lexical shape; RFC 3339 / ISO 8601 validity is not claimed.
    public static func dateTime() -> Node {
        let sign   = classOf(charsItems("+-"), min: 1, max: .count(1))
        let frac   = seq([lit("."), digN(1, .inf)])
        let offset = seq([sign, digN(2, .count(2)), lit(":"), digN(2, .count(2))])
        return seq([
            digN(4, .count(4)), lit("-"), digN(2, .count(2)), lit("-"), digN(2, .count(2)),
            lit("T"),
            digN(2, .count(2)), lit(":"), digN(2, .count(2)), lit(":"), digN(2, .count(2)),
            opt(frac),
            opt(alt([lit("Z"), offset])),
        ])
    }

    /// Compile a Node to a PCRE2 regex string.
    public static func compile(_ node: Node) throws -> String {
        return try PCRE2Emitter().emit(node: node)
    }
}
