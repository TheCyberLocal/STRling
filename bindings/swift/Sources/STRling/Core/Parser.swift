/// STRling Parser - Recursive Descent Parser for Swift
///
/// Transforms STRling DSL patterns into AST nodes.
/// Mirrors the TypeScript reference implementation.

import Foundation

// MARK: - Control Escapes

private let controlEscapes: [Character: String] = [
    "n": "\n",
    "r": "\r",
    "t": "\t",
    "f": "\u{000C}",
    "v": "\u{000B}"
]

// MARK: - Known Escapes (non-error producing when used outside char class)

private let knownEscapeChars: Set<Character> = [
    "d", "D", "w", "W", "s", "S",
    "b", "B", "A", "Z",
    "n", "r", "t", "f", "v",
    "k", "p", "P",
    "x", "u", "U",
    "0"
]

// MARK: - Cursor

/// Cursor for tracking position in input text
private class Cursor {
    let text: String
    var i: String.Index
    var extendedMode: Bool
    var inClass: Int = 0
    
    init(_ text: String, extendedMode: Bool = false) {
        self.text = text
        self.i = text.startIndex
        self.extendedMode = extendedMode
    }
    
    var eof: Bool {
        i >= text.endIndex
    }
    
    var position: Int {
        text.distance(from: text.startIndex, to: i)
    }
    
    func peek(_ offset: Int = 0) -> Character? {
        if offset == 0 {
            guard !eof else { return nil }
            return text[i]
        }
        guard let idx = text.index(i, offsetBy: offset, limitedBy: text.endIndex) else {
            return nil
        }
        if idx >= text.endIndex {
            return nil
        }
        return text[idx]
    }
    
    func peekString(_ offset: Int = 0) -> String {
        guard let ch = peek(offset) else { return "" }
        return String(ch)
    }
    
    func take() -> Character? {
        guard !eof else { return nil }
        let ch = text[i]
        i = text.index(after: i)
        return ch
    }
    
    func takeString() -> String {
        guard let ch = take() else { return "" }
        return String(ch)
    }
    
    func match(_ s: String) -> Bool {
        guard let endIdx = text.index(i, offsetBy: s.count, limitedBy: text.endIndex) else {
            return false
        }
        if text[i..<endIdx] == s {
            i = endIdx
            return true
        }
        return false
    }
    
    func skipWsAndComments() {
        guard extendedMode && inClass == 0 else { return }
        while !eof {
            guard let ch = peek() else { break }
            if " \t\r\n".contains(ch) {
                _ = take()
                continue
            }
            if ch == "#" {
                while !eof {
                    guard let c = peek() else { break }
                    if "\r\n".contains(c) { break }
                    _ = take()
                }
                continue
            }
            break
        }
    }
}

// MARK: - Parser

/// STRling DSL Parser
public class Parser {
    private var flags: Flags
    private var src: String
    private var cur: Cursor
    private var capCount: Int = 0
    private var capNames: Set<String> = []
    
    /// Initialize parser with source text
    ///
    /// - Parameter text: The STRling DSL source text
    public init(_ text: String) {
        let (parsedFlags, pattern) = Parser.parseDirectives(text)
        self.flags = parsedFlags
        self.src = pattern
        self.cur = Cursor(pattern, extendedMode: parsedFlags.extended)
    }
    
    /// Raise a STRlingParseError with an instructional hint.
    private func raiseError(_ message: String, _ pos: Int) throws -> Never {
        throw STRlingParseError(message: message, pos: pos, text: src)
    }
    
    // MARK: - Directive Parsing
    
    private static func parseDirectives(_ text: String) -> (Flags, String) {
        var flags = Flags()
        let lines = text.components(separatedBy: "\n")
        var patternLines: [String] = []
        var inPattern = false
        
        for line in lines {
            let trimmed = line.trimmingCharacters(in: .whitespaces)
            
            if !inPattern {
                // Skip blank lines and comments before pattern
                if trimmed.isEmpty || trimmed.hasPrefix("#") {
                    continue
                }
                
                // Check for % directives
                if trimmed.hasPrefix("%") {
                    // Must be exactly %flags
                    if trimmed.hasPrefix("%flags") {
                        let afterFlags = String(trimmed.dropFirst(6)).trimmingCharacters(in: .whitespaces)
                        let cleaned = afterFlags.lowercased().filter { !",[]\t\n\r ".contains($0) }
                        // Validate flag characters
                        for ch in cleaned {
                            if !"imsux".contains(ch) {
                                return (Flags(invalidFlag: true, invalidFlagChar: String(ch)), text)
                            }
                        }
                        flags = Flags.fromLetters(cleaned)
                        continue
                    } else {
                        // Malformed directive (e.g., %flagg)
                        // We need to signal this error. Return the text as-is with a marker.
                        return (Flags(malformedDirective: true), text)
                    }
                }
                
                // First non-directive, non-blank, non-comment line - start of pattern
                inPattern = true
                
                // Check if this line contains %flags (directive after pattern content on same line)
                if let percentIdx = trimmed.range(of: "%flags") {
                    // Only if there's content before %flags
                    let before = trimmed[trimmed.startIndex..<percentIdx.lowerBound]
                    if !before.trimmingCharacters(in: .whitespaces).isEmpty {
                        return (Flags(directiveAfterPattern: true), text)
                    }
                }
                
                patternLines.append(line)
            } else {
                // Already in pattern mode
                if trimmed.hasPrefix("%flags") || (trimmed.hasPrefix("%") && !trimmed.isEmpty) {
                    // Directive after pattern content
                    return (Flags(directiveAfterPattern: true), text)
                }
                patternLines.append(line)
            }
        }
        
        // Edge case: single line with no newline that contains %flags after content
        // e.g., "abc%flags i"
        if !inPattern && lines.count == 1 {
            let trimmed = lines[0].trimmingCharacters(in: .whitespaces)
            if !trimmed.hasPrefix("%") && trimmed.contains("%flags") {
                return (Flags(directiveAfterPattern: true), text)
            }
        }
        
        return (flags, patternLines.joined(separator: "\n"))
    }
    
    /// Parse the source text
    public func parse() throws -> (Flags, Node) {
        // Check for directive errors
        if flags.malformedDirective {
            throw STRlingParseError(message: "Malformed directive", pos: 0, text: src)
        }
        if flags.directiveAfterPattern {
            throw STRlingParseError(message: "Directive after pattern", pos: 0, text: src)
        }
        if flags.invalidFlag {
            let ch = flags.invalidFlagChar ?? "?"
            throw STRlingParseError(message: "Invalid flag '\(ch)'", pos: 0, text: src)
        }
        
        // Check for inline modifiers like (?i)
        checkInlineModifiers(src)
        
        let node = try parseAlt()
        cur.skipWsAndComments()
        
        if !cur.eof {
            if cur.peekString() == ")" {
                try raiseError("Unmatched ')'", cur.position)
            }
            try raiseError("Unexpected trailing input", cur.position)
        }
        
        return (flags, node)
    }
    
    /// Check for inline modifiers and issue a warning (not an error)
    private func checkInlineModifiers(_ text: String) {
        // Detect (?i), (?m), (?s), (?x), (?u) and combinations
        // This is informational; actual parsing continues
        let modifierPattern = try? NSRegularExpression(pattern: #"\(\?[imsuUx]+(?:-[imsuUx]+)?\)"#)
        if let match = modifierPattern?.firstMatch(in: text, range: NSRange(text.startIndex..., in: text)) {
            let _ = match // Inline modifiers detected but handled via directives
        }
    }
    
    // MARK: - Alt/Seq/Atom
    
    private func parseAlt() throws -> Node {
        cur.skipWsAndComments()
        
        if cur.peekString() == "|" {
            try raiseError("Alternation lacks left-hand side", cur.position)
        }
        
        var branches: [Node] = [try parseSeq()]
        cur.skipWsAndComments()
        
        while cur.peekString() == "|" {
            let pipePos = cur.position
            _ = cur.take()
            cur.skipWsAndComments()
            
            if cur.eof || cur.peekString() == ")" {
                try raiseError("Alternation lacks right-hand side", pipePos)
            }
            
            if cur.peekString() == "|" {
                try raiseError("Empty alternation", pipePos)
            }
            
            branches.append(try parseSeq())
            cur.skipWsAndComments()
        }
        
        if branches.count == 1 { return branches[0] }
        return .alt(Alt(branches: branches))
    }
    
    private func parseSeq() throws -> Node {
        var parts: [Node] = []
        
        while true {
            cur.skipWsAndComments()
            let ch = cur.peekString()
            
            if "*+?{".contains(ch) && parts.isEmpty {
                if ch == "{" {
                    try raiseError("Invalid quantifier '{'", cur.position)
                }
                try raiseError("Invalid quantifier '\(ch)'", cur.position)
            }
            
            if ch.isEmpty || "|)".contains(ch) { break }
            
            var atom = try parseAtom()
            atom = try parseQuantIfAny(child: atom)
            parts.append(atom)
        }
        
        if parts.count == 1 { return parts[0] }
        return .seq(Seq(parts: parts))
    }
    
    private func parseAtom() throws -> Node {
        cur.skipWsAndComments()
        let ch = cur.peekString()
        
        if ch == "." {
            _ = cur.take()
            return .dot(Dot())
        }
        if ch == "^" {
            _ = cur.take()
            return .anchor(Anchor(at: "Start"))
        }
        if ch == "$" {
            _ = cur.take()
            return .anchor(Anchor(at: "End"))
        }
        if ch == "(" {
            return try parseGroupOrLook()
        }
        if ch == "[" {
            return try parseCharClass()
        }
        if ch == "\\" {
            return try parseEscapeAtom()
        }
        if ch == ")" {
            try raiseError("Unmatched ')'", cur.position)
        }
        
        return .lit(Lit(value: cur.takeString()))
    }
    
    // MARK: - Quantifiers
    
    private func parseQuantIfAny(child: Node) throws -> Node {
        let ch = cur.peekString()
        var min: Int?
        var max: QuantMax?
        var mode = "Greedy"
        
        if ch == "*" {
            min = 0
            max = .inf
            _ = cur.take()
        } else if ch == "+" {
            min = 1
            max = .inf
            _ = cur.take()
        } else if ch == "?" {
            min = 0
            max = .count(1)
            _ = cur.take()
        } else if ch == "{" {
            let saveI = cur.i
            _ = cur.take()
            
            // Check for invalid brace quantifier content
            let contentStart = cur.i
            var braceContent = ""
            while !cur.eof && cur.peekString() != "}" {
                braceContent += cur.takeString()
            }
            
            if cur.peekString() == "}" {
                // Check if content is valid (digits, optional comma, optional digits)
                let trimContent = braceContent.trimmingCharacters(in: .whitespaces)
                let validBrace = isValidBraceContent(trimContent)
                
                if !validBrace {
                    try raiseError("Brace quantifier: Invalid brace quantifier content", cur.position)
                }
                
                // Reset and re-parse properly
                cur.i = contentStart
            } else {
                // No closing brace - if we consumed digits, it's an incomplete quantifier
                if braceContent.first?.isNumber == true {
                    try raiseError("Incomplete quantifier", cur.position)
                }
                // No closing brace, not numeric - treat { as literal
                cur.i = saveI
                return child
            }
            
            // Now parse the numbers properly
            cur.i = contentStart
            guard let m = readIntOptional() else {
                cur.i = saveI
                return child
            }
            
            min = m
            max = .count(m)
            
            if cur.peekString() == "," {
                _ = cur.take()
                if let n = readIntOptional() {
                    if n < m {
                        try raiseError("Invalid quantifier range", cur.position)
                    }
                    max = .count(n)
                } else {
                    max = .inf
                }
            }
            
            if cur.peekString() != "}" {
                try raiseError("Incomplete quantifier", cur.position)
            }
            _ = cur.take()
        } else {
            return child
        }
        
        // Check if child is an anchor
        if case .anchor = child {
            try raiseError("Cannot quantify anchor", cur.position)
        }
        
        let nxt = cur.peekString()
        if nxt == "?" {
            mode = "Lazy"
            _ = cur.take()
        } else if nxt == "+" {
            mode = "Possessive"
            _ = cur.take()
        }
        
        return .quant(Quant(child: child, min: min!, max: max!, mode: mode))
    }
    
    private func isValidBraceContent(_ content: String) -> Bool {
        if content.isEmpty { return false }
        let parts = content.split(separator: ",", maxSplits: 1, omittingEmptySubsequences: false)
        if parts.count == 1 {
            return parts[0].allSatisfy { $0.isNumber }
        }
        if parts.count == 2 {
            let left = parts[0].trimmingCharacters(in: .whitespaces)
            let right = parts[1].trimmingCharacters(in: .whitespaces)
            if !left.allSatisfy({ $0.isNumber }) { return false }
            if left.isEmpty { return false }
            if right.isEmpty { return true } // {n,} is valid
            return right.allSatisfy { $0.isNumber }
        }
        return false
    }
    
    private func readIntOptional() -> Int? {
        var s = ""
        while let ch = cur.peek(), ch.isNumber {
            s += cur.takeString()
        }
        return s.isEmpty ? nil : Int(s)
    }
    
    // MARK: - Groups and Lookarounds
    
    private func parseGroupOrLook() throws -> Node {
        _ = cur.take() // consume '('
        
        if cur.match("?:") {
            let body = try parseAlt()
            if !cur.match(")") {
                try raiseError("Unterminated group", cur.position)
            }
            return .group(Group(capturing: false, body: body))
        }
        
        if cur.match("?<=") {
            let body = try parseAlt()
            if !cur.match(")") {
                try raiseError("Unterminated lookbehind", cur.position)
            }
            return .look(Look(dir: "Behind", neg: false, body: body))
        }
        
        if cur.match("?<!") {
            let body = try parseAlt()
            if !cur.match(")") {
                try raiseError("Unterminated lookbehind", cur.position)
            }
            return .look(Look(dir: "Behind", neg: true, body: body))
        }
        
        if cur.match("?<") {
            var name = ""
            while cur.peekString() != ">" && !cur.eof {
                name += cur.takeString()
            }
            if !cur.match(">") {
                try raiseError("Unterminated group name", cur.position)
            }
            
            // Validate group name
            try validateGroupName(name, cur.position)
            
            if capNames.contains(name) {
                try raiseError("Duplicate group name <\(name)>", cur.position)
            }
            capCount += 1
            capNames.insert(name)
            
            let body = try parseAlt()
            if !cur.match(")") {
                try raiseError("Unterminated group", cur.position)
            }
            return .group(Group(capturing: true, body: body, name: name))
        }
        
        if cur.match("?>") {
            let body = try parseAlt()
            if !cur.match(")") {
                try raiseError("Unterminated atomic group", cur.position)
            }
            return .group(Group(capturing: false, body: body, atomic: true))
        }
        
        if cur.match("?=") {
            let body = try parseAlt()
            if !cur.match(")") {
                try raiseError("Unterminated lookahead", cur.position)
            }
            return .look(Look(dir: "Ahead", neg: false, body: body))
        }
        
        if cur.match("?!") {
            let body = try parseAlt()
            if !cur.match(")") {
                try raiseError("Unterminated lookahead", cur.position)
            }
            return .look(Look(dir: "Ahead", neg: true, body: body))
        }
        
        capCount += 1
        let body = try parseAlt()
        if !cur.match(")") {
            try raiseError("Unterminated group", cur.position)
        }
        return .group(Group(capturing: true, body: body))
    }
    
    private func validateGroupName(_ name: String, _ pos: Int) throws {
        if name.isEmpty {
            try raiseError("Invalid group name", pos)
        }
        let first = name.first!
        if first.isNumber {
            try raiseError("Invalid group name", pos)
        }
        // Group name must match [a-zA-Z_][a-zA-Z0-9_]*
        let validPattern = try! NSRegularExpression(pattern: "^[a-zA-Z_][a-zA-Z0-9_]*$")
        let range = NSRange(name.startIndex..., in: name)
        if validPattern.firstMatch(in: name, range: range) == nil {
            try raiseError("Invalid group name", pos)
        }
    }
    
    // MARK: - Character Classes
    
    private func parseCharClass() throws -> Node {
        let startPos = cur.position
        _ = cur.take() // consume '['
        cur.inClass += 1
        
        var neg = false
        if cur.peekString() == "^" {
            neg = true
            _ = cur.take()
        }
        
        // Check for empty character class: [] or [^]
        if cur.peekString() == "]" {
            cur.inClass -= 1
            try raiseError("Unterminated character class", startPos)
        }
        
        var items: [ClassItem] = []
        
        while !cur.eof && cur.peekString() != "]" {
            if cur.peekString() == "\\" {
                let escItem = try parseClassEscape()
                
                // Check if this is followed by a range
                if cur.peekString() == "-" && cur.peek(1).map({ String($0) }) != "]" && cur.peek(1) != nil {
                    // Only allow range if the escape is a simple literal
                    if let lit = escItem as? ClassLiteral {
                        _ = cur.take() // consume '-'
                        let endCh: String
                        if cur.peekString() == "\\" {
                            let endItem = try parseClassEscape()
                            if let endLit = endItem as? ClassLiteral {
                                endCh = endLit.ch
                            } else {
                                items.append(lit)
                                items.append(ClassLiteral(ch: "-"))
                                items.append(endItem)
                                continue
                            }
                        } else {
                            endCh = cur.takeString()
                        }
                        // Validate range
                        if let fromScalar = lit.ch.unicodeScalars.first,
                           let toScalar = endCh.unicodeScalars.first,
                           fromScalar.value > toScalar.value {
                            try raiseError("Invalid character range", cur.position)
                        }
                        items.append(ClassRange(fromCh: lit.ch, toCh: endCh))
                    } else {
                        items.append(escItem)
                    }
                } else {
                    items.append(escItem)
                }
            } else {
                let ch = cur.takeString()
                
                if cur.peekString() == "-" && cur.peek(1).map({ String($0) }) != "]" && cur.peek(1) != nil {
                    _ = cur.take() // consume '-'
                    let endCh: String
                    if cur.peekString() == "\\" {
                        let endItem = try parseClassEscape()
                        if let endLit = endItem as? ClassLiteral {
                            endCh = endLit.ch
                        } else {
                            items.append(ClassLiteral(ch: ch))
                            items.append(ClassLiteral(ch: "-"))
                            items.append(endItem)
                            continue
                        }
                    } else {
                        endCh = cur.takeString()
                    }
                    // Validate range
                    if let fromScalar = ch.unicodeScalars.first,
                       let toScalar = endCh.unicodeScalars.first,
                       fromScalar.value > toScalar.value {
                        try raiseError("Invalid character range", cur.position)
                    }
                    items.append(ClassRange(fromCh: ch, toCh: endCh))
                } else {
                    items.append(ClassLiteral(ch: ch))
                }
            }
        }
        
        if cur.eof {
            cur.inClass -= 1
            try raiseError("Unterminated character class", startPos)
        }
        
        _ = cur.take() // consume ']'
        cur.inClass -= 1
        
        return .charClass(CharClass(negated: neg, items: items))
    }
    
    private func parseClassEscape() throws -> ClassItem {
        let startPos = cur.position
        _ = cur.take() // consume '\'
        
        guard let nxt = cur.peek() else {
            try raiseError("Unexpected end of escape", startPos)
        }
        
        if "dDwWsS".contains(nxt) {
            let ch = cur.takeString()
            return ClassEscape(type: ch)
        }
        
        if nxt == "p" || nxt == "P" {
            let tp = cur.takeString()
            if !cur.match("{") {
                try raiseError("Expected '{' after \\p/\\P", startPos)
            }
            var prop = ""
            while cur.peekString() != "}" && !cur.eof {
                prop += cur.takeString()
            }
            if !cur.match("}") {
                try raiseError("Unterminated \\p{...}", startPos)
            }
            return ClassEscape(type: tp, property: prop)
        }
        
        if let escaped = controlEscapes[nxt] {
            _ = cur.take()
            return ClassLiteral(ch: escaped)
        }
        
        if nxt == "b" {
            _ = cur.take()
            return ClassLiteral(ch: "\u{0008}")  // Backspace
        }
        
        // Forbidden: \0 (octal)
        if nxt == "0" {
            try raiseError("Forbidden octal escape", startPos)
        }
        
        // \x hex escape
        if nxt == "x" {
            _ = cur.take()
            let val = try parseHexEscapeValue(startPos)
            return ClassLiteral(ch: val)
        }
        
        // \u / \U unicode escape
        if nxt == "u" || nxt == "U" {
            let val = try parseUnicodeEscapeValue(startPos)
            return ClassLiteral(ch: val)
        }
        
        // Unknown escape for alphanumeric
        if nxt.isLetter || nxt.isNumber {
            try raiseError("Unknown escape sequence \\\(nxt)", startPos)
        }
        
        return ClassLiteral(ch: cur.takeString())
    }
    
    // MARK: - Escape Atoms
    
    private func parseEscapeAtom() throws -> Node {
        let startPos = cur.position
        _ = cur.take() // consume '\'
        
        guard let nxt = cur.peek() else {
            try raiseError("Unexpected end of escape", startPos)
        }
        
        // Backreference
        if nxt.isNumber && nxt != "0" {
            var num = 0
            while let ch = cur.peek(), ch.isNumber {
                num = num * 10 + Int(String(cur.take()!))!
                if num > capCount {
                    try raiseError("Backreference to undefined group \\\(num)", startPos)
                }
            }
            return .backref(Backref(byIndex: num))
        }
        
        if nxt == "b" {
            _ = cur.take()
            return .anchor(Anchor(at: "WordBoundary"))
        }
        if nxt == "B" {
            _ = cur.take()
            return .anchor(Anchor(at: "NotWordBoundary"))
        }
        if nxt == "A" {
            _ = cur.take()
            return .anchor(Anchor(at: "AbsoluteStart"))
        }
        if nxt == "Z" {
            _ = cur.take()
            return .anchor(Anchor(at: "EndBeforeFinalNewline"))
        }
        
        if nxt == "k" {
            _ = cur.take()
            if !cur.match("<") {
                try raiseError("Expected '<' after \\k", startPos)
            }
            var name = ""
            while cur.peekString() != ">" && !cur.eof {
                name += cur.takeString()
            }
            if !cur.match(">") {
                try raiseError("Unterminated named backref", startPos)
            }
            if !capNames.contains(name) {
                try raiseError("Backreference to undefined group <\(name)>", startPos)
            }
            return .backref(Backref(byName: name))
        }
        
        if "dDwWsS".contains(nxt) {
            let ch = cur.takeString()
            return .charClass(CharClass(negated: false, items: [ClassEscape(type: ch)]))
        }
        
        if nxt == "p" || nxt == "P" {
            let tp = cur.takeString()
            if !cur.match("{") {
                try raiseError("Expected '{' after \\p/\\P", startPos)
            }
            var prop = ""
            while cur.peekString() != "}" && !cur.eof {
                prop += cur.takeString()
            }
            if !cur.match("}") {
                try raiseError("Unterminated \\p{...}", startPos)
            }
            return .charClass(CharClass(negated: false, items: [ClassEscape(type: tp, property: prop)]))
        }
        
        if let escaped = controlEscapes[nxt] {
            _ = cur.take()
            return .lit(Lit(value: escaped))
        }
        
        if nxt == "x" {
            _ = cur.take()
            return .lit(Lit(value: try parseHexEscapeValue(startPos)))
        }
        
        if nxt == "u" || nxt == "U" {
            return .lit(Lit(value: try parseUnicodeEscapeValue(startPos)))
        }
        
        // Forbidden: \0 (octal)
        if nxt == "0" {
            try raiseError("Forbidden octal escape", startPos)
        }
        
        // Unknown escape: alphanumeric characters that aren't known
        if nxt.isLetter || nxt.isNumber {
            if !knownEscapeChars.contains(nxt) {
                try raiseError("Unknown escape sequence \\\(nxt)", startPos)
            }
        }
        
        return .lit(Lit(value: cur.takeString()))
    }
    
    // MARK: - Hex/Unicode Escapes
    
    private func parseHexEscapeValue(_ startPos: Int) throws -> String {
        if cur.match("{") {
            var hex = ""
            while let ch = cur.peek(), ch.isHexDigit {
                hex += cur.takeString()
            }
            if !cur.match("}") {
                try raiseError("Unterminated \\x{...}", startPos)
            }
            let code = Int(hex.isEmpty ? "0" : hex, radix: 16) ?? 0
            guard let scalar = UnicodeScalar(code) else {
                try raiseError("Invalid hex escape value", startPos)
            }
            return String(scalar)
        }
        
        let h1 = cur.takeString()
        let h2 = cur.takeString()
        guard h1.first?.isHexDigit == true && h2.first?.isHexDigit == true else {
            try raiseError("Invalid \\xHH escape", startPos)
        }
        let code = Int(h1 + h2, radix: 16) ?? 0
        guard let scalar = UnicodeScalar(code) else {
            try raiseError("Invalid hex escape value", startPos)
        }
        return String(scalar)
    }
    
    private func parseUnicodeEscapeValue(_ startPos: Int) throws -> String {
        let tp = cur.takeString()
        
        if tp == "u" && cur.match("{") {
            var hex = ""
            while let ch = cur.peek(), ch.isHexDigit {
                hex += cur.takeString()
            }
            if !cur.match("}") {
                try raiseError("Unterminated \\u{...}", startPos)
            }
            let code = Int(hex.isEmpty ? "0" : hex, radix: 16) ?? 0
            guard let scalar = UnicodeScalar(code) else {
                try raiseError("Invalid unicode escape value", startPos)
            }
            return String(scalar)
        }
        
        if tp == "u" {
            var hex = ""
            for _ in 0..<4 {
                hex += cur.takeString()
            }
            guard hex.count == 4, let code = Int(hex, radix: 16), let scalar = UnicodeScalar(code) else {
                try raiseError("Invalid \\uHHHH escape", startPos)
            }
            return String(scalar)
        }
        
        if tp == "U" {
            var hex = ""
            for _ in 0..<8 {
                hex += cur.takeString()
            }
            guard hex.count == 8, let code = Int(hex, radix: 16), let scalar = UnicodeScalar(code) else {
                try raiseError("Invalid \\UHHHHHHHH escape", startPos)
            }
            return String(scalar)
        }
        
        try raiseError("Invalid unicode escape", startPos)
    }
}

// MARK: - Convenience Function

/// Parse a STRling DSL string into flags and AST
public func parse(_ src: String) throws -> (Flags, Node) {
    let parser = Parser(src)
    return try parser.parse()
}
