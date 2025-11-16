package com.strling.core;

import java.util.HashMap;
import java.util.Map;

/**
 * STRling Error Classes - Rich Error Handling for Instructional Diagnostics
 *
 * <p>This module provides enhanced error classes that deliver context-aware,
 * instructional error messages. The STRlingParseError class stores detailed
 * information about syntax errors including position, context, and beginner-friendly
 * hints for resolution.</p>
 */
public class STRlingParseError extends RuntimeException {
    /**
     * A concise description of what went wrong.
     */
    private final String message;
    
    /**
     * The character position (0-indexed) where the error occurred.
     */
    private final int pos;
    
    /**
     * The full input text being parsed.
     */
    private final String text;
    
    /**
     * An instructional hint explaining how to fix the error.
     */
    private final String hint;
    
    /**
     * Initializes a STRlingParseError.
     * 
     * @param message A concise description of what went wrong
     * @param pos The character position (0-indexed) where the error occurred
     * @param text The full input text being parsed (default: "")
     * @param hint An instructional hint explaining how to fix the error (default: null)
     */
    public STRlingParseError(String message, int pos, String text, String hint) {
        super(formatError(message, pos, text, hint));
        this.message = message;
        this.pos = pos;
        this.text = text != null ? text : "";
        this.hint = hint;
    }
    
    /**
     * Initializes a STRlingParseError without a hint.
     * 
     * @param message A concise description of what went wrong
     * @param pos The character position (0-indexed) where the error occurred
     * @param text The full input text being parsed
     */
    public STRlingParseError(String message, int pos, String text) {
        this(message, pos, text, null);
    }
    
    /**
     * Initializes a STRlingParseError without text or hint.
     * 
     * @param message A concise description of what went wrong
     * @param pos The character position (0-indexed) where the error occurred
     */
    public STRlingParseError(String message, int pos) {
        this(message, pos, "", null);
    }
    
    /**
     * Gets the error message.
     * 
     * @return The error message
     */
    public String getErrorMessage() {
        return message;
    }
    
    /**
     * Gets the error position.
     * 
     * @return The character position where the error occurred
     */
    public int getPos() {
        return pos;
    }
    
    /**
     * Gets the input text.
     * 
     * @return The full input text being parsed
     */
    public String getText() {
        return text;
    }
    
    /**
     * Gets the hint.
     * 
     * @return The instructional hint, or null if none provided
     */
    public String getHint() {
        return hint;
    }
    
    /**
     * Formats the error in the visionary state format.
     * 
     * @param message The error message
     * @param pos The character position where the error occurred
     * @param text The full input text
     * @param hint An optional hint
     * @return A formatted error message with context and hints
     */
    private static String formatError(String message, int pos, String text, String hint) {
        if (text == null || text.isEmpty()) {
            // Fallback to simple format if no text provided
            return message + " at position " + pos;
        }
        
        // Find the line containing the error
        String[] lines = text.split("\n", -1);
        int currentPos = 0;
        int lineNum = 1;
        String lineText = "";
        int col = pos;
        
        boolean found = false;
        for (int i = 0; i < lines.length; i++) {
            String line = lines[i];
            int lineLen = line.length() + 1; // +1 for newline
            if (currentPos + lineLen > pos) {
                lineNum = i + 1;
                lineText = line;
                col = pos - currentPos;
                found = true;
                break;
            }
            currentPos += lineLen;
        }
        
        if (!found) {
            // Error is beyond the last line
            if (lines.length > 0) {
                lineNum = lines.length;
                lineText = lines[lines.length - 1];
                col = lineText.length();
            } else {
                lineText = text;
                col = pos;
            }
        }
        
        // Build the formatted error message
        StringBuilder sb = new StringBuilder();
        sb.append("STRling Parse Error: ").append(message).append("\n");
        sb.append("\n");
        sb.append("> ").append(lineNum).append(" | ").append(lineText).append("\n");
        sb.append(">   | ");
        for (int i = 0; i < col; i++) {
            sb.append(" ");
        }
        sb.append("^\n");
        
        if (hint != null && !hint.isEmpty()) {
            sb.append("\n");
            sb.append("Hint: ").append(hint);
        }
        
        return sb.toString();
    }
    
    /**
     * Gets the formatted error message.
     * 
     * @return The formatted error string
     */
    public String toFormattedString() {
        return getMessage();
    }
    
    /**
     * Converts the error to LSP Diagnostic format.
     * 
     * <p>Returns a Map compatible with the Language Server Protocol
     * Diagnostic specification, which can be serialized to JSON for
     * communication with LSP clients.</p>
     * 
     * @return A Map containing:
     *         <ul>
     *         <li>range: The line/column range where the error occurred</li>
     *         <li>severity: Error severity (1 = Error)</li>
     *         <li>message: The error message with hint if available</li>
     *         <li>source: "STRling"</li>
     *         <li>code: A normalized error code derived from the message</li>
     *         </ul>
     */
    public Map<String, Object> toLspDiagnostic() {
        // Find the line and column containing the error
        String[] lines = text.isEmpty() ? new String[0] : text.split("\n", -1);
        int currentPos = 0;
        int lineNum = 0; // 0-indexed for LSP
        int col = pos;
        
        boolean found = false;
        for (int i = 0; i < lines.length; i++) {
            String line = lines[i];
            int lineLen = line.length() + 1; // +1 for newline
            if (currentPos + lineLen > pos) {
                lineNum = i;
                col = pos - currentPos;
                found = true;
                break;
            }
            currentPos += lineLen;
        }
        
        if (!found) {
            // Error is beyond the last line
            if (lines.length > 0) {
                lineNum = lines.length - 1;
                col = lines[lines.length - 1].length();
            } else {
                lineNum = 0;
                col = pos;
            }
        }
        
        // Build the diagnostic message
        String diagnosticMessage = message;
        if (hint != null && !hint.isEmpty()) {
            diagnosticMessage += "\n\nHint: " + hint;
        }
        
        // Create error code from message (normalize to snake_case)
        String errorCode = message.toLowerCase();
        String[] charsToReplace = {" ", "'", "\"", "(", ")", "[", "]", "{", "}", "\\", "/"};
        for (String ch : charsToReplace) {
            errorCode = errorCode.replace(ch, "_");
        }
        // Remove multiple underscores and empty parts
        errorCode = errorCode.replaceAll("_+", "_").replaceAll("^_|_$", "");
        
        // Build range
        Map<String, Integer> start = new HashMap<>();
        start.put("line", lineNum);
        start.put("character", col);
        
        Map<String, Integer> end = new HashMap<>();
        end.put("line", lineNum);
        end.put("character", col + 1);
        
        Map<String, Object> range = new HashMap<>();
        range.put("start", start);
        range.put("end", end);
        
        // Build diagnostic
        Map<String, Object> diagnostic = new HashMap<>();
        diagnostic.put("range", range);
        diagnostic.put("severity", 1); // 1 = Error, 2 = Warning, 3 = Information, 4 = Hint
        diagnostic.put("message", diagnosticMessage);
        diagnostic.put("source", "STRling");
        diagnostic.put("code", errorCode);
        
        return diagnostic;
    }
}
