package strling

import com.strling.jvm.NativeClient

/** Immutable options for constructing canonical source CompileRequests. */
data class SourceCompileOptions(
    val sourceId: String = "src:kotlin.adapter",
    val frontendId: String = "semantic_strling",
    val frontendVersion: String? = null,
    val mediaType: String = if (frontendId == "legacy_regex") "text/x-regex" else "text/strling",
    val specificationVersion: String = "1.0-draft.1",
    val requestedOutputs: List<String>? = null,
    val compilerOptions: Map<String, Any?> = defaultCompilerOptions(),
    val targetProfileReference: Map<String, Any?>? = null,
    val targetProfile: Map<String, Any?>? = null,
) {
    companion object {
        @JvmStatic
        fun defaultCompilerOptions(): Map<String, Any?> = mapOf(
            "partial_semantics" to "forbid",
            "diagnostic_policy" to mapOf("minimum_severity" to "hint"),
        )
    }
}

/** Canonical compile-request conveniences over a supplied native client. */
class Compiler(private val client: NativeClient) {
    fun compile(request: Map<String, *>, targetProfile: Map<String, *>? = null): Any? =
        client.compile(request, targetProfile)

    fun check(request: Map<String, *>, targetProfile: Map<String, *>? = null): Any? =
        compile(request, targetProfile)

    /** Compatibility name returning canonical compile data, never a local AST. */
    fun parse(source: String, options: SourceCompileOptions = SourceCompileOptions()): Any? =
        client.compile(
            sourceCompileRequest(source, options, listOf("semantic")),
            options.targetProfile,
        )

    /** Compatibility name requesting a canonical TargetArtifact. */
    fun parseToArtifact(source: String, options: SourceCompileOptions): Any? {
        require(options.targetProfile != null && options.targetProfileReference != null) {
            "parseToArtifact requires an exact target profile and reference"
        }
        return client.compile(
            sourceCompileRequest(
                source,
                options,
                listOf("semantic", "portability", "target_artifact"),
            ),
            options.targetProfile,
        )
    }

    fun describe(): Any? = client.describe()

    fun inspectTargetProfile(targetProfile: Map<String, *>): Any? =
        client.inspectTargetProfile(targetProfile)

    companion object {
        @JvmStatic
        fun sourceCompileRequest(
            source: String,
            options: SourceCompileOptions = SourceCompileOptions(),
            fallbackOutputs: List<String> = listOf("semantic", "analysis"),
        ): Map<String, Any?> = mapOf(
            "contract_version" to "1.0.0",
            "specification_version" to options.specificationVersion,
            "input" to mapOf(
                "kind" to "source",
                "document" to mapOf(
                    "contract_version" to "1.0.0",
                    "source_id" to options.sourceId,
                    "specification_version" to options.specificationVersion,
                    "frontend" to mapOf(
                        "id" to options.frontendId,
                        "dialect_version" to (options.frontendVersion ?: options.specificationVersion),
                    ),
                    "content" to mapOf(
                        "kind" to "inline",
                        "encoding" to "utf-8",
                        "media_type" to options.mediaType,
                        "text" to source,
                    ),
                    "provenance" to mapOf("kind" to "authored"),
                ),
            ),
            "requested_outputs" to (options.requestedOutputs ?: fallbackOutputs),
            "compiler_options" to options.compilerOptions,
        ).let { request ->
            options.targetProfileReference?.let {
                request + ("target_profile" to it)
            } ?: request
        }
    }
}
