package strling

import kotlinx.serialization.json.Json
import kotlinx.serialization.json.decodeFromJsonElement
import kotlinx.serialization.json.jsonObject
import org.junit.jupiter.api.Assertions.assertEquals
import org.junit.jupiter.api.TestFactory
import org.junit.jupiter.api.DynamicTest
import java.io.File
import strling.core.Compiler
import strling.core.Node
import strling.core.IROp

class ConformanceTest {

    private val json = Json {
        ignoreUnknownKeys = true
        prettyPrint = true
        isLenient = true
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
                DynamicTest.dynamicTest(file.name) {
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
}
