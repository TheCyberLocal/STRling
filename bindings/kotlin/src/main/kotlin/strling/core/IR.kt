package strling.core

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable
import kotlinx.serialization.json.JsonClassDiscriminator
import kotlinx.serialization.json.JsonElement

/**
 * STRling Intermediate Representation (IR) Node Definitions
 * 
 * This module defines the complete set of IR node classes that represent
 * language-agnostic regex constructs.
 */

// ---- Base IR operation ----

@Serializable
@JsonClassDiscriminator("ir")
sealed interface IROp

@Serializable
@JsonClassDiscriminator("ir")
sealed interface IRClassItem

// ---- IR concrete operations ----

@Serializable
@SerialName("Alt")
data class IRAlt(val branches: List<IROp>) : IROp

@Serializable
@SerialName("Seq")
data class IRSeq(val parts: List<IROp>) : IROp

@Serializable
@SerialName("Lit")
data class IRLit(val value: String) : IROp

@Serializable
@SerialName("Dot")
class IRDot : IROp {
    override fun equals(other: Any?): Boolean = other is IRDot
    override fun hashCode(): Int = "IRDot".hashCode()
}

@Serializable
@SerialName("Anchor")
data class IRAnchor(val at: String) : IROp

// ---- IR CharClass ----

@Serializable
@SerialName("CharClass")
data class IRCharClass(val negated: Boolean, val items: List<IRClassItem>) : IROp

@Serializable
@SerialName("Range")
data class IRClassRange(val from: String, val to: String) : IRClassItem

@Serializable
@SerialName("Char")
data class IRClassLiteral(val char: String) : IRClassItem

@Serializable
@SerialName("Esc")
data class IRClassEscape(val type: String, val property: String? = null) : IRClassItem

@Serializable
@SerialName("Quant")
data class IRQuant(
    val child: IROp,
    val min: Int,
    val max: JsonElement, // Int or "Inf"
    val mode: String
) : IROp

@Serializable
@SerialName("Group")
data class IRGroup(
    val capturing: Boolean,
    val body: IROp,
    val name: String? = null,
    val atomic: Boolean? = null
) : IROp

@Serializable
@SerialName("Backref")
data class IRBackref(
    val byIndex: Int? = null,
    val byName: String? = null
) : IROp

@Serializable
@SerialName("Look")
data class IRLook(
    val dir: String,
    val neg: Boolean,
    val body: IROp
) : IROp
