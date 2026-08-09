package strling.core

/**
 * STRling Parser - Recursive Descent Parser for STRling DSL
 *
 * This module implements a hand-rolled recursive-descent parser that transforms
 * STRling pattern syntax into Abstract Syntax Tree (AST) nodes.
 */
class Parser private constructor(text: String) {

    /**
     * Result of a parse operation containing flags and the parsed AST.
     */
    data class ParseResult(val flags: Flags, val ast: Node)

    /**
     * Lexer cursor for tracking position within the input text.
     */
    private class Cursor(
        val text: String,
        var i: Int = 0,
        var extendedMode: Boolean = false,
        var inClass: Int = 0
    ) {
        fun eof(): Boolean = i >= text.length

        fun peek(n: Int = 0): String {
            val j = i + n
            return if (j >= text.length) "" else text[j].toString()
        }

        fun take(): String {
            if (eof()) return ""
            val ch = text[i]
            i++
            return ch.toString()
        }

        fun match(s: String): Boolean {
            if (text.startsWith(s, i)) {
                i += s.length
                return true
            }
            return false
        }

        /**
         * Skip whitespace and comments in extended/free-spacing mode.
         */
        fun skipWsAndComments() {
            if (!extendedMode || inClass > 0) return

            while (!eof()) {
                val ch = peek()
                when {
                    ch in listOf(" ", "\t", "\r", "\n") -> i++
                    ch == "#" -> {
                        while (!eof() && peek() !in listOf("\r", "\n")) {
                            i++
                        }
                    }
                    else -> break
                }
            }
        }
    }

    private val originalText = text
    private val flags: Flags
    private val src: String
    private val cur: Cursor
    private var capCount = 0
    private val capNames = mutableSetOf<String>()

    private val controlEscapes = mapOf(
        "n" to "\n",
        "r" to "\r",
        "t" to "\t",
        "f" to "\u000C",
        "v" to "\u000B"
    )

    init {
        val dirResult = parseDirectives(text)
        flags = dirResult.flags
        src = dirResult.pattern
        cur = Cursor(src, 0, flags.extended, 0)
    }

    /**
     * Raise a STRlingParseError with an instructional hint.
     */
    private fun raiseError(message: String, pos: Int): Nothing {
        throw STRlingParseError(message, pos, src)
    }

    /**
     * Directive parsing result.
     */
    private data class DirectiveResult(val flags: Flags, val pattern: String)

    /**
     * Parse directives (like %flags) from the pattern.
     */
    private fun parseDirectives(text: String): DirectiveResult {
        var flags = Flags()
        val lines = text.split("\n")
        val patternLines = mutableListOf<String>()
        var inPattern = false

        for ((lineNum, rawLine) in lines.withIndex()) {
            val line = rawLine.trimEnd('\r')
            val stripped = line.trim()

            // Skip leading blank lines or comments
            if (!inPattern && (stripped.isEmpty() || stripped.startsWith("#"))) {
                continue
            }

            // Process %flags directive
            if (!inPattern && stripped.startsWith("%flags")) {
                val idx = line.indexOf("%flags")
                val after = line.substring(idx + "%flags".length)

                // Normalize separators and whitespace
                val letters = after.replace(Regex("[,\\[\\]\\s]+"), " ").trim().lowercase()
                val validFlags = setOf('i', 'm', 's', 'u', 'x')

                for (ch in letters.replace(" ", "")) {
                    if (ch !in validFlags) {
                        val pos = lines.take(lineNum).sumOf { it.length + 1 }
                        throw STRlingParseError("Invalid flag '$ch'", pos + idx, text)
                    }
                }

                flags = Flags.fromLetters(letters)

                // Check for remainder pattern content on the same line
                val remainder = after.trim()
                if (remainder.isNotEmpty() && !remainder.all { " ,\t[]imsuxIMSUX".contains(it) }) {
                    inPattern = true
                    val patternStart = after.takeWhile { " ,\t[]imsuxIMSUX".contains(it) }.length
                    if (patternStart < after.length) {
                        patternLines.add(after.substring(patternStart))
                    }
                } else {
                    inPattern = true
                }
                continue
            }

            // Reject unknown directives
            if (!inPattern && stripped.startsWith("%")) {
                val pos = lines.take(lineNum).sumOf { it.length + 1 }
                throw STRlingParseError("Malformed directive", pos + line.indexOf("%"), text)
            }

            // Check for directive after pattern content
            if (line.contains("%flags")) {
                val pos = lines.take(lineNum).sumOf { it.length + 1 }
                throw STRlingParseError(
                    "Directive after pattern",
                    pos + line.indexOf("%flags"),
                    text
                )
            }

            inPattern = true
            patternLines.add(line)
        }

        return DirectiveResult(flags, patternLines.joinToString("\n"))
    }

    /**
     * Parse the entire STRling pattern into an AST.
     */
    private fun parseInternal(): Node {
        cur.skipWsAndComments()
        if (cur.eof()) {
            return Literal("")
        }

        val node = parseAlt()
        cur.skipWsAndComments()

        if (!cur.eof()) {
            when (cur.peek()) {
                ")" -> raiseError("Unmatched ')'", cur.i)
                "|" -> raiseError("Alternation lacks right-hand side", cur.i)
                else -> raiseError("Unexpected trailing input", cur.i)
            }
        }

        return node
    }

    /**
     * Parse an alternation expression.
     */
    private fun parseAlt(): Node {
        cur.skipWsAndComments()
        if (cur.peek() == "|") {
            raiseError("Alternation lacks left-hand side", cur.i)
        }

        val branches = mutableListOf<Node>()
        branches.add(parseSeq())
        cur.skipWsAndComments()

        while (cur.peek() == "|") {
            val pipePos = cur.i
            cur.take()
            cur.skipWsAndComments()

            if (cur.peek().isEmpty()) {
                raiseError("Alternation lacks right-hand side", pipePos)
            }
            if (cur.peek() == "|") {
                raiseError("Empty alternation", pipePos)
            }

            branches.add(parseSeq())
            cur.skipWsAndComments()
        }

        return if (branches.size == 1) branches[0] else Alternation(branches)
    }

    /**
     * Parse a sequence of terms.
     */
    private fun parseSeq(): Node {
        val parts = mutableListOf<Node>()
        var prevHadFailedQuant = false

        while (true) {
            cur.skipWsAndComments()
            val ch = cur.peek()

            // Invalid quantifier at start of sequence
            if (ch.isNotEmpty() && ch in listOf("*", "+", "?", "{") && parts.isEmpty()) {
                raiseError("Invalid quantifier '$ch'", cur.i)
            }

            // Stop parsing sequence
            if (ch.isEmpty() || ch == ")" || ch == "|") {
                break
            }

            val atom = parseAtom()
            val (quantified, hadFailedQuant) = parseQuantIfAny(atom)

            // Coalesce adjacent Lit nodes
            val prevIsBackref = parts.isNotEmpty() && parts.last() is Backreference
            val shouldCoalesce = quantified is Literal &&
                    parts.isNotEmpty() &&
                    parts.last() is Literal &&
                    !cur.extendedMode &&
                    !prevHadFailedQuant &&
                    !prevIsBackref

            if (shouldCoalesce) {
                val prevLit = parts.removeAt(parts.lastIndex) as Literal
                val currLit = quantified as Literal
                parts.add(Literal(prevLit.value + currLit.value))
            } else {
                parts.add(quantified)
            }

            prevHadFailedQuant = hadFailedQuant
        }

        return when {
            parts.isEmpty() -> Literal("")
            parts.size == 1 -> parts[0]
            else -> Sequence(parts)
        }
    }

    /**
     * Result of quantifier parsing.
     */
    private data class QuantResult(val node: Node, val hadFailedParse: Boolean)

    /**
     * Parse an optional quantifier following an atom.
     */
    private fun parseQuantIfAny(child: Node): QuantResult {
        val ch = cur.peek()

        // Anchors cannot be quantified
        if (child is Anchor) {
            if (ch.isNotEmpty() && ch in listOf("*", "+", "?", "{")) {
                raiseError("Cannot quantify anchor", cur.i)
            }
            return QuantResult(child, false)
        }

        var min = 0
        var max: Any = 0

        when (ch) {
            "*" -> {
                cur.take()
                min = 0
                max = "Inf"
            }
            "+" -> {
                cur.take()
                min = 1
                max = "Inf"
            }
            "?" -> {
                cur.take()
                min = 0
                max = 1
            }
            "{" -> {
                val bq = parseBraceQuant() ?: return QuantResult(child, true)
                min = bq.first ?: 0
                max = bq.second ?: "Inf"
            }
            else -> return QuantResult(child, false)
        }

        // Validate range
        if (max is Int && min > max) {
            raiseError("Invalid quantifier range", cur.i)
        }

        // Check for mode suffix
        val greedy: Boolean
        val lazy: Boolean
        val possessive: Boolean

        when (cur.peek()) {
            "?" -> {
                cur.take()
                greedy = false
                lazy = true
                possessive = false
            }
            "+" -> {
                cur.take()
                greedy = false
                lazy = false
                possessive = true
            }
            else -> {
                greedy = true
                lazy = false
                possessive = false
            }
        }

        val maxElement = when (max) {
            is Int -> kotlinx.serialization.json.JsonPrimitive(max)
            else -> kotlinx.serialization.json.JsonPrimitive("Inf")
        }

        return QuantResult(Quantifier(child, min, maxElement, greedy, lazy, possessive), false)
    }

    /**
     * Parse a brace quantifier {m,n}.
     */
    private fun parseBraceQuant(): Pair<Int?, Any?>? {
        if (!cur.match("{")) return null

        val quantStart = cur.i - 1
        cur.skipWsAndComments()

        // Read first number
        val digits = StringBuilder()
        while (!cur.eof() && cur.peek()[0].isDigit()) {
            digits.append(cur.take())
        }

        val min = if (digits.isNotEmpty()) digits.toString().toInt() else null

        cur.skipWsAndComments()
        if (min == null) {
            // Look ahead for a closing '}' with non-digit/non-comma content (e.g. {foo})
            val saved = cur.i
            var j = 0
            val content = StringBuilder()
            while (true) {
                val ch = cur.peek(j)
                if (ch == "" || ch == "}" || ch == "\r" || ch == "\n") break
                content.append(ch)
                j++
            }
            if (cur.peek(j) == "}" && content.isNotEmpty() && content.toString().any { !it.isDigit() && it != ',' }) {
                raiseError("Brace quantifier: Invalid brace quantifier content", quantStart)
            }
            cur.i = quantStart
            return null
        }

        if (cur.peek() == ",") {
            cur.take()
            cur.skipWsAndComments()

            val maxDigits = StringBuilder()
            while (!cur.eof() && cur.peek()[0].isDigit()) {
                maxDigits.append(cur.take())
            }

            val max: Any? = if (maxDigits.isNotEmpty()) maxDigits.toString().toInt() else "Inf"

            cur.skipWsAndComments()
            if (!cur.match("}")) {
                raiseError("Incomplete quantifier", cur.i)
            }

            return Pair(min, max)
        } else if (cur.peek() == "}") {
            cur.take()
            return Pair(min, min)
        }

        raiseError("Incomplete quantifier", cur.i)
    }

    /**
     * Parse an atomic pattern element.
     */
    private fun parseAtom(): Node {
        cur.skipWsAndComments()
        val ch = cur.peek()

        return when (ch) {
            "." -> {
                cur.take()
                Dot()
            }
            "^" -> {
                cur.take()
                Anchor("Start")
            }
            "$" -> {
                cur.take()
                Anchor("End")
            }
            "(" -> parseGroupOrLook()
            "[" -> parseCharClass()
            "\\" -> parseEscapeAtom()
            ")" -> raiseError("Unmatched ')'", cur.i)
            "|" -> {
                raiseError("Unexpected token", cur.i)
            }
            else -> Literal(cur.take())
        }
    }

    /**
     * Parse an escape sequence atom.
     */
    private fun parseEscapeAtom(): Node {
        val startPos = cur.i
        cur.take() // consume backslash
        val nxt = cur.peek()

        // Backref by index
        if (nxt.isNotEmpty() && nxt[0].isDigit() && nxt != "0") {
            val savedPos = cur.i
            val numStr = StringBuilder()

            while (cur.peek().isNotEmpty() && cur.peek()[0].isDigit()) {
                numStr.append(cur.take())
                val num = numStr.toString().toInt()
                if (num > capCount) {
                    cur.i--
                    numStr.setLength(numStr.length - 1)
                    break
                }
            }

            if (numStr.isNotEmpty()) {
                val num = numStr.toString().toInt()
                if (num <= capCount) {
                    return Backreference(num, null)
                }
            }

            cur.i = savedPos
            val num = readDecimal()
            raiseError("Backreference to undefined group \\$num", startPos)
        }

        // Anchors
        when (nxt) {
            "b" -> { cur.take(); return Anchor("WordBoundary") }
            "B" -> { cur.take(); return Anchor("NotWordBoundary") }
            "A" -> { cur.take(); return Anchor("AbsoluteStart") }
            "Z" -> { cur.take(); return Anchor("EndBeforeFinalNewline") }
        }

        // Named backref \k<name>
        if (nxt == "k") {
            cur.take()
            if (!cur.match("<")) {
                raiseError("Expected '<' after \\k", startPos)
            }
            val name = readIdentUntil(">")
            if (!cur.match(">")) {
                raiseError("Unterminated named backref", startPos)
            }
            if (name !in capNames) {
                raiseError("Backreference to undefined group <$name>", startPos)
            }
            return Backreference(null, name)
        }

        // Shorthand classes
        if (nxt in listOf("d", "D", "w", "W", "s", "S")) {
            val type = cur.take()
            return CharacterClass(false, listOf(Escape(type)))
        }

        // Property escapes
        if (nxt in listOf("p", "P")) {
            val tp = cur.take()
            if (!cur.match("{")) {
                raiseError("Expected { after \\p/\\P", startPos + 1)
            }
            val prop = readUntil("}")
            if (!cur.match("}")) {
                raiseError("Unterminated \\p{...}", startPos + 1)
            }
            val negated = tp == "P"
            return CharacterClass(false, listOf(UnicodeProperty(prop, null, negated)))
        }

        // Control escapes
        if (nxt in controlEscapes) {
            val ch = cur.take()
            return Literal(controlEscapes[ch]!!)
        }

        // Hex escapes
        if (nxt == "x") {
            return Literal(parseHexEscape(startPos))
        }

        // Unicode escapes
        if (nxt in listOf("u", "U")) {
            return Literal(parseUnicodeEscape(startPos))
        }

        // Null byte
        if (nxt == "0") {
            cur.take()
            return Literal("\u0000")
        }

        // Escaped literal
        if (nxt.isNotEmpty()) {
            val escapedChar = cur.take()
            if (escapedChar[0].isLetter()) {
                raiseError("Unknown escape sequence \\$escapedChar", startPos)
            }
            return Literal(escapedChar)
        }

        raiseError("Incomplete escape at end of pattern", startPos)
    }

    private fun readDecimal(): Int {
        val digits = StringBuilder()
        while (!cur.eof() && cur.peek()[0].isDigit()) {
            digits.append(cur.take())
        }
        return digits.toString().toInt()
    }

    private fun readIdentUntil(terminator: String): String {
        val result = StringBuilder()
        while (!cur.eof() && cur.peek() != terminator) {
            result.append(cur.take())
        }
        return result.toString()
    }

    private fun readUntil(terminator: String): String {
        val result = StringBuilder()
        while (!cur.eof() && cur.peek() != terminator) {
            result.append(cur.take())
        }
        return result.toString()
    }

    private fun parseHexEscape(startPos: Int): String {
        cur.take() // consume x

        if (cur.match("{")) {
            val hexs = StringBuilder()
            while (!cur.eof() && cur.peek().matches(Regex("[0-9A-Fa-f]"))) {
                hexs.append(cur.take())
            }
            if (!cur.match("}")) {
                raiseError("Unterminated \\x{...}", startPos)
            }
            val cp = if (hexs.isNotEmpty()) hexs.toString().toInt(16) else 0
            return String(Character.toChars(cp))
        }

        val h1 = cur.take()
        val h2 = cur.take()
        if (!h1.matches(Regex("[0-9A-Fa-f]")) || !h2.matches(Regex("[0-9A-Fa-f]"))) {
            raiseError("Invalid \\xHH escape", startPos)
        }
        return (h1 + h2).toInt(16).toChar().toString()
    }

    private fun parseUnicodeEscape(startPos: Int): String {
        val tp = cur.take() // u or U

        if (tp == "u" && cur.match("{")) {
            val hexs = StringBuilder()
            while (!cur.eof() && cur.peek().matches(Regex("[0-9A-Fa-f]"))) {
                hexs.append(cur.take())
            }
            if (!cur.match("}")) {
                raiseError("Unterminated \\u{...}", startPos)
            }
            val cp = if (hexs.isNotEmpty()) hexs.toString().toInt(16) else 0
            return String(Character.toChars(cp))
        }

        if (tp == "U") {
            val hexs = StringBuilder()
            repeat(8) {
                val ch = cur.take()
                if (!ch.matches(Regex("[0-9A-Fa-f]"))) {
                    raiseError("Invalid \\UHHHHHHHH escape", startPos)
                }
                hexs.append(ch)
            }
            val cp = hexs.toString().toInt(16)
            return String(Character.toChars(cp))
        }

        val hexs = StringBuilder()
        repeat(4) {
            val ch = cur.take()
            if (!ch.matches(Regex("[0-9A-Fa-f]"))) {
                raiseError("Invalid \\uHHHH escape", startPos)
            }
            hexs.append(ch)
        }
        val cp = hexs.toString().toInt(16)
        return String(Character.toChars(cp))
    }

    /**
     * Parse a character class.
     */
    private fun parseCharClass(): Node {
        cur.take() // consume [
        val startPos = cur.i
        cur.inClass++

        var negated = false
        if (cur.peek() == "^") {
            negated = true
            cur.take()
        }

        val items = mutableListOf<ClassItem>()

        while (true) {
            if (cur.eof()) {
                cur.inClass--
                raiseError("Unterminated character class", cur.i)
            }

            // Close the class
            if (cur.peek() == "]" && cur.i > startPos) {
                cur.take()
                cur.inClass--
                return CharacterClass(negated, items)
            }

            // Check for range
            if (cur.peek() == "-" &&
                items.isNotEmpty() &&
                items.last() is Literal &&
                cur.peek(1) != "]") {

                val dashPos = cur.i
                cur.take() // consume -
                val endItem = readClassItem()

                if (endItem is Literal) {
                    val startLit = items.removeAt(items.lastIndex) as Literal
                    val startCh = startLit.value
                    val endCh = endItem.value

                    if (startCh[0] > endCh[0]) {
                        raiseError("Invalid character range [$startCh-$endCh]", dashPos)
                    }
                    items.add(Range(startCh, endCh))
                } else {
                    items.add(Literal("-"))
                    items.add(endItem)
                }
                continue
            }

            items.add(readClassItem())
        }
    }

    /**
     * Read one character class item.
     */
    private fun readClassItem(): ClassItem {
        if (cur.peek() == "\\") {
            val escapeStart = cur.i
            cur.take() // consume backslash
            val nxt = cur.peek()

            // Shorthand classes
            if (nxt in listOf("d", "D", "w", "W", "s", "S")) {
                return Escape(cur.take())
            }

            // Unicode properties
            if (nxt in listOf("p", "P")) {
                val tp = cur.take()
                if (!cur.match("{")) {
                    raiseError("Expected { after \\p/\\P", escapeStart)
                }
                val prop = readUntil("}")
                if (!cur.match("}")) {
                    raiseError("Unterminated \\p{...}", escapeStart)
                }
                val negated = tp == "P"
                return UnicodeProperty(prop, null, negated)
            }

            // Hex escapes
            if (nxt == "x") {
                return Literal(parseHexEscape(escapeStart))
            }

            // Unicode escapes
            if (nxt in listOf("u", "U")) {
                return Literal(parseUnicodeEscape(escapeStart))
            }

            // Null byte
            if (nxt == "0") {
                cur.take()
                return Literal("\u0000")
            }

            // Control escapes
            if (nxt in controlEscapes) {
                val ch = cur.take()
                return Literal(controlEscapes[ch]!!)
            }

            // \b inside class is backspace
            if (nxt == "b") {
                cur.take()
                return Literal("\b")
            }

            // Identity escape
            return Literal(cur.take())
        }

        // Regular literal
        return Literal(cur.take())
    }

    /**
     * Parse a group or lookaround construct.
     */
    private fun parseGroupOrLook(): Node {
        val startPos = cur.i
        cur.take() // consume (

        // Non-capturing group
        if (cur.match("?:")) {
            val body = parseAlt()
            if (!cur.match(")")) {
                raiseError("Unterminated group", cur.i)
            }
            return Group(false, body)
        }

        // Atomic group
        if (cur.match("?>")) {
            val body = parseAlt()
            if (!cur.match(")")) {
                raiseError("Unterminated group", cur.i)
            }
            return Group(false, body, null, true)
        }

        // Positive lookahead
        if (cur.match("?=")) {
            val body = parseAlt()
            if (!cur.match(")")) {
                raiseError("Unterminated lookahead", cur.i)
            }
            return Lookahead(body)
        }

        // Negative lookahead
        if (cur.match("?!")) {
            val body = parseAlt()
            if (!cur.match(")")) {
                raiseError("Unterminated lookahead", cur.i)
            }
            return NegativeLookahead(body)
        }

        // Positive lookbehind
        if (cur.match("?<=")) {
            val body = parseAlt()
            if (!cur.match(")")) {
                raiseError("Unterminated lookbehind", cur.i)
            }
            return Lookbehind(body)
        }

        // Negative lookbehind
        if (cur.match("?<!")) {
            val body = parseAlt()
            if (!cur.match(")")) {
                raiseError("Unterminated lookbehind", cur.i)
            }
            return NegativeLookbehind(body)
        }

        // Named capturing group
        if (cur.match("?<")) {
            val nameStartPos = cur.i
            val name = readIdentUntil(">")
            if (!cur.match(">")) {
                raiseError("Unterminated group name", cur.i)
            }
            if (!name.matches(Regex("^[A-Za-z_][A-Za-z0-9_]*$"))) {
                raiseError("Invalid group name <$name>", nameStartPos)
            }
            if (name in capNames) {
                raiseError("Duplicate group name <$name>", startPos)
            }
            capNames.add(name)
            capCount++
            val body = parseAlt()
            if (!cur.match(")")) {
                raiseError("Unterminated group", cur.i)
            }
            return Group(true, body, name)
        }

        // Check for inline modifiers
        if (cur.peek() == "?") {
            raiseError("Inline modifiers are not supported", startPos + 1)
        }

        // Default: capturing group
        capCount++
        val body = parseAlt()
        if (!cur.match(")")) {
            raiseError("Unterminated group", cur.i)
        }
        return Group(true, body)
    }

    companion object {
        /**
         * Parse a STRling pattern string into an AST.
         */
        fun parse(src: String): ParseResult {
            val parser = Parser(src)
            val ast = parser.parseInternal()
            return ParseResult(parser.flags, ast)
        }
    }
}

// HintEngine is now in its own file: strling/core/HintEngine.kt
