package strling.core

/**
 * STRling Error Classes - Rich Error Handling for Instructional Diagnostics
 * 
 * This module provides enhanced error classes that deliver context-aware,
 * instructional error messages. The STRlingParseError class stores detailed
 * information about syntax errors including position, context, and beginner-friendly
 * hints for resolution.
 */

/**
 * Rich parse error with position tracking and instructional hints.
 * 
 * This error class transforms parse failures into learning opportunities by
 * providing:
 * - The specific error message
 * - The exact position where the error occurred
 * - The full line of text containing the error
 * - A beginner-friendly hint explaining how to fix the issue
 * 
 * @property message A concise description of what went wrong
 * @property pos The character position (0-indexed) where the error occurred
 * @property text The full input text being parsed
 * @property hint An instructional hint explaining how to fix the error
 */
class STRlingParseError(
    message: String,
    val pos: Int,
    val text: String = "",
    val hint: String? = null
) : Exception(message) {
    
    /**
     * Format the error in the visionary state format.
     * 
     * @return A formatted error message with context and hints
     */
    private fun formatError(): String {
        if (text.isEmpty()) {
            // Fallback to simple format if no text provided
            return "${message} at position $pos"
        }
        
        // Find the line containing the error
        val lines = text.lines()
        var currentPos = 0
        var lineNum = 1
        var lineText = ""
        var col = pos
        
        for ((i, line) in lines.withIndex()) {
            val lineLen = line.length + 1  // +1 for newline
            if (currentPos + lineLen > pos) {
                lineNum = i + 1
                lineText = line
                col = pos - currentPos
                break
            }
            currentPos += lineLen
        }
        
        // Error is beyond the last line
        if (lineText.isEmpty() && lines.isNotEmpty()) {
            lineNum = lines.size
            lineText = lines.last()
            col = lineText.length
        } else if (lineText.isEmpty()) {
            lineText = text
            col = pos
        }
        
        // Build the formatted error message
        val parts = mutableListOf<String>()
        parts.add("STRling Parse Error: $message")
        parts.add("")
        parts.add("> $lineNum | $lineText")
        parts.add(">   | ${" ".repeat(col)}^")
        
        if (hint != null) {
            parts.add("")
            parts.add("Hint: $hint")
        }
        
        return parts.joinToString("\n")
    }
    
    /**
     * Return the formatted error message.
     */
    override fun toString(): String {
        return formatError()
    }
    
    /**
     * Backwards/JS-friendly alias for getting the formatted error string.
     * 
     * @return The formatted error message (same as `toString()`)
     */
    fun toFormattedString(): String {
        return formatError()
    }
    
    /**
     * Convert the error to LSP Diagnostic format.
     * 
     * Returns a map compatible with the Language Server Protocol
     * Diagnostic specification, which can be serialized to JSON for
     * communication with LSP clients.
     * 
     * @return A map containing:
     *   - range: The line/column range where the error occurred
     *   - severity: Error severity (1 = Error)
     *   - message: The error message with hint if available
     *   - source: "STRling"
     *   - code: A normalized error code derived from the message
     */
    fun toLspDiagnostic(): Map<String, Any> {
        // Find the line and column containing the error
        val lines = if (text.isNotEmpty()) text.lines() else emptyList()
        var currentPos = 0
        var lineNum = 0  // 0-indexed for LSP
        var col = pos
        
        for ((i, line) in lines.withIndex()) {
            val lineLen = line.length + 1  // +1 for newline
            if (currentPos + lineLen > pos) {
                lineNum = i
                col = pos - currentPos
                break
            }
            currentPos += lineLen
        }
        
        // Error is beyond the last line
        if (currentPos <= pos && lines.isNotEmpty()) {
            lineNum = lines.size - 1
            col = lines.last().length
        } else if (lines.isEmpty()) {
            lineNum = 0
            col = pos
        }
        
        // Build the diagnostic message
        val diagnosticMessage = if (hint != null) {
            "$message\n\nHint: $hint"
        } else {
            message ?: ""
        }
        
        // Create error code from message (normalize to snake_case)
        var errorCode = (message ?: "").lowercase()
        for (char in listOf(" ", "'", "\"", "(", ")", "[", "]", "{", "}", "\\", "/")) {
            errorCode = errorCode.replace(char, "_")
        }
        errorCode = errorCode.split("_").filter { it.isNotEmpty() }.joinToString("_")
        
        return mapOf(
            "range" to mapOf(
                "start" to mapOf("line" to lineNum, "character" to col),
                "end" to mapOf("line" to lineNum, "character" to col + 1)
            ),
            "severity" to 1,  // 1 = Error, 2 = Warning, 3 = Information, 4 = Hint
            "message" to diagnosticMessage,
            "source" to "STRling",
            "code" to errorCode
        )
    }
}
