package strling.core

/**
 * STRling Intermediate Representation (IR) Node Definitions
 * 
 * This module defines the complete set of IR node classes that represent
 * language-agnostic regex constructs. The IR serves as an intermediate layer
 * between the parsed AST and the target-specific emitters (e.g., PCRE2).
 * 
 * IR nodes are designed to be:
 *   - Simple and composable
 *   - Easy to serialize (via toDict methods)
 *   - Independent of any specific regex flavor
 *   - Optimized for transformation and analysis
 * 
 * Each IR node corresponds to a fundamental regex operation (alternation,
 * sequencing, character classes, quantification, etc.) and can be serialized
 * to a dictionary representation for further processing or debugging.
 */

// ---- Base IR operation ----

/**
 * Base class for all IR operations.
 * 
 * All IR nodes extend this sealed class and must implement the toDict() method
 * for serialization to a dictionary representation.
 */
sealed class IROp {
    /**
     * Serialize the IR node to a dictionary representation.
     * 
     * @return The dictionary representation of this IR node
     */
    abstract fun toDict(): Map<String, Any>
}

// ---- IR concrete operations ----

/**
 * Represents an alternation (OR) operation in the IR.
 * 
 * Matches any one of the provided branches. Equivalent to the | operator
 * in traditional regex syntax.
 */
data class IRAlt(val branches: List<IROp>) : IROp() {
    override fun toDict(): Map<String, Any> {
        return mapOf(
            "ir" to "Alt",
            "branches" to branches.map { it.toDict() }
        )
    }
}

/**
 * Represents a sequence of IR operations.
 * 
 * Matches all parts in order. This is the concatenation operation.
 */
data class IRSeq(val parts: List<IROp>) : IROp() {
    override fun toDict(): Map<String, Any> {
        return mapOf(
            "ir" to "Seq",
            "parts" to parts.map { it.toDict() }
        )
    }
}

/**
 * Represents a literal string in the IR.
 * 
 * Matches the exact character sequence specified by value.
 */
data class IRLit(val value: String) : IROp() {
    override fun toDict(): Map<String, Any> {
        return mapOf(
            "ir" to "Lit",
            "value" to value
        )
    }
}

/**
 * Represents the dot metacharacter in the IR.
 * 
 * Matches any character (behavior depends on flags).
 */
class IRDot : IROp() {
    override fun toDict(): Map<String, Any> {
        return mapOf("ir" to "Dot")
    }
    
    override fun equals(other: Any?): Boolean = other is IRDot
    override fun hashCode(): Int = "IRDot".hashCode()
}

/**
 * Represents an anchor in the IR.
 * 
 * Anchors match positions rather than characters.
 * 
 * @property at The anchor type
 */
data class IRAnchor(val at: String) : IROp() {
    override fun toDict(): Map<String, Any> {
        return mapOf(
            "ir" to "Anchor",
            "at" to at
        )
    }
}

// ---- IR CharClass ----

/**
 * Base class for IR character class items.
 */
sealed class IRClassItem {
    /**
     * Serialize the class item to a dictionary representation.
     * 
     * @return The dictionary representation of this class item
     */
    abstract fun toDict(): Map<String, Any>
}

/**
 * Represents a character range in an IR character class.
 * 
 * @property fromCh The starting character of the range
 * @property toCh The ending character of the range
 */
data class IRClassRange(val fromCh: String, val toCh: String) : IRClassItem() {
    override fun toDict(): Map<String, Any> {
        return mapOf(
            "ir" to "Range",
            "from" to fromCh,
            "to" to toCh
        )
    }
}

/**
 * Represents a literal character in an IR character class.
 * 
 * @property ch The literal character
 */
data class IRClassLiteral(val ch: String) : IRClassItem() {
    override fun toDict(): Map<String, Any> {
        return mapOf(
            "ir" to "Char",
            "char" to ch
        )
    }
}

/**
 * Represents an escape sequence in an IR character class.
 * 
 * @property type The escape type
 * @property property The Unicode property name (for p and P escapes)
 */
data class IRClassEscape(val type: String, val property: String? = null) : IRClassItem() {
    override fun toDict(): Map<String, Any> {
        val d = mutableMapOf<String, Any>(
            "ir" to "Esc",
            "type" to type
        )
        if (property != null) {
            d["property"] = property
        }
        return d
    }
}

/**
 * Represents a character class in the IR.
 * 
 * @property negated Whether the class is negated
 * @property items The list of items in the class
 */
data class IRCharClass(val negated: Boolean, val items: List<IRClassItem>) : IROp() {
    override fun toDict(): Map<String, Any> {
        return mapOf(
            "ir" to "CharClass",
            "negated" to negated,
            "items" to items.map { it.toDict() }
        )
    }
}

/**
 * Represents a quantifier in the IR.
 * 
 * @property child The IR operation to be quantified
 * @property min Minimum number of repetitions
 * @property max Maximum number of repetitions (Int or "Inf")
 * @property mode The quantifier mode: "Greedy", "Lazy", or "Possessive"
 */
data class IRQuant(
    val child: IROp,
    val min: Int,
    val max: Any,  // Int or "Inf"
    val mode: String
) : IROp() {
    override fun toDict(): Map<String, Any> {
        return mapOf(
            "ir" to "Quant",
            "child" to child.toDict(),
            "min" to min,
            "max" to max,
            "mode" to mode
        )
    }
}

/**
 * Represents a group in the IR.
 * 
 * @property capturing Whether this is a capturing group
 * @property body The content of the group
 * @property name The name of the group (for named captures)
 * @property atomic Whether this is an atomic group
 */
data class IRGroup(
    val capturing: Boolean,
    val body: IROp,
    val name: String? = null,
    val atomic: Boolean? = null
) : IROp() {
    override fun toDict(): Map<String, Any> {
        val d = mutableMapOf<String, Any>(
            "ir" to "Group",
            "capturing" to capturing,
            "body" to body.toDict()
        )
        if (name != null) {
            d["name"] = name
        }
        if (atomic != null) {
            d["atomic"] = atomic
        }
        return d
    }
}

/**
 * Represents a backreference in the IR.
 * 
 * @property byIndex The index of the capture group to reference
 * @property byName The name of the capture group to reference
 */
data class IRBackref(
    val byIndex: Int? = null,
    val byName: String? = null
) : IROp() {
    override fun toDict(): Map<String, Any> {
        val d = mutableMapOf<String, Any>("ir" to "Backref")
        if (byIndex != null) {
            d["byIndex"] = byIndex
        }
        if (byName != null) {
            d["byName"] = byName
        }
        return d
    }
}

/**
 * Represents a lookahead or lookbehind assertion in the IR.
 * 
 * @property dir The direction: "Ahead" or "Behind"
 * @property neg Whether this is a negative assertion
 * @property body The content of the assertion
 */
data class IRLook(
    val dir: String,
    val neg: Boolean,
    val body: IROp
) : IROp() {
    override fun toDict(): Map<String, Any> {
        return mapOf(
            "ir" to "Look",
            "dir" to dir,
            "neg" to neg,
            "body" to body.toDict()
        )
    }
}
