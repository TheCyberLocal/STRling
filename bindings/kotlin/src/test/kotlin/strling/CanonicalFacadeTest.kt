package strling

import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertFailsWith
import kotlin.test.assertFalse
import kotlin.test.assertNull
import kotlin.test.assertTrue

class CanonicalFacadeTest {
    @Test
    fun sourceRequestUsesCanonicalContractsAndNoAmbientTarget() {
        val request = Compiler.sourceCompileRequest("literal \"hello\"")

        assertEquals("1.0.0", request["contract_version"])
        assertEquals(listOf("semantic", "analysis"), request["requested_outputs"])
        assertFalse(request.containsKey("target_profile"))
    }

    @Test
    fun exactTargetReferenceIsProjectedWithoutSelectingIt() {
        val reference = mapOf<String, Any?>("profile_id" to "pcre2-10.43")
        val request = Compiler.sourceCompileRequest(
            "literal \"x\"",
            SourceCompileOptions(targetProfileReference = reference),
            listOf("semantic"),
        )

        assertEquals(reference, request["target_profile"])
    }

    @Test
    fun simplyRecordsProtocolOperationsInsteadOfRenderingRegex() {
        val pattern = Simply.merge(
            Simply.startsWith("ab"),
            Simply.digit().repeat(2),
            Simply.endsWith(Essential.email()),
        )
        val request = pattern.buildRequest(compileProjection())

        assertEquals("1.1.0", request["protocol_version"])
        @Suppress("UNCHECKED_CAST")
        val steps = request["steps"] as List<Map<String, Any?>>
        assertTrue(steps.any { it["operation"] == "stdlib_helper" })
        assertFailsWith<STRlingError> { pattern.toString() }
        assertFailsWith<STRlingError> { pattern.exec("input") }
    }

    @Test
    fun lexicalHelperRecordsNullDefaultInsteadOfSemanticValidation() {
        val request = Essential.ip().buildRequest(compileProjection())
        @Suppress("UNCHECKED_CAST")
        val steps = request["steps"] as List<Map<String, Any?>>
        @Suppress("UNCHECKED_CAST")
        val arguments = steps.single()["arguments"] as Map<String, Any?>
        @Suppress("UNCHECKED_CAST")
        val parameters = arguments["parameters"] as Map<String, Any?>

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
}
