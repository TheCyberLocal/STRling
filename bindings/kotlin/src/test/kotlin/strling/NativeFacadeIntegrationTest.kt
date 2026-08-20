package strling

import com.strling.jvm.NativeClient
import com.fasterxml.jackson.databind.ObjectMapper
import java.nio.file.Paths
import kotlin.io.path.createDirectories
import kotlin.test.Test
import kotlin.test.assertTrue
import org.junit.jupiter.api.Assumptions

class NativeFacadeIntegrationTest {
    @Test
    fun sourceAndSimplyFacadesDelegateToTheSameNativeClient() {
        val configured = System.getenv("STRLING_NATIVE_LIBRARY")
        Assumptions.assumeTrue(
            !configured.isNullOrEmpty(),
            "STRLING_NATIVE_LIBRARY is required for governed integration execution",
        )
        NativeClient.load(Paths.get(configured).toAbsolutePath().normalize()).use { client ->
            val describe = client.describe()
            val compile = Compiler(client).parse(
                "literal \"hello\"",
                SourceCompileOptions(sourceId = "src:jvm.parity"),
            )
            val simply = client.simplyCompile(
                Essential.ip().buildRequest(
                    compileProjection(),
                    identityNamespace = "jvm-parity",
                ),
            )
            assertTrue(compile is Map<*, *>)
            assertTrue(simply is Map<*, *>)
            writeEvidence(describe, compile, simply)
        }
    }

    private fun compileProjection(): Map<String, Any?> = mapOf(
        "requested_outputs" to listOf("semantic"),
        "compiler_options" to mapOf(
            "partial_semantics" to "forbid",
            "diagnostic_policy" to mapOf("minimum_severity" to "hint"),
        ),
    )

    private fun writeEvidence(describe: Any?, compile: Any?, simply: Any?) {
        val configured = System.getenv("STRLING_JVM_EVIDENCE_DIR")
        if (configured.isNullOrEmpty()) return
        val directory = Paths.get(configured).resolve("kotlin").createDirectories()
        val mapper = ObjectMapper()
        mapper.writeValue(directory.resolve("describe.json").toFile(), describe)
        mapper.writeValue(directory.resolve("compile.json").toFile(), compile)
        mapper.writeValue(directory.resolve("simply.json").toFile(), simply)
    }
}
