package strling

import java.nio.file.Files
import java.nio.file.Path
import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertNull
import kotlin.test.assertTrue

class Essential5Test {
    @Test
    fun exposesAllFiveCanonicalRegistryIdentities() {
        val compatibilityFixture = essential5Fixture()
        assertEquals("1.0.0", Essential.REGISTRY_VERSION)
        assertEquals(
            listOf(
                "stdlib.date_time",
                "stdlib.email",
                "stdlib.ip",
                "stdlib.url",
                "stdlib.uuid",
            ),
            Essential.HELPER_IDS,
        )
        listOf("dateTime", "email", "ip", "url", "uuid").forEach {
            assertTrue(compatibilityFixture.contains("\"$it\""))
        }
    }

    @Test
    fun recordsLexicalHelpersWithoutHostSemanticValidation() {
        val helpers = listOf(
            Essential.dateTime(),
            Essential.email(),
            Essential.ip(),
            Essential.url(),
            Essential.uuid(),
        )

        helpers.forEachIndexed { index, pattern ->
            val request = pattern.buildRequest(compileProjection())
            @Suppress("UNCHECKED_CAST")
            val steps = request["steps"] as List<Map<String, Any?>>
            @Suppress("UNCHECKED_CAST")
            val arguments = steps.single()["arguments"] as Map<String, Any?>
            assertEquals("stdlib_helper", steps.single()["operation"])
            assertEquals(Essential.HELPER_IDS[index], arguments["helper_id"])
        }

        val ipRequest = Essential.ip().buildRequest(compileProjection())
        @Suppress("UNCHECKED_CAST")
        val ipSteps = ipRequest["steps"] as List<Map<String, Any?>>
        @Suppress("UNCHECKED_CAST")
        val ipArguments = ipSteps.single()["arguments"] as Map<String, Any?>
        @Suppress("UNCHECKED_CAST")
        val parameters = ipArguments["parameters"] as Map<String, Any?>
        assertTrue(parameters.containsKey("version"))
        assertNull(parameters["version"])
    }

    private fun compileProjection(): Map<String, Any?> = mapOf(
        "requested_outputs" to listOf("semantic"),
        "compiler_options" to mapOf(
            "partial_semantics" to "forbid",
            "diagnostic_policy" to mapOf("minimum_severity" to "hint"),
        ),
    )

    private fun essential5Fixture(): String {
        var current: Path? = Path.of("").toAbsolutePath()
        while (current != null) {
            val candidate = current.resolve("spec/stdlib/essential_5.json")
            if (Files.isRegularFile(candidate)) return Files.readString(candidate)
            current = current.parent
        }
        error("spec/stdlib/essential_5.json not found")
    }
}
