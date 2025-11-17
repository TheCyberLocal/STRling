package strling.core

/**
 * STRling AST Node Definitions
 * 
 * This module defines the complete set of Abstract Syntax Tree (AST) node classes
 * that represent the parsed structure of STRling patterns. The AST is the direct
 * output of the parser and represents the syntactic structure of the pattern before
 * optimization and lowering to IR.
 * 
 * AST nodes are designed to:
 *   - Closely mirror the source pattern syntax
 *   - Be easily serializable to the Base TargetArtifact schema
 *   - Provide a clean separation between parsing and compilation
 *   - Support multiple target regex flavors through the compilation pipeline
 * 
 * Each AST node type corresponds to a syntactic construct in the STRling DSL
 * (alternation, sequencing, character classes, anchors, etc.) and can be
 * serialized to a dictionary representation for debugging or storage.
 */

// ---- Flags container ----

/**
 * Container for regex flags/modifiers.
 * 
 * Flags control the behavior of pattern matching (case sensitivity, multiline
 * mode, etc.). This class encapsulates all standard regex flags.
 */
data class Flags(
    val ignoreCase: Boolean = false,
    val multiline: Boolean = false,
    val dotAll: Boolean = false,
    val unicode: Boolean = false,
    val extended: Boolean = false
) {
    /**
     * Serializes the flags to a dictionary representation.
     * 
     * @return Map containing all flag values
     */
    fun toDict(): Map<String, Boolean> {
        return mapOf(
            "ignoreCase" to ignoreCase,
            "multiline" to multiline,
            "dotAll" to dotAll,
            "unicode" to unicode,
            "extended" to extended
        )
    }
    
    companion object {
        /**
         * Creates Flags from a string of flag letters.
         * 
         * @param letters String containing flag letters (i, m, s, u, x)
         * @return A new Flags instance with the specified flags enabled
         */
        fun fromLetters(letters: String): Flags {
            var ignoreCase = false
            var multiline = false
            var dotAll = false
            var unicode = false
            var extended = false
            
            val cleaned = letters.replace(",", "").replace(" ", "")
            for (ch in cleaned) {
                when (ch) {
                    'i' -> ignoreCase = true
                    'm' -> multiline = true
                    's' -> dotAll = true
                    'u' -> unicode = true
                    'x' -> extended = true
                    else -> {
                        // Unknown flags are ignored at parser stage; may be warned later
                    }
                }
            }
            
            return Flags(ignoreCase, multiline, dotAll, unicode, extended)
        }
    }
}

// ---- Base node ----

/**
 * Base class for all AST nodes.
 * 
 * All AST nodes extend this sealed class and must implement the toDict() method
 * for serialization to a dictionary representation.
 */
sealed class Node {
    /**
     * Serialize the AST node to a dictionary representation.
     * 
     * @return The dictionary representation of this AST node
     */
    abstract fun toDict(): Map<String, Any>
}

// ---- Concrete nodes matching Base Schema ----

/**
 * Represents an alternation (OR) operation in the AST.
 * 
 * Matches any one of the provided branches. Equivalent to the | operator
 * in traditional regex syntax.
 */
data class Alt(val branches: List<Node>) : Node() {
    override fun toDict(): Map<String, Any> {
        return mapOf(
            "kind" to "Alt",
            "branches" to branches.map { it.toDict() }
        )
    }
}

/**
 * Represents a sequence of nodes in the AST.
 * 
 * Matches all parts in order. This is the concatenation operation.
 */
data class Seq(val parts: List<Node>) : Node() {
    override fun toDict(): Map<String, Any> {
        return mapOf(
            "kind" to "Seq",
            "parts" to parts.map { it.toDict() }
        )
    }
}

/**
 * Represents a literal string in the AST.
 * 
 * Matches the exact character sequence specified by value.
 */
data class Lit(val value: String) : Node() {
    override fun toDict(): Map<String, Any> {
        return mapOf(
            "kind" to "Lit",
            "value" to value
        )
    }
}

/**
 * Represents the dot metacharacter in the AST.
 * 
 * Matches any character (behavior depends on flags).
 */
class Dot : Node() {
    override fun toDict(): Map<String, Any> {
        return mapOf("kind" to "Dot")
    }
    
    override fun equals(other: Any?): Boolean = other is Dot
    override fun hashCode(): Int = "Dot".hashCode()
}

/**
 * Represents an anchor in the AST.
 * 
 * Anchors match positions rather than characters.
 * 
 * @property at The anchor type: "Start", "End", "WordBoundary", "NotWordBoundary",
 *              or Absolute* variants
 */
data class Anchor(val at: String) : Node() {
    override fun toDict(): Map<String, Any> {
        return mapOf(
            "kind" to "Anchor",
            "at" to at
        )
    }
}

// ---- CharClass ----

/**
 * Base class for character class items.
 */
sealed class ClassItem {
    /**
     * Serialize the class item to a dictionary representation.
     * 
     * @return The dictionary representation of this class item
     */
    abstract fun toDict(): Map<String, Any>
}

/**
 * Represents a character range in a character class.
 * 
 * @property fromCh The starting character of the range
 * @property toCh The ending character of the range
 */
data class ClassRange(val fromCh: String, val toCh: String) : ClassItem() {
    override fun toDict(): Map<String, Any> {
        return mapOf(
            "kind" to "Range",
            "from" to fromCh,
            "to" to toCh
        )
    }
}

/**
 * Represents a literal character in a character class.
 * 
 * @property ch The literal character
 */
data class ClassLiteral(val ch: String) : ClassItem() {
    override fun toDict(): Map<String, Any> {
        return mapOf(
            "kind" to "Char",
            "char" to ch
        )
    }
}

/**
 * Represents an escape sequence in a character class.
 * 
 * @property type The escape type: d, D, w, W, s, S, p, P
 * @property property The Unicode property name (for p and P escapes)
 */
data class ClassEscape(val type: String, val property: String? = null) : ClassItem() {
    override fun toDict(): Map<String, Any> {
        val data = mutableMapOf<String, Any>(
            "kind" to "Esc",
            "type" to type
        )
        if (type in listOf("p", "P") && property != null) {
            data["property"] = property
        }
        return data
    }
}

/**
 * Represents a character class in the AST.
 * 
 * @property negated Whether the class is negated (matches anything NOT in the class)
 * @property items The list of items (ranges, literals, escapes) in the class
 */
data class CharClass(val negated: Boolean, val items: List<ClassItem>) : Node() {
    override fun toDict(): Map<String, Any> {
        return mapOf(
            "kind" to "CharClass",
            "negated" to negated,
            "items" to items.map { it.toDict() }
        )
    }
}

/**
 * Represents a quantifier in the AST.
 * 
 * @property child The node to be quantified
 * @property min Minimum number of repetitions
 * @property max Maximum number of repetitions ("Inf" for unbounded)
 * @property mode The quantifier mode: "Greedy", "Lazy", or "Possessive"
 */
data class Quant(
    val child: Node,
    val min: Int,
    val max: Any,  // Int or "Inf"
    val mode: String
) : Node() {
    override fun toDict(): Map<String, Any> {
        return mapOf(
            "kind" to "Quant",
            "child" to child.toDict(),
            "min" to min,
            "max" to max,
            "mode" to mode
        )
    }
}

/**
 * Represents a group in the AST.
 * 
 * @property capturing Whether this is a capturing group
 * @property body The content of the group
 * @property name The name of the group (for named captures)
 * @property atomic Whether this is an atomic group (extension)
 */
data class Group(
    val capturing: Boolean,
    val body: Node,
    val name: String? = null,
    val atomic: Boolean? = null
) : Node() {
    override fun toDict(): Map<String, Any> {
        val data = mutableMapOf<String, Any>(
            "kind" to "Group",
            "capturing" to capturing,
            "body" to body.toDict()
        )
        if (name != null) {
            data["name"] = name
        }
        if (atomic != null) {
            data["atomic"] = atomic
        }
        return data
    }
}

/**
 * Represents a backreference in the AST.
 * 
 * @property byIndex The index of the capture group to reference
 * @property byName The name of the capture group to reference
 */
data class Backref(
    val byIndex: Int? = null,
    val byName: String? = null
) : Node() {
    override fun toDict(): Map<String, Any> {
        val data = mutableMapOf<String, Any>("kind" to "Backref")
        if (byIndex != null) {
            data["byIndex"] = byIndex
        }
        if (byName != null) {
            data["byName"] = byName
        }
        return data
    }
}

/**
 * Represents a lookahead or lookbehind assertion in the AST.
 * 
 * @property dir The direction: "Ahead" or "Behind"
 * @property neg Whether this is a negative assertion
 * @property body The content of the assertion
 */
data class Look(
    val dir: String,
    val neg: Boolean,
    val body: Node
) : Node() {
    override fun toDict(): Map<String, Any> {
        return mapOf(
            "kind" to "Look",
            "dir" to dir,
            "neg" to neg,
            "body" to body.toDict()
        )
    }
}
