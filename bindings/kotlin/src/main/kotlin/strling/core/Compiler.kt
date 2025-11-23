package strling.core

import kotlinx.serialization.json.JsonPrimitive

object Compiler {
    fun compile(node: Node): IROp {
        return when (node) {
            is Alternation -> IRAlt(node.alternatives.map { compile(it) })
            is Sequence -> {
                val compiledParts = node.parts.map { compile(it) }
                val mergedParts = mutableListOf<IROp>()
                for (part in compiledParts) {
                    if (mergedParts.isNotEmpty() && mergedParts.last() is IRLit && part is IRLit) {
                        val last = mergedParts.removeAt(mergedParts.lastIndex) as IRLit
                        mergedParts.add(IRLit(last.value + part.value))
                    } else {
                        mergedParts.add(part)
                    }
                }
                if (mergedParts.size == 1) {
                    mergedParts[0]
                } else {
                    IRSeq(mergedParts)
                }
            }
            is Literal -> IRLit(node.value)
            is Dot -> IRDot()
            is Anchor -> {
                val at = if (node.at == "NonWordBoundary") "NotWordBoundary" else node.at
                IRAnchor(at)
            }
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
            is Group -> {
                val atomic = if (node.atomic == true) true else null
                IRGroup(node.capturing, compile(node.body), node.name, atomic)
            }
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
            is Escape -> {
                val type = when (item.kind) {
                    "digit" -> "d"
                    "space" -> "s"
                    "word" -> "w"
                    "not-digit" -> "D"
                    "not-space" -> "S"
                    "not-word" -> "W"
                    else -> item.kind
                }
                IRClassEscape(type)
            }
            is Literal -> IRClassLiteral(item.value)
            is UnicodeProperty -> {
                val type = if (item.negated) "P" else "p"
                IRClassEscape(type, item.value)
            }
        }
    }
}
