package strling

import kotlinx.serialization.json.JsonPrimitive
import strling.core.*

/**
 * STRling Simply API - Fluent Pattern Builder for Kotlin
 *
 * This object provides a fluent, chainable API for building regex patterns
 * without dealing with raw AST node classes. It mirrors the TypeScript reference
 * implementation while following Kotlin idioms and conventions.
 *
 * Example:
 * ```kotlin
 * import strling.Simply
 *
 * val pattern = Simply.merge(
 *     Simply.start(),
 *     Simply.capture(Simply.digit(3)),
 *     Simply.may(Simply.anyOf("-. ")),
 *     Simply.capture(Simply.digit(3)),
 *     Simply.may(Simply.anyOf("-. ")),
 *     Simply.capture(Simply.digit(4)),
 *     Simply.end()
 * )
 * ```
 */
object Simply {
    
    // ========== Static Patterns / Character Classes ==========
    
    /**
     * Matches the start of a line/string.
     */
    fun start(): Pattern = Pattern(Anchor(at = "Start"))
    
    /**
     * Matches the end of a line/string.
     */
    fun end(): Pattern = Pattern(Anchor(at = "End"))
    
    /**
     * Matches any digit character (0-9).
     *
     * @param minRep Minimum number of repetitions (default: 1, matches exactly once)
     * @param maxRep Maximum number of repetitions. If null, matches exactly minRep times.
     *               Use 0 for unlimited repetitions.
     */
    fun digit(minRep: Int = 1, maxRep: Int? = null): Pattern {
        val node = CharacterClass(
            negated = false,
            members = listOf(Escape(kind = "d"))
        )
        val pattern = Pattern(node)
        return if (minRep == 1 && maxRep == null) pattern else pattern.repeat(minRep, maxRep)
    }
    
    /**
     * Matches any letter (uppercase or lowercase).
     *
     * @param minRep Minimum number of repetitions (default: 1)
     * @param maxRep Maximum number of repetitions. If null, matches exactly minRep times.
     */
    fun letter(minRep: Int = 1, maxRep: Int? = null): Pattern {
        val node = CharacterClass(
            negated = false,
            members = listOf(
                Range(from = "A", to = "Z"),
                Range(from = "a", to = "z")
            )
        )
        val pattern = Pattern(node)
        return if (minRep == 1 && maxRep == null) pattern else pattern.repeat(minRep, maxRep)
    }
    
    /**
     * Matches any alphanumeric character (letter or digit).
     *
     * @param minRep Minimum number of repetitions (default: 1)
     * @param maxRep Maximum number of repetitions. If null, matches exactly minRep times.
     */
    fun alphaNum(minRep: Int = 1, maxRep: Int? = null): Pattern {
        val node = CharacterClass(
            negated = false,
            members = listOf(
                Range(from = "A", to = "Z"),
                Range(from = "a", to = "z"),
                Range(from = "0", to = "9")
            )
        )
        val pattern = Pattern(node)
        return if (minRep == 1 && maxRep == null) pattern else pattern.repeat(minRep, maxRep)
    }
    
    /**
     * Matches any whitespace character.
     *
     * @param minRep Minimum number of repetitions (default: 1)
     * @param maxRep Maximum number of repetitions. If null, matches exactly minRep times.
     */
    fun whitespace(minRep: Int = 1, maxRep: Int? = null): Pattern {
        val node = CharacterClass(
            negated = false,
            members = listOf(Escape(kind = "s"))
        )
        val pattern = Pattern(node)
        return if (minRep == 1 && maxRep == null) pattern else pattern.repeat(minRep, maxRep)
    }
    
    /**
     * Creates a literal pattern from a string.
     *
     * @param text The text to match literally
     */
    fun literal(text: String): Pattern = Pattern(Literal(value = text))
    
    // ========== Character Sets ==========
    
    /**
     * Matches any character within a range.
     *
     * @param start Starting character or digit
     * @param end Ending character or digit
     */
    fun between(start: Any, end: Any): Pattern {
        val (startStr, endStr) = when {
            start is Int && end is Int -> {
                require(start in 0..9 && end in 0..9) {
                    "between(start, end): Both must be single digits (0-9)"
                }
                require(start <= end) {
                    "between(start, end): start must not be greater than end"
                }
                start.toString() to end.toString()
            }
            start is Char && end is Char -> {
                require(start.isLetter() && end.isLetter()) {
                    "between(start, end): Both must be letters"
                }
                require(
                    (start.isLowerCase() && end.isLowerCase()) ||
                    (start.isUpperCase() && end.isUpperCase())
                ) {
                    "between(start, end): Both letters must be the same case"
                }
                require(start <= end) {
                    "between(start, end): start must not be greater than end"
                }
                start.toString() to end.toString()
            }
            start is String && end is String -> {
                require(start.length == 1 && end.length == 1) {
                    "between(start, end): Both must be single characters"
                }
                val startChar = start[0]
                val endChar = end[0]
                require((startChar.isLetter() && endChar.isLetter()) || (startChar.isDigit() && endChar.isDigit())) {
                    "between(start, end): Both must be either letters or digits, not mixed"
                }
                if (startChar.isLetter()) {
                    require(
                        (startChar.isLowerCase() && endChar.isLowerCase()) ||
                        (startChar.isUpperCase() && endChar.isUpperCase())
                    ) {
                        "between(start, end): Both letters must be the same case"
                    }
                }
                require(start <= end) {
                    "between(start, end): start must not be greater than end"
                }
                start to end
            }
            else -> throw IllegalArgumentException(
                "between(start, end): Both arguments must be integers (0-9) or letters of the same case"
            )
        }
        
        return Pattern(
            CharacterClass(
                negated = false,
                members = listOf(Range(from = startStr, to = endStr))
            )
        )
    }
    
    /**
     * Matches any of the provided characters.
     * This creates a character class from a string of characters.
     *
     * @param chars String containing characters to match
     */
    fun anyOf(chars: String): Pattern {
        require(chars.isNotEmpty()) { "anyOf(chars): chars cannot be empty" }
        
        val members = chars.map { Literal(value = it.toString()) }
        return Pattern(
            CharacterClass(
                negated = false,
                members = members
            )
        )
    }
    
    // ========== Constructors ==========
    
    /**
     * Matches any one of the provided patterns (alternation/OR operation).
     *
     * @param patterns One or more patterns or strings to match
     */
    fun anyOf(vararg patterns: Any): Pattern {
        require(patterns.isNotEmpty()) { "anyOf(...patterns): At least one pattern required" }
        
        val nodes = patterns.map { pattern ->
            when (pattern) {
                is Pattern -> pattern.node
                is String -> Literal(value = pattern)
                else -> throw IllegalArgumentException(
                    "anyOf(...patterns): All arguments must be Pattern or String"
                )
            }
        }
        
        val allNamedGroups = patterns.filterIsInstance<Pattern>().flatMap { it.namedGroups }
        return Pattern(Alternation(alternatives = nodes), namedGroups = allNamedGroups)
    }
    
    /**
     * Concatenates patterns sequentially.
     *
     * @param patterns One or more patterns or strings to concatenate
     */
    fun merge(vararg patterns: Any): Pattern {
        require(patterns.isNotEmpty()) { "merge(...patterns): At least one pattern required" }
        
        val nodes = patterns.map { pattern ->
            when (pattern) {
                is Pattern -> pattern.node
                is String -> Literal(value = pattern)
                else -> throw IllegalArgumentException(
                    "merge(...patterns): All arguments must be Pattern or String"
                )
            }
        }
        
        val allNamedGroups = patterns.filterIsInstance<Pattern>().flatMap { it.namedGroups }
        return if (nodes.size == 1) {
            Pattern(nodes[0], namedGroups = allNamedGroups)
        } else {
            Pattern(Sequence(parts = nodes), namedGroups = allNamedGroups)
        }
    }
    
    /**
     * Makes patterns optional (matches 0 or 1 times).
     *
     * @param patterns One or more patterns or strings to make optional
     */
    fun may(vararg patterns: Any): Pattern {
        require(patterns.isNotEmpty()) { "may(...patterns): At least one pattern required" }
        
        val bodyNode = if (patterns.size == 1) {
            when (val pattern = patterns[0]) {
                is Pattern -> pattern.node
                is String -> Literal(value = pattern)
                else -> throw IllegalArgumentException(
                    "may(...patterns): All arguments must be Pattern or String"
                )
            }
        } else {
            val nodes = patterns.map { pattern ->
                when (pattern) {
                    is Pattern -> pattern.node
                    is String -> Literal(value = pattern)
                    else -> throw IllegalArgumentException(
                        "may(...patterns): All arguments must be Pattern or String"
                    )
                }
            }
            Sequence(parts = nodes)
        }
        
        val allNamedGroups = if (patterns.size == 1 && patterns[0] is Pattern) {
            (patterns[0] as Pattern).namedGroups
        } else {
            patterns.filterIsInstance<Pattern>().flatMap { it.namedGroups }
        }
        
        return Pattern(
            Quantifier(
                target = bodyNode,
                min = 0,
                max = JsonPrimitive(1),
                greedy = true,
                lazy = false,
                possessive = false
            ),
            namedGroups = allNamedGroups
        )
    }
    
    /**
     * Creates a numbered capture group.
     *
     * @param patterns One or more patterns or strings to capture
     */
    fun capture(vararg patterns: Any): Pattern {
        require(patterns.isNotEmpty()) { "capture(...patterns): At least one pattern required" }
        
        val bodyNode = if (patterns.size == 1) {
            when (val pattern = patterns[0]) {
                is Pattern -> pattern.node
                is String -> Literal(value = pattern)
                else -> throw IllegalArgumentException(
                    "capture(...patterns): All arguments must be Pattern or String"
                )
            }
        } else {
            val nodes = patterns.map { pattern ->
                when (pattern) {
                    is Pattern -> pattern.node
                    is String -> Literal(value = pattern)
                    else -> throw IllegalArgumentException(
                        "capture(...patterns): All arguments must be Pattern or String"
                    )
                }
            }
            Sequence(parts = nodes)
        }
        
        val allNamedGroups = if (patterns.size == 1 && patterns[0] is Pattern) {
            (patterns[0] as Pattern).namedGroups
        } else {
            patterns.filterIsInstance<Pattern>().flatMap { it.namedGroups }
        }
        
        return Pattern(Group(capturing = true, body = bodyNode), namedGroups = allNamedGroups)
    }
    
    /**
     * Creates a named capture group.
     *
     * @param name The name for the capture group
     * @param patterns One or more patterns or strings to capture
     */
    fun group(name: String, vararg patterns: Any): Pattern {
        require(name.isNotEmpty()) { "group(name, ...patterns): name cannot be empty" }
        require(patterns.isNotEmpty()) { "group(name, ...patterns): At least one pattern required" }
        
        val bodyNode = if (patterns.size == 1) {
            when (val pattern = patterns[0]) {
                is Pattern -> pattern.node
                is String -> Literal(value = pattern)
                else -> throw IllegalArgumentException(
                    "group(name, ...patterns): All arguments must be Pattern or String"
                )
            }
        } else {
            val nodes = patterns.map { pattern ->
                when (pattern) {
                    is Pattern -> pattern.node
                    is String -> Literal(value = pattern)
                    else -> throw IllegalArgumentException(
                        "group(name, ...patterns): All arguments must be Pattern or String"
                    )
                }
            }
            Sequence(parts = nodes)
        }
        
        // Collect named groups from input patterns and combine with the new group name
        val existingNamedGroups = patterns
            .filterIsInstance<Pattern>()
            .flatMap { it.namedGroups }
        return Pattern(
            Group(capturing = true, body = bodyNode, name = name),
            namedGroups = existingNamedGroups + name
        )
    }
}

/**
 * Represents a regex pattern with fluent chainable methods.
 *
 * Pattern objects are immutable - all modifier methods return new Pattern instances.
 */
data class Pattern(
    val node: Node,
    val namedGroups: List<String> = emptyList()
) {
    
    /**
     * Makes this pattern optional (matches 0 or 1 times).
     */
    fun optional(): Pattern {
        return Pattern(
            Quantifier(
                target = node,
                min = 0,
                max = JsonPrimitive(1),
                greedy = true,
                lazy = false,
                possessive = false
            ),
            namedGroups = namedGroups
        )
    }
    
    /**
     * Wraps this pattern in a capturing group.
     */
    fun asCapture(): Pattern {
        return Pattern(
            Group(capturing = true, body = node),
            namedGroups = namedGroups
        )
    }
    
    /**
     * Wraps this pattern in a named capturing group.
     *
     * @param name The name for the capture group
     */
    fun asGroup(name: String): Pattern {
        require(name.isNotEmpty()) { "asGroup(name): name cannot be empty" }
        return Pattern(
            Group(capturing = true, body = node, name = name),
            namedGroups = namedGroups + name
        )
    }
    
    /**
     * Makes this pattern repeat between min and max times.
     *
     * @param min Minimum number of repetitions
     * @param max Maximum number of repetitions. If null, matches exactly min times.
     *            Use 0 for unlimited repetitions.
     */
    fun repeat(min: Int, max: Int? = null): Pattern {
        require(min >= 0) { "repeat(min, max): min must be 0 or greater" }
        if (max != null) {
            require(max >= 0) { "repeat(min, max): max must be 0 or greater" }
            if (max != 0) {
                require(max >= min) {
                    "repeat(min, max): max must be greater than or equal to min (use 0 for unbounded)"
                }
            }
        }
        
        // Validate named groups cannot be repeated more than once
        // max == null means exactly min times
        // max == 0 means unbounded (min or more)
        // max > 1 means can repeat more than once
        val canRepeatMultiple = when (max) {
            null -> min > 1
            0 -> true  // unbounded
            else -> max > 1
        }
        
        if (namedGroups.isNotEmpty() && canRepeatMultiple) {
            throw IllegalArgumentException(
                "repeat(min, max): Named groups cannot be repeated more than once as they must be unique. " +
                "Consider using asCapture() or Simply.merge() instead."
            )
        }
        
        val qMax = when (max) {
            null -> JsonPrimitive(min)
            0 -> JsonPrimitive("Inf")
            else -> JsonPrimitive(max)
        }
        
        return Pattern(
            Quantifier(
                target = node,
                min = min,
                max = qMax,
                greedy = true,
                lazy = false,
                possessive = false
            ),
            namedGroups = namedGroups
        )
    }
    
    /**
     * Makes this pattern lazy (non-greedy).
     *
     * Can only be applied to quantified patterns (created with optional() or repeat()).
     */
    fun lazy(): Pattern {
        require(node is Quantifier) {
            "lazy(): Can only make quantified patterns lazy. Use optional() or repeat() first."
        }
        
        val quant = node as Quantifier
        return Pattern(
            Quantifier(
                target = quant.target,
                min = quant.min,
                max = quant.max,
                greedy = false,
                lazy = true,
                possessive = false
            ),
            namedGroups = namedGroups
        )
    }
}
