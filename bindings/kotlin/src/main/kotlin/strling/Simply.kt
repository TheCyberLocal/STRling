package strling

import com.strling.jvm.NativeClient

/** Invalid host-side recipe construction; canonical failures remain values. */
class STRlingError(message: String) : IllegalArgumentException(message)

/** Records host-neutral Simply 1.1 operations without evaluating semantics. */
class SimplyBuilder(
    private val identityNamespace: String,
    private val specificationVersion: String = "1.0-draft.1",
    private val semanticOptions: Map<String, *> = defaultSemanticOptions(),
) {
    private val owner = Any()
    private val steps = mutableListOf<Map<String, Any?>>()

    class Value internal constructor(val stepId: String, internal val owner: Any)

    fun empty(stepId: String): Value = append(stepId, "empty", emptyMap<String, Any?>())
    fun literal(stepId: String, text: String): Value =
        append(stepId, "literal", mapOf("text" to text))
    fun wildcard(stepId: String): Value = append(stepId, "wildcard", emptyMap<String, Any?>())
    fun characterSet(stepId: String, members: List<Map<String, *>>, negated: Boolean): Value =
        append(stepId, "character_set", mapOf("negated" to negated, "members" to members))
    fun sequence(stepId: String, values: List<Value>): Value =
        append(stepId, "sequence", mapOf("values" to values.map(::stepId)))
    fun alternation(stepId: String, values: List<Value>): Value =
        append(stepId, "alternation", mapOf("values" to values.map(::stepId)))
    fun capture(stepId: String, captureKey: String, value: Value, name: String? = null): Value =
        append(
            stepId,
            "capture",
            mapOf("value" to stepId(value), "capture_key" to captureKey) +
                (name?.let { mapOf("name" to it) } ?: emptyMap<String, String>()),
        )
    fun backreference(stepId: String, captureKey: String): Value =
        append(stepId, "backreference", mapOf("capture_key" to captureKey))
    fun position(stepId: String, position: String): Value =
        append(stepId, "position", mapOf("position" to position))
    fun lookaround(
        stepId: String,
        direction: String,
        polarity: String,
        value: Value,
    ): Value = append(
        stepId,
        "lookaround",
        mapOf("value" to stepId(value), "direction" to direction, "polarity" to polarity),
    )
    fun atomic(stepId: String, value: Value): Value =
        append(stepId, "atomic", mapOf("value" to stepId(value)))
    fun repeat(stepId: String, value: Value, min: Int, max: Int?, mode: String): Value =
        append(
            stepId,
            "repeat",
            mapOf("value" to stepId(value), "min" to min, "max" to max, "mode" to mode),
        )
    fun stdlibHelper(stepId: String, helperId: String, parameters: Map<String, *>): Value =
        append(
            stepId,
            "stdlib_helper",
            mapOf("helper_id" to helperId, "parameters" to parameters),
        )

    fun buildRequest(root: Value, compileProjection: Map<String, *>): Map<String, Any?> = mapOf(
        "protocol_version" to "1.1.0",
        "contract_version" to "1.0.0",
        "specification_version" to specificationVersion,
        "identity_namespace" to identityNamespace,
        "semantic_options" to semanticOptions.toMap(),
        "steps" to steps.toList(),
        "root_step_id" to stepId(root),
        "compile" to compileProjection.toMap(),
    )

    private fun append(stepId: String, operation: String, arguments: Map<String, *>): Value {
        steps += mapOf("step_id" to stepId, "operation" to operation, "arguments" to arguments)
        return Value(stepId, owner)
    }

    private fun stepId(value: Value): String {
        if (value.owner !== owner) {
            throw STRlingError("Simply values belong to exactly one builder")
        }
        return value.stepId
    }

    companion object {
        @JvmStatic
        fun defaultSemanticOptions(): Map<String, String> = mapOf(
            "case_matching" to "sensitive",
            "text_model" to "unicode_scalar_values",
            "builtin_character_domain" to "unicode",
            "wildcard_line_terminators" to "exclude",
        )
    }
}

/** Immutable recipe that records canonical Simply operations on demand. */
class Pattern internal constructor(
    private val repetition: Repetition? = null,
    private val recipe: (Context) -> SimplyBuilder.Value,
) {
    internal class Context(val builder: SimplyBuilder) {
        private var sequence = 0
        fun next(prefix: String): String {
            sequence += 1
            return "$prefix-$sequence"
        }
    }

    internal data class Repetition(
        val value: Pattern,
        val min: Int,
        val max: Int?,
    )

    internal fun record(context: Context): SimplyBuilder.Value = recipe(context)

    fun repeat(min: Int, max: Int? = min): Pattern {
        require(min >= 0 && (max == null || max >= min)) {
            "repetition bounds must be non-negative and ordered"
        }
        val source = this
        return Pattern(Repetition(source, min, max)) { context ->
                context.builder.repeat(
                    context.next("repeat"),
                    source.record(context),
                    min,
                    max,
                    "greedy",
                )
            }
    }

    fun may(): Pattern = repeat(0, 1)

    fun lazy(): Pattern {
        val selected = repetition ?: throw STRlingError("lazy requires a repeated pattern")
        return Pattern(selected) { context ->
                context.builder.repeat(
                    context.next("repeat"),
                    selected.value.record(context),
                    selected.min,
                    selected.max,
                    "lazy",
                )
            }
    }

    fun asCapture(): Pattern {
        val source = this
        return Pattern { context ->
            context.builder.capture(
                context.next("capture"),
                context.next("capture-key"),
                source.record(context),
            )
        }
    }

    fun asGroup(name: String): Pattern {
        require(name.isNotEmpty()) { "capture group name cannot be empty" }
        val source = this
        return Pattern { context ->
            context.builder.capture(
                context.next("capture"),
                name,
                source.record(context),
                name,
            )
        }
    }

    fun buildRequest(
        compileProjection: Map<String, *>,
        identityNamespace: String = "kotlin-simply",
        semanticOptions: Map<String, *> = SimplyBuilder.defaultSemanticOptions(),
    ): Map<String, Any?> {
        val builder = SimplyBuilder(identityNamespace, semanticOptions = semanticOptions)
        val context = Context(builder)
        return builder.buildRequest(record(context), compileProjection)
    }

    fun compile(
        client: NativeClient,
        compileProjection: Map<String, *>,
        targetProfile: Map<String, *>? = null,
    ): Any? = client.simplyCompile(buildRequest(compileProjection), targetProfile)

    fun exec(@Suppress("UNUSED_PARAMETER") text: String): Nothing = throw STRlingError(
        "Pattern.exec was retired: canonical adapters do not simulate runtime regex execution",
    )

    override fun toString(): String = throw STRlingError(
        "implicit regex rendering was retired: compile through the canonical adapter",
    )

    companion object {
        internal fun stdlibHelper(helperId: String, parameters: Map<String, *>): Pattern =
            Pattern { context ->
                context.builder.stdlibHelper(
                    context.next("stdlib"),
                    helperId,
                    parameters,
                )
            }
    }
}

/** Idiomatic Kotlin constructors for canonical Simply recipes. */
object Simply {
    fun empty(): Pattern = Pattern { it.builder.empty(it.next("empty")) }

    fun literal(text: String): Pattern = if (text.isEmpty()) {
        empty()
    } else {
        Pattern { it.builder.literal(it.next("literal"), text) }
    }

    fun anything(): Pattern = Pattern { it.builder.wildcard(it.next("wildcard")) }

    fun digit(): Pattern = builtin("digit")
    fun word(): Pattern = builtin("word")
    fun whitespace(): Pattern = builtin("whitespace")

    fun between(start: Char, end: Char): Pattern {
        require(!start.isSurrogate() && !end.isSurrogate() && start <= end) {
            "character range must be ordered Unicode scalars"
        }
        return characterSet(
            listOf(mapOf("kind" to "range", "start" to start.toString(), "end" to end.toString())),
        )
    }

    fun anyOfChars(characters: String): Pattern {
        require(characters.isNotEmpty()) { "character set cannot be empty" }
        return characterSet(
            characters.codePoints().toArray().map { codePoint ->
                mapOf(
                    "kind" to "literal",
                    "value" to String(Character.toChars(codePoint)),
                )
            },
        )
    }

    fun merge(vararg values: Any): Pattern {
        val patterns = patterns(*values)
        if (patterns.size == 1) return patterns.single()
        return Pattern { context ->
            context.builder.sequence(context.next("sequence"), patterns.map { it.record(context) })
        }
    }

    fun anyOf(vararg values: Any): Pattern {
        val patterns = patterns(*values)
        return Pattern { context ->
            context.builder.alternation(
                context.next("alternation"),
                patterns.map { it.record(context) },
            )
        }
    }

    fun may(vararg values: Any): Pattern = merge(*values).may()
    fun capture(vararg values: Any): Pattern = merge(*values).asCapture()
    fun group(name: String, vararg values: Any): Pattern = merge(*values).asGroup(name)
    fun ref(captureKey: String): Pattern = Pattern {
        it.builder.backreference(it.next("backreference"), captureKey)
    }
    fun startsWith(vararg values: Any): Pattern = merge(position("start_of_text"), merge(*values))
    fun endsWith(vararg values: Any): Pattern = merge(merge(*values), position("end_of_text"))
    fun followedBy(vararg values: Any): Pattern = lookaround("ahead", "positive", merge(*values))
    fun notFollowedBy(vararg values: Any): Pattern = lookaround("ahead", "negative", merge(*values))
    fun precededBy(vararg values: Any): Pattern = lookaround("behind", "positive", merge(*values))
    fun notPrecededBy(vararg values: Any): Pattern =
        lookaround("behind", "negative", merge(*values))
    fun atomic(vararg values: Any): Pattern {
        val pattern = merge(*values)
        return Pattern { it.builder.atomic(it.next("atomic"), pattern.record(it)) }
    }

    private fun builtin(name: String): Pattern = characterSet(
        listOf(
            mapOf(
                "kind" to "builtin",
                "name" to name,
                "domain" to "target_native",
                "negated" to false,
            ),
        ),
    )

    private fun characterSet(members: List<Map<String, *>>): Pattern = Pattern {
        it.builder.characterSet(it.next("character-set"), members, false)
    }

    private fun position(position: String): Pattern = Pattern {
        it.builder.position(it.next("position"), position)
    }

    private fun lookaround(direction: String, polarity: String, value: Pattern): Pattern = Pattern {
        it.builder.lookaround(it.next("lookaround"), direction, polarity, value.record(it))
    }

    private fun patterns(vararg values: Any): List<Pattern> {
        require(values.isNotEmpty()) { "at least one Pattern or literal string is required" }
        return values.map { value ->
            when (value) {
                is Pattern -> value
                is String -> literal(value)
                else -> throw STRlingError("expected a Pattern or literal string")
            }
        }
    }
}
