package strling.core

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable
import kotlinx.serialization.json.JsonClassDiscriminator
import kotlinx.serialization.json.JsonElement

/**
 * STRling AST Node Definitions
 * 
 * This module defines the complete set of Abstract Syntax Tree (AST) node classes
 * that represent the parsed structure of STRling patterns.
 */

// ---- Flags container ----

/**
 * Container for regex flags/modifiers.
 */
@Serializable
data class Flags(
    val ignoreCase: Boolean = false,
    val multiline: Boolean = false,
    val dotAll: Boolean = false,
    val unicode: Boolean = false,
    val extended: Boolean = false
) {
    companion object {
        /**
         * Creates Flags from a string of flag letters.
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
                }
            }
            
            return Flags(ignoreCase, multiline, dotAll, unicode, extended)
        }
    }
}

// ---- Base node ----

@Serializable
@JsonClassDiscriminator("type")
sealed interface Node

@Serializable
@JsonClassDiscriminator("type")
sealed interface ClassItem

// ---- Concrete nodes ----

@Serializable
@SerialName("Alternation")
data class Alternation(val alternatives: List<Node>) : Node

@Serializable
@SerialName("Sequence")
data class Sequence(val parts: List<Node>) : Node

@Serializable
@SerialName("Literal")
data class Literal(val value: String) : Node, ClassItem

@Serializable
@SerialName("Dot")
class Dot : Node {
    override fun equals(other: Any?): Boolean = other is Dot
    override fun hashCode(): Int = "Dot".hashCode()
}

@Serializable
@SerialName("Anchor")
data class Anchor(val at: String) : Node

@Serializable
@SerialName("CharacterClass")
data class CharacterClass(val negated: Boolean, val members: List<ClassItem>) : Node

@Serializable
@SerialName("Range")
data class Range(val from: String, val to: String) : ClassItem

@Serializable
@SerialName("Escape")
data class Escape(val kind: String) : ClassItem

@Serializable
@SerialName("UnicodeProperty")
data class UnicodeProperty(
    val value: String,
    val name: String? = null,
    val negated: Boolean = false
) : ClassItem

@Serializable
@SerialName("Quantifier")
data class Quantifier(
    val target: Node,
    val min: Int,
    val max: JsonElement? = null,
    val greedy: Boolean,
    val lazy: Boolean,
    val possessive: Boolean
) : Node

@Serializable
@SerialName("Group")
data class Group(
    val capturing: Boolean,
    val body: Node,
    val name: String? = null,
    val atomic: Boolean? = null,
    val number: Int? = null,
    val expression: Node? = null
) : Node

@Serializable
@SerialName("Backreference")
data class Backreference(
    val index: Int? = null,
    val name: String? = null
) : Node

@Serializable
@SerialName("Lookahead")
data class Lookahead(val body: Node) : Node

@Serializable
@SerialName("NegativeLookahead")
data class NegativeLookahead(val body: Node) : Node

@Serializable
@SerialName("Lookbehind")
data class Lookbehind(val body: Node) : Node

@Serializable
@SerialName("NegativeLookbehind")
data class NegativeLookbehind(val body: Node) : Node
