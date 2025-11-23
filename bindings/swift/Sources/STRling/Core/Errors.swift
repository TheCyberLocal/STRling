/// STRling Error Classes - Rich Error Handling for Instructional Diagnostics
///
/// This module provides enhanced error classes that deliver context-aware,
/// instructional error messages. The STRlingParseError class stores detailed
/// information about syntax errors including position, context, and beginner-friendly
/// hints for resolution.

import Foundation

/// Rich parse error with position tracking and instructional hints.
///
/// This error class transforms parse failures into learning opportunities by
/// providing:
/// - The specific error message
/// - The exact position where the error occurred
/// - The full line of text containing the error
/// - A beginner-friendly hint explaining how to fix the issue
public struct STRlingParseError: Error {
    /// A concise description of what went wrong
    public let message: String
    
    /// The character position (0-indexed) where the error occurred
    public let pos: Int
    
    /// The full input text being parsed
    public let text: String
    
    /// An instructional hint explaining how to fix the error
    public let hint: String?
    
    /// Initialize a STRlingParseError.
    ///
    /// - Parameters:
    ///   - message: A concise description of what went wrong
    ///   - pos: The character position (0-indexed) where the error occurred
    ///   - text: The full input text being parsed (default: "")
    ///   - hint: An instructional hint explaining how to fix the error (default: nil)
    public init(message: String, pos: Int, text: String = "", hint: String? = nil) {
        self.message = message
        self.pos = pos
        self.text = text
        self.hint = hint
    }
    
    /// Format the error in the visionary state format.
    ///
    /// - Returns: A formatted error message with context and hints
    private func formatError() -> String {
        if text.isEmpty {
            // Fallback to simple format if no text provided
            return "\(message) at position \(pos)"
        }
        
        // Find the line containing the error
        let lines = text.components(separatedBy: .newlines)
        var currentPos = 0
        var lineNum = 1
        var lineText = ""
        var col = pos
        
        for (i, line) in lines.enumerated() {
            let lineLen = line.count + 1  // +1 for newline
            if currentPos + lineLen > pos {
                lineNum = i + 1
                lineText = line
                col = pos - currentPos
                break
            }
            currentPos += lineLen
        }
        
        // If we didn't find the line, use the last line
        if lineText.isEmpty {
            if !lines.isEmpty {
                lineNum = lines.count
                lineText = lines.last!
                col = lineText.count
            } else {
                lineText = text
                col = pos
            }
        }
        
        // Build the formatted error message
        var parts: [String] = []
        parts.append("STRling Parse Error: \(message)")
        parts.append("")
        parts.append("> \(lineNum) | \(lineText)")
        parts.append(">   | \(String(repeating: " ", count: col))^")
        
        if let hint = hint {
            parts.append("")
            parts.append("Hint: \(hint)")
        }
        
        return parts.joined(separator: "\n")
    }
    
    /// Return the formatted error message.
    public var localizedDescription: String {
        return formatError()
    }
    
    /// Backwards/JS-friendly alias for getting the formatted error string.
    ///
    /// - Returns: The formatted error message (same as `localizedDescription`)
    public func toFormattedString() -> String {
        return formatError()
    }
    
    /// Convert the error to LSP Diagnostic format.
    ///
    /// Returns a dictionary compatible with the Language Server Protocol
    /// Diagnostic specification, which can be serialized to JSON for
    /// communication with LSP clients.
    ///
    /// - Returns: A dictionary containing:
    ///   - range: The line/column range where the error occurred
    ///   - severity: Error severity (1 = Error)
    ///   - message: The error message with hint if available
    ///   - source: "STRling"
    ///   - code: A normalized error code derived from the message
    public func toLSPDiagnostic() -> [String: Any] {
        // Find the line and column containing the error
        let lines = text.isEmpty ? [] : text.components(separatedBy: .newlines)
        var currentPos = 0
        var lineNum = 0  // 0-indexed for LSP
        var col = pos
        
        for (i, line) in lines.enumerated() {
            let lineLen = line.count + 1  // +1 for newline
            if currentPos + lineLen > pos {
                lineNum = i
                col = pos - currentPos
                break
            }
            currentPos += lineLen
        }
        
        // If we didn't find the line, use the last line
        if lineNum == 0 && !lines.isEmpty && currentPos <= pos {
            lineNum = lines.count - 1
            col = lines.last?.count ?? 0
        }
        
        // Build the diagnostic message
        var diagnosticMessage = message
        if let hint = hint {
            diagnosticMessage += "\n\nHint: \(hint)"
        }
        
        // Create error code from message (normalize to snake_case)
        var errorCode = message.lowercased()
        let charsToReplace = [" ", "'", "\"", "(", ")", "[", "]", "{", "}", "\\", "/"]
        for char in charsToReplace {
            errorCode = errorCode.replacingOccurrences(of: char, with: "_")
        }
        errorCode = errorCode.components(separatedBy: "_").filter { !$0.isEmpty }.joined(separator: "_")
        
        return [
            "range": [
                "start": ["line": lineNum, "character": col],
                "end": ["line": lineNum, "character": col + 1]
            ],
            "severity": 1,  // 1 = Error, 2 = Warning, 3 = Information, 4 = Hint
            "message": diagnosticMessage,
            "source": "STRling",
            "code": errorCode
        ]
    }
}

/// Errors that can occur during compilation/lowering
public enum CompilerError: Error {
    case unknownClassItemType(String)
    case invalidQuantifier(String)
    case generic(String)
}
