package strling.core

import kotlinx.serialization.json.JsonPrimitive

object Compiler {
    fun compile(node: Node): IROp {
        return when (node) {
            is Alternation -> IRAlt(node.alternatives.map { compile(it) })
            is Sequence -> IRSeq(node.parts.map { compile(it) })
            is Literal -> IRLit(node.value)
            is Dot -> IRDot()
            is Anchor -> IRAnchor(node.at)
            is CharacterClass -> IRCharClass(node.negated, node.members.map { compileClassItem(it) })
            is Quantifier -> {
                val mode = when {
                    node.possessive -> "Possessive"
                    node.lazy -> "Lazy"
                    else -> "Greedy"
                }
                // If max is null, it means infinity ("Inf")
                val maxVal = node.max ?: JsonPrimitive("Inf")
                IRQuant(compile(node.target), node.min, maxVal, mode)
            }
            is Group -> IRGroup(node.capturing, compile(node.body), node.name, node.atomic)
            is Backreference -> IRBackref(node.index, node.name)
            is Lookahead -> IRLook("Ahead", false, compile(node.body))
            is NegativeLookahead -> IRLook("Ahead", true, compile(node.body))
            is Lookbehind -> IRLook("Behind", false, compile(node.body))
            is NegativeLookbehind -> IRLook("Behind", true, compile(node.body))
        }
    }

    private fun compileClassItem(item: ClassItem): IRClassItem {
        return when (item) {
            is Range -> IRClassRange(item.from, item.to)
            is Escape -> IRClassEscape(item.kind)
            is Literal -> IRClassLiteral(item.value)
            is UnicodeProperty -> {
                val type = if (item.negated) "P" else "p"
                IRClassEscape(type, item.value)
            }
        }
    }
}
