package strling

import kotlinx.serialization.json.Json
import kotlinx.serialization.json.JsonElement
import kotlinx.serialization.json.JsonNull
import kotlinx.serialization.json.JsonObject
import kotlinx.serialization.json.JsonPrimitive
import kotlinx.serialization.json.intOrNull
import kotlinx.serialization.json.jsonArray
import kotlinx.serialization.json.jsonObject
import kotlinx.serialization.json.jsonPrimitive
import org.junit.jupiter.api.Assertions.assertEquals
import org.junit.jupiter.api.Assertions.assertFalse
import org.junit.jupiter.api.Assertions.assertNotNull
import org.junit.jupiter.api.Assertions.assertThrows
import org.junit.jupiter.api.Assertions.assertTrue
import org.junit.jupiter.api.DynamicTest
import org.junit.jupiter.api.Test
import org.junit.jupiter.api.TestFactory
import strling.core.IRGroup
import strling.core.IRLit
import strling.core.IRLook
import strling.core.IROp
import strling.core.IRQuant
import strling.core.STRlingCompilationError
import strling.emitters.Pcre2Emitter
import java.io.File

/**
 * Emitter Edges Conformance — Kotlin bridge.
 *
 * Drives the global pathological-AST fixture
 * `tests/conformance/inputs/emitter_edges/pathological.json` through
 * the Kotlin [Pcre2Emitter] and asserts each safety guard fires:
 *   1. Variable-Length Lookbehind Rejection — [STRlingCompilationError]
 *   2. AST Depth Limit Exceeded             — [STRlingCompilationError]
 *   3. ReDoS Risk Warning (`(a+)+`)         — non-fatal `STRlingWarning`
 *
 * The local [astToIR] mirrors the TypeScript bridge so the test targets
 * the emitter without coupling to the parser/compiler stages. Keep it
 * minimal — supporting only node types currently appearing in
 * `pathological.json` — so adapter omissions cannot mask emitter bugs by
 * silently dropping nodes.
 */
class EmitterEdgesConformanceTest {

    private val json = Json { ignoreUnknownKeys = true; isLenient = true }

    /** Climb from CWD until `toolchain.json` marks the workspace root. */
    private fun fixturePath(): File {
        var dir: File = File("").absoluteFile
        repeat(12) {
            if (File(dir, "toolchain.json").exists()) {
                return File(dir, "tests/conformance/inputs/emitter_edges/pathological.json")
            }
            dir = dir.parentFile ?: return@repeat
        }
        error("could not locate workspace root (toolchain.json) from ${File("").absolutePath}")
    }

    /** User-facing AST -> IR adapter. Extend only as new node types appear. */
    private fun astToIR(node: JsonObject): IROp {
        val type = node["type"]?.jsonPrimitive?.content ?: ""
        return when (type) {
            "Literal" -> IRLit(node["value"]?.jsonPrimitive?.content ?: "")
            "Group" -> IRGroup(false, astToIR(node["content"]!!.jsonObject), null, false)
            "Quantifier" -> {
                val child = astToIR(node["content"]!!.jsonObject)
                val minV = node["min"]?.jsonPrimitive?.intOrNull ?: 0
                val rawMax: JsonElement? = node["max"]
                val maxEl: JsonElement = when {
                    rawMax == null || rawMax is JsonNull -> JsonPrimitive("Inf")
                    rawMax is JsonPrimitive && rawMax.intOrNull != null -> rawMax
                    rawMax is JsonPrimitive -> JsonPrimitive("Inf")
                    else -> JsonPrimitive("Inf")
                }
                val mode = node["mode"]?.jsonPrimitive?.content ?: "Greedy"
                IRQuant(child, minV, maxEl, mode)
            }
            "Lookbehind" -> IRLook("Behind", false, astToIR(node["content"]!!.jsonObject))
            "NegativeLookbehind" -> IRLook("Behind", true, astToIR(node["content"]!!.jsonObject))
            "Lookahead" -> IRLook("Ahead", false, astToIR(node["content"]!!.jsonObject))
            "NegativeLookahead" -> IRLook("Ahead", true, astToIR(node["content"]!!.jsonObject))
            else -> error("astToIR: unsupported pathological AST node type \"$type\". Extend the adapter when new pathological vectors are added.")
        }
    }

    private fun expectedSubstring(prefixed: String): String {
        if (prefixed.startsWith("STRlingCompilationError:")) {
            return prefixed.removePrefix("STRlingCompilationError:").trim()
        }
        if (prefixed.startsWith("STRlingWarning")) {
            val idx = prefixed.indexOf(']')
            if (idx >= 0) return prefixed.substring(idx + 1).trimStart(':', ' ')
        }
        return prefixed
    }

    @TestFactory
    fun pathologicalCases(): List<DynamicTest> {
        val raw = fixturePath().readText()
        val root = json.parseToJsonElement(raw).jsonObject
        val cases = root["tests"]?.jsonArray ?: return emptyList()
        return cases.map { tcEl ->
            val tc = tcEl.jsonObject
            val name = tc["name"]?.jsonPrimitive?.content ?: "<unnamed>"
            DynamicTest.dynamicTest(name) {
                val ir = astToIR(tc["ast"]!!.jsonObject)
                val maxDepth = tc["depth_override_for_test"]?.jsonPrimitive?.intOrNull ?: 0

                val ee = tc["expected_error"]?.jsonPrimitive?.content
                val ew = tc["expected_warning"]?.jsonPrimitive?.content
                when {
                    ee != null -> {
                        val needle = expectedSubstring(ee)
                        val ex = assertThrows(STRlingCompilationError::class.java) {
                            Pcre2Emitter.emitWithDiagnostics(ir, null, maxDepth)
                        }
                        assertNotNull(ex.message)
                        assertTrue(
                            ex.message!!.contains(needle),
                            "[$name] error missing \"$needle\": ${ex.message}",
                        )
                    }
                    ew != null -> {
                        val needle = expectedSubstring(ew)
                        val result = Pcre2Emitter.emitWithDiagnostics(ir, null, maxDepth)
                        // Warnings must NOT abort emission — the pattern is still produced.
                        assertFalse(
                            result.pattern.isEmpty(),
                            "[$name] expected non-empty pattern when only a warning fires",
                        )
                        assertTrue(
                            result.warnings.any { it.code == "REDOS_RISK" && it.message.contains(needle) },
                            "[$name] missing REDOS_RISK warning containing \"$needle\"; got ${result.warnings}",
                        )
                    }
                    else -> error("[$name] declares neither expected_error nor expected_warning")
                }
            }
        }
    }

    @Test
    fun nonPathologicalEmitsNoWarnings() {
        val result = Pcre2Emitter.emitWithDiagnostics(IRLit("abc"))
        assertEquals("abc", result.pattern)
        assertTrue(result.warnings.isEmpty())
    }

    @Test
    fun depthCapDoesNotFireUnderLimit() {
        val deep = IRGroup(false, IRGroup(false, IRLit("ok"), null, false), null, false)
        val result = Pcre2Emitter.emitWithDiagnostics(deep, null, 5)
        assertTrue(result.warnings.isEmpty())
        assertTrue(result.pattern.contains("ok"))
    }
}
