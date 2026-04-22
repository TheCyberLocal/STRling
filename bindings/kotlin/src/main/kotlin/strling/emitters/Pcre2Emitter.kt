package strling.emitters

import kotlinx.serialization.json.JsonPrimitive
import kotlinx.serialization.json.int
import kotlinx.serialization.json.intOrNull
import strling.core.*

/**
 * STRling PCRE2 Emitter - IR to PCRE2 Pattern String
 *
 * This class implements the emitter that transforms STRling's Intermediate
 * Representation (IR) into PCRE2-compatible regex pattern strings.
 */
object Pcre2Emitter {
    
    /**
     * Escapes PCRE2 metacharacters in literal strings.
     */
    fun escapeLiteral(s: String): String {
        val metaChars = setOf('.', '^', '$', '|', '(', ')', '?', '*', '+', '{', '}', '[', ']', '\\')
        val result = StringBuilder()
        
        for (ch in s) {
            if (ch in metaChars) {
                result.append('\\').append(ch)
            } else {
                result.append(ch)
            }
        }
        
        return result.toString()
    }
    
    /**
     * Escapes a character for use inside [...] per PCRE2 rules.
     */
    fun escapeClassChar(ch: String): String {
        if (ch.length != 1) {
            throw IllegalArgumentException("escapeClassChar expects single character")
        }
        
        val c = ch[0]
        return when (c) {
            '\\', ']' -> "\\$c"
            '[' -> "\\["
            '-' -> "\\-"
            '^' -> "\\^"
            '\n' -> "\\n"
            '\r' -> "\\r"
            '\t' -> "\\t"
            '\u000C' -> "\\f"
            '\u000B' -> "\\v"
            else -> {
                val code = c.code
                when {
                    code < 32 || (code in 127..159) -> String.format("\\x%02x", code)
                    else -> ch
                }
            }
        }
    }
    
    /**
     * Emit a PCRE2 character class.
     */
    private fun emitClass(cc: IRCharClass): String {
        val items = cc.items
        
        // Single-item shorthand optimization
        if (items.size == 1 && items[0] is IRClassEscape) {
            val esc = items[0] as IRClassEscape
            val k = esc.type
            val prop = esc.property
            
            when (k) {
                "d", "w", "s" -> {
                    if (cc.negated) {
                        return when (k) {
                            "d" -> "\\D"
                            "w" -> "\\W"
                            "s" -> "\\S"
                            else -> "\\$k"
                        }
                    }
                    return "\\$k"
                }
                "D", "W", "S" -> {
                    val base = k.lowercase()
                    return if (cc.negated) "\\$base" else "\\$k"
                }
                "p", "P" -> {
                    if (prop != null) {
                        val isUpperP = k == "P"
                        val useUpperP = cc.negated xor isUpperP
                        val use = if (useUpperP) "P" else "p"
                        return "\\$use{$prop}"
                    }
                }
            }
        }
        
        // General case: build a bracket class
        val parts = StringBuilder()
        for (item in items) {
            when (item) {
                is IRClassLiteral -> {
                    parts.append(escapeClassChar(item.char))
                }
                is IRClassRange -> {
                    parts.append(escapeClassChar(item.from))
                    parts.append('-')
                    parts.append(escapeClassChar(item.to))
                }
                is IRClassEscape -> {
                    when {
                        item.type.matches(Regex("[dDwWsS]")) -> {
                            parts.append('\\').append(item.type)
                        }
                        (item.type == "p" || item.type == "P") && item.property != null -> {
                            parts.append('\\').append(item.type).append('{').append(item.property).append('}')
                        }
                        else -> {
                            parts.append('\\').append(item.type)
                        }
                    }
                }
            }
        }
        
        val inner = parts.toString()
        return "[" + (if (cc.negated) "^" else "") + inner + "]"
    }
    
    /**
     * Emit quantifier suffix.
     */
    private fun emitQuantSuffix(minv: Int, maxv: Any, mode: String): String {
        val q = when {
            minv == 0 && maxv == "Inf" -> "*"
            minv == 1 && maxv == "Inf" -> "+"
            minv == 0 && maxv == 1 -> "?"
            minv == maxv -> "{$minv}"
            maxv == "Inf" -> "{$minv,}"
            else -> "{$minv,$maxv}"
        }
        
        return when (mode) {
            "Lazy" -> "$q?"
            "Possessive" -> "$q+"
            else -> q
        }
    }
    
    /**
     * Return true if 'child' needs a non-capturing group when quantifying.
     */
    private fun needsGroupForQuant(child: IROp): Boolean {
        return when (child) {
            is IRCharClass, is IRDot, is IRGroup, is IRBackref, is IRAnchor -> false
            is IRLit -> {
                // Single escape sequences don't need grouping
                if (child.value.length == 2 && child.value[0] == '\\') false
                else child.value.length > 1
            }
            is IRAlt, is IRLook -> true
            is IRSeq -> child.parts.size > 1
            else -> false
        }
    }
    
    /**
     * Generate opening for group based on type.
     */
    private fun emitGroupOpen(g: IRGroup): String {
        return when {
            g.atomic == true -> "(?>"
            g.capturing -> {
                if (g.name != null) "(?<${g.name}>"
                else "("
            }
            else -> "(?:"
        }
    }
    
    /**
     * Default upper bound on AST/IR nesting depth before the emitter
     * aborts. Mirrors the SSOT in the TypeScript reference and the
     * matching constants in every other binding.
     */
    const val DEFAULT_MAX_DEPTH = 250

    private const val REDOS_MESSAGE =
        "The pattern contains overlapping alternations or nested unbounded " +
            "quantifiers (e.g., (a+)+). This can lead to catastrophic backtracking " +
            "and exponential CPU spikes. Consider using possessive quantifiers " +
            "(++ or *+) or atomic groups to guarantee execution safety."

    /**
     * Mutable per-emit context threaded through [emitNode] so the depth,
     * lookbehind and warning-collection guards can fire without
     * polluting the public API.
     */
    private class EmitContext(maxDepth: Int) {
        var depth: Int = 0
        val maxDepth: Int = if (maxDepth > 0) maxDepth else DEFAULT_MAX_DEPTH
        var inLookbehind: Boolean = false
        val warnings: MutableList<STRlingWarning> = mutableListOf()
    }

    /** Resolve a `IRQuant.max` JsonElement to either an Int or the string "Inf". */
    private fun resolveMax(maxEl: Any): Any {
        return when {
            maxEl is JsonPrimitive -> maxEl.intOrNull ?: maxEl.content
            maxEl.toString() == "\"Inf\"" -> "Inf"
            else -> maxEl.toString().replace("\"", "")
        }
    }

    /** True iff a quantifier has an unbounded upper bound. */
    private fun isUnboundedQuant(q: IRQuant): Boolean = resolveMax(q.max) == "Inf"

    /** True iff a quantifier matches a variable number of characters. */
    private fun isVariableLengthQuant(q: IRQuant): Boolean {
        val mx = resolveMax(q.max)
        return mx != q.min
    }

    /**
     * Mirror of `_isFixedLengthBody` in the TS SSOT. Returns true when
     * [node] consumes a fixed number of characters and is therefore
     * safe inside a PCRE2 lookbehind.
     */
    private fun isFixedLengthBody(node: IROp): Boolean = when (node) {
        is IRQuant -> !isVariableLengthQuant(node) && isFixedLengthBody(node.child)
        is IRSeq -> node.parts.all { isFixedLengthBody(it) }
        is IRAlt -> node.branches.all { isFixedLengthBody(it) }
        is IRGroup -> isFixedLengthBody(node.body)
        is IRLook -> true // lookarounds are zero-width
        else -> true
    }

    /**
     * Mirror of `_hasNestedUnboundedQuant` in the TS SSOT. Detects an
     * unbounded quantifier reachable via single-child wrappers or any
     * branch of an Alt.
     */
    private fun hasNestedUnboundedQuant(child: IROp): Boolean = when (child) {
        is IRQuant -> isUnboundedQuant(child)
        is IRGroup -> hasNestedUnboundedQuant(child.body)
        is IRSeq -> child.parts.size == 1 && hasNestedUnboundedQuant(child.parts[0])
        is IRAlt -> child.branches.any { hasNestedUnboundedQuant(it) }
        else -> false
    }

    private fun pushReDoSWarning(ctx: EmitContext) {
        if (ctx.warnings.any { it.code == "REDOS_RISK" }) return
        ctx.warnings.add(STRlingWarning("REDOS_RISK", REDOS_MESSAGE))
    }

    /**
     * Emit a single IR node to PCRE2 syntax.
     */
    private fun emitNode(node: IROp, parentKind: String): String {
        return emitNode(node, parentKind, EmitContext(0))
    }

    private fun emitNode(node: IROp, parentKind: String, ctx: EmitContext): String {
        ctx.depth += 1
        try {
            if (ctx.depth > ctx.maxDepth) {
                throw STRlingCompilationError(
                    "Maximum AST depth exceeded (limit: ${ctx.maxDepth}). " +
                        "This pattern is too deeply nested and risks host stack " +
                        "exhaustion during emission. Refactor the pattern to " +
                        "reduce nesting, or flatten capturing groups where possible.",
                    "MAX_DEPTH",
                )
            }
            return when (node) {
                is IRLit -> escapeLiteral(node.value)
                is IRDot -> "."
                is IRAnchor -> {
                    val at = if (node.at == "NonWordBoundary") "NotWordBoundary" else node.at
                    when (at) {
                        "Start" -> "^"
                        "End" -> "$"
                        "WordBoundary" -> "\\b"
                        "NotWordBoundary" -> "\\B"
                        "AbsoluteStart" -> "\\A"
                        "EndBeforeFinalNewline" -> "\\Z"
                        "AbsoluteEnd" -> "\\z"
                        else -> ""
                    }
                }
                is IRBackref -> {
                    when {
                        node.byName != null -> "\\k<${node.byName}>"
                        node.byIndex != null -> "\\${node.byIndex}"
                        else -> ""
                    }
                }
                is IRCharClass -> emitClass(node)
                is IRSeq -> node.parts.joinToString("") { emitNode(it, "Seq", ctx) }
                is IRAlt -> {
                    val body = node.branches.joinToString("|") { emitNode(it, "Alt", ctx) }
                    if (parentKind in listOf("Seq", "Quant")) "(?:$body)" else body
                }
                is IRQuant -> {
                    // ReDoS guard: only flag when the *outer* quantifier is
                    // itself unbounded (e.g. `(a+)+`). A bounded outer like
                    // `(a+){0,3}` cannot produce exponential backtracking on
                    // its own.
                    if (isUnboundedQuant(node) && hasNestedUnboundedQuant(node.child)) {
                        pushReDoSWarning(ctx)
                    }
                    var childStr = emitNode(node.child, "Quant", ctx)
                    if (needsGroupForQuant(node.child) && node.child !is IRGroup) {
                        childStr = "(?:$childStr)"
                    }
                    childStr + emitQuantSuffix(node.min, resolveMax(node.max), node.mode)
                }
                is IRGroup -> emitGroupOpen(node) + emitNode(node.body, "Group", ctx) + ")"
                is IRLook -> {
                    // Variable-length lookbehind guard: PCRE2 mandates a
                    // fixed-width lookbehind body. Detect the violation here
                    // so the user sees a Signpost-pattern error rather than
                    // an opaque PCRE2 compile failure leaking from the runtime.
                    if (node.dir == "Behind" && !isFixedLengthBody(node.body)) {
                        throw STRlingCompilationError(
                            "PCRE2 does not support variable-length lookbehinds. " +
                                "The lookbehind body contains a quantifier that makes " +
                                "its length unpredictable. Rewrite the assertion using " +
                                "a fixed-length range (e.g. `{1,8}` instead of `+`), " +
                                "or restructure the pattern using a Lookahead, or " +
                                "extract the quantified portion outside the assertion.",
                            "VLB_NOT_SUPPORTED",
                        )
                    }
                    val wasInLb = ctx.inLookbehind
                    if (node.dir == "Behind") ctx.inLookbehind = true
                    try {
                        val op = when {
                            node.dir == "Ahead" && !node.neg -> "?="
                            node.dir == "Ahead" && node.neg -> "?!"
                            node.dir == "Behind" && !node.neg -> "?<="
                            node.dir == "Behind" && node.neg -> "?<!"
                            else -> "?="
                        }
                        "($op${emitNode(node.body, "Look", ctx)})"
                    } finally {
                        ctx.inLookbehind = wasInLb
                    }
                }
            }
        } finally {
            ctx.depth -= 1
        }
    }
    
    /**
     * Build the inline prefix form for flags.
     */
    private fun emitPrefixFromFlags(flags: Flags): String {
        val letters = StringBuilder()
        if (flags.ignoreCase) letters.append('i')
        if (flags.multiline) letters.append('m')
        if (flags.dotAll) letters.append('s')
        if (flags.unicode) letters.append('u')
        if (flags.extended) letters.append('x')
        
        return if (letters.isNotEmpty()) "(?$letters)" else ""
    }
    
    /**
     * Emit a PCRE2 pattern string from IR.
     */
    fun emit(irRoot: IROp, flags: Flags? = null): String {
        return emitWithDiagnostics(irRoot, flags, 0).pattern
    }

    /**
     * Emit a PCRE2 pattern string from IR and surface any non-fatal
     * diagnostics collected during emission. Pass [maxDepth] <= 0 to
     * use [DEFAULT_MAX_DEPTH].
     */
    fun emitWithDiagnostics(irRoot: IROp, flags: Flags? = null, maxDepth: Int = 0): CompileResult {
        val prefix = if (flags != null) emitPrefixFromFlags(flags) else ""
        val ctx = EmitContext(maxDepth)
        val body = emitNode(irRoot, "", ctx)
        return CompileResult(prefix + body, ctx.warnings.toList())
    }
}
