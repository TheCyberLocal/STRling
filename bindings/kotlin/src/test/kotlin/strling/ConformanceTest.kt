package strling

import kotlinx.serialization.json.Json
import kotlinx.serialization.json.decodeFromJsonElement
import kotlinx.serialization.json.jsonObject
import kotlinx.serialization.json.jsonPrimitive
import org.junit.jupiter.api.Assertions.assertEquals
import org.junit.jupiter.api.Assertions.assertTrue
import org.junit.jupiter.api.TestFactory
import org.junit.jupiter.api.DynamicTest
import java.io.File
import strling.core.Compiler
import strling.core.Node
import strling.core.IROp
import strling.core.Parser
import strling.core.STRlingParseError

class ConformanceTest {

    private val json = Json {
        ignoreUnknownKeys = true
        prettyPrint = true
        isLenient = true
    }

    /**
     * Get the semantic test name for a fixture file
     */
    private fun getTestName(filename: String): String {
        val stem = filename.removeSuffix(".json")
        return when (stem) {
            "semantic_duplicates" -> "test_semantic_duplicate_capture_group"
            "semantic_ranges" -> "test_semantic_ranges"
            else -> "test_conformance_$stem"
        }
    }

    @TestFactory
    fun runConformanceTests(): List<DynamicTest> {
        // Adjust path to point to tests/spec from bindings/kotlin
        val specDir = File("../../tests/spec")
        if (!specDir.exists()) {
            // Fallback for running from root or different context
            val altDir = File("tests/spec")
            if (altDir.exists()) {
                return generateTests(altDir)
            }
            println("Spec directory not found at ${specDir.absolutePath}")
            return emptyList()
        }

        return generateTests(specDir)
    }

    private fun generateTests(dir: File): List<DynamicTest> {
        return dir.listFiles { _, name -> name.endsWith(".json") }
            ?.sortedBy { it.name }
            ?.map { file ->
                val testName = getTestName(file.name)
                DynamicTest.dynamicTest(testName) {
                    println("=== RUN $testName (${file.name})")
                    runTest(file)
                }
            }
            ?: emptyList()
    }

    private fun runTest(file: File) {
        val content = file.readText()
        val root = json.parseToJsonElement(content).jsonObject

        // Skip if no input_ast or expected_ir
        if (!root.containsKey("input_ast") || !root.containsKey("expected_ir")) {
            return
        }

        val inputAstJson = root["input_ast"]!!
        val expectedIrJson = root["expected_ir"]!!

        try {
            // Decode AST
            // The @JsonClassDiscriminator("type") on Node interface handles the type field
            val ast = json.decodeFromJsonElement<Node>(inputAstJson)

            // Compile
            val actualIr = Compiler.compile(ast)

            // Decode Expected IR
            // The @JsonClassDiscriminator("ir") on IROp interface handles the ir field
            val expectedIr = json.decodeFromJsonElement<IROp>(expectedIrJson)

            // Assert
            assertEquals(expectedIr, actualIr, "IR mismatch in ${file.name}")
        } catch (e: Exception) {
            throw AssertionError("Failed to process ${file.name}: ${e.message}", e)
        }
    }

    @TestFactory
    fun runErrorConformanceTests(): List<DynamicTest> {
        val specDir = File("../../tests/spec")
        val dir = if (specDir.exists()) specDir else {
            val altDir = File("tests/spec")
            if (altDir.exists()) altDir else return emptyList()
        }

        return dir.listFiles { _, name -> name.endsWith(".json") }
            ?.sortedBy { it.name }
            ?.mapNotNull { file ->
                val content = file.readText()
                val root = json.parseToJsonElement(content).jsonObject
                if (!root.containsKey("expected_error") || !root.containsKey("expected_hint")) {
                    return@mapNotNull null
                }
                // Skip compilation-error fixtures (have input_ast) — those are tested by IR conformance
                if (root.containsKey("input_ast")) {
                    return@mapNotNull null
                }

                val expectedError = root["expected_error"]!!.jsonPrimitive.content
                val expectedHint = root["expected_hint"]!!.jsonPrimitive.content
                val inputDsl = root["input_dsl"]!!.jsonPrimitive.content
                val testName = "test_error_${file.nameWithoutExtension}"

                DynamicTest.dynamicTest(testName) {
                    println("=== RUN $testName (${file.name})")
                    try {
                        Parser.parse(inputDsl)
                        throw AssertionError("Expected error '$expectedError' but parsing succeeded for ${file.name}")
                    } catch (e: STRlingParseError) {
                        assertTrue(
                            e.message?.contains(expectedError) == true,
                            "Error message mismatch in ${file.name}: expected to contain '$expectedError' but got '${e.message}'"
                        )
                        assertEquals(
                            expectedHint,
                            e.hint,
                            "Hint mismatch in ${file.name}"
                        )
                    }
                }
            }
            ?: emptyList()
    }
}
