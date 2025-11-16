namespace Strling.Core;

/// <summary>
/// STRling Error Classes - Rich Error Handling for Instructional Diagnostics
/// 
/// This module provides enhanced error classes that deliver context-aware,
/// instructional error messages. The STRlingParseError class stores detailed
/// information about syntax errors including position, context, and beginner-friendly
/// hints for resolution.
/// </summary>

using System;
using System.Collections.Generic;
using System.Linq;

/// <summary>
/// Rich parse error with position tracking and instructional hints.
/// 
/// This error class transforms parse failures into learning opportunities by
/// providing:
/// - The specific error message
/// - The exact position where the error occurred
/// - The full line of text containing the error
/// - A beginner-friendly hint explaining how to fix the issue
/// </summary>
public class STRlingParseError : Exception
{
    /// <summary>
    /// A concise description of what went wrong.
    /// </summary>
    public string ErrorMessage { get; }
    
    /// <summary>
    /// The character position (0-indexed) where the error occurred.
    /// </summary>
    public int Pos { get; }
    
    /// <summary>
    /// The full input text being parsed.
    /// </summary>
    public string Text { get; }
    
    /// <summary>
    /// An instructional hint explaining how to fix the error.
    /// </summary>
    public string? Hint { get; }

    /// <summary>
    /// Initialize a STRlingParseError.
    /// </summary>
    /// <param name="message">A concise description of what went wrong</param>
    /// <param name="pos">The character position (0-indexed) where the error occurred</param>
    /// <param name="text">The full input text being parsed (default: "")</param>
    /// <param name="hint">An instructional hint explaining how to fix the error (default: null)</param>
    public STRlingParseError(
        string message,
        int pos,
        string text = "",
        string? hint = null)
        : base(FormatError(message, pos, text, hint))
    {
        ErrorMessage = message;
        Pos = pos;
        Text = text;
        Hint = hint;
    }

    /// <summary>
    /// Format the error in the visionary state format.
    /// </summary>
    /// <returns>A formatted error message with context and hints</returns>
    private static string FormatError(string message, int pos, string text, string? hint)
    {
        if (string.IsNullOrEmpty(text))
        {
            // Fallback to simple format if no text provided
            return $"{message} at position {pos}";
        }

        // Find the line containing the error
        var lines = text.Split('\n');
        var currentPos = 0;
        var lineNum = 1;
        var lineText = "";
        var col = pos;

        for (int i = 0; i < lines.Length; i++)
        {
            var line = lines[i];
            var lineLen = line.Length + 1; // +1 for newline
            if (currentPos + lineLen > pos)
            {
                lineNum = i + 1;
                lineText = line;
                col = pos - currentPos;
                break;
            }
            currentPos += lineLen;
        }

        // If error is beyond the last line
        if (string.IsNullOrEmpty(lineText))
        {
            if (lines.Length > 0)
            {
                lineNum = lines.Length;
                lineText = lines[^1];
                col = lineText.Length;
            }
            else
            {
                lineText = text;
                col = pos;
            }
        }

        // Build the formatted error message
        var parts = new List<string>
        {
            $"STRling Parse Error: {message}",
            "",
            $"> {lineNum} | {lineText}",
            $">   | {new string(' ', col)}^"
        };

        if (!string.IsNullOrEmpty(hint))
        {
            parts.Add("");
            parts.Add($"Hint: {hint}");
        }

        return string.Join("\n", parts);
    }

    /// <summary>
    /// Backwards/JS-friendly alias for getting the formatted error string.
    /// </summary>
    /// <returns>The formatted error message (same as ToString())</returns>
    public string ToFormattedString()
    {
        return Message;
    }

    /// <summary>
    /// Convert the error to LSP Diagnostic format.
    /// 
    /// Returns a dictionary compatible with the Language Server Protocol
    /// Diagnostic specification, which can be serialized to JSON for
    /// communication with LSP clients.
    /// </summary>
    /// <returns>
    /// A dictionary containing:
    /// - range: The line/column range where the error occurred
    /// - severity: Error severity (1 = Error)
    /// - message: The error message with hint if available
    /// - source: "STRling"
    /// - code: A normalized error code derived from the message
    /// </returns>
    public Dictionary<string, object> ToLspDiagnostic()
    {
        // Find the line and column containing the error
        var lines = !string.IsNullOrEmpty(Text) ? Text.Split('\n') : Array.Empty<string>();
        var currentPos = 0;
        var lineNum = 0; // 0-indexed for LSP
        var col = Pos;

        for (int i = 0; i < lines.Length; i++)
        {
            var line = lines[i];
            var lineLen = line.Length + 1; // +1 for newline
            if (currentPos + lineLen > Pos)
            {
                lineNum = i;
                col = Pos - currentPos;
                break;
            }
            currentPos += lineLen;
        }

        // If error is beyond the last line
        if (lineNum >= lines.Length && lines.Length > 0)
        {
            lineNum = lines.Length - 1;
            col = lines[^1].Length;
        }
        else if (lines.Length == 0)
        {
            lineNum = 0;
            col = Pos;
        }

        // Build the diagnostic message
        var diagnosticMessage = ErrorMessage;
        if (!string.IsNullOrEmpty(Hint))
        {
            diagnosticMessage += $"\n\nHint: {Hint}";
        }

        // Create error code from message (normalize to snake_case)
        var errorCode = ErrorMessage.ToLower();
        foreach (var ch in new[] { ' ', '\'', '"', '(', ')', '[', ']', '{', '}', '\\', '/' })
        {
            errorCode = errorCode.Replace(ch, '_');
        }
        errorCode = string.Join("_", errorCode.Split('_').Where(s => !string.IsNullOrEmpty(s)));

        return new Dictionary<string, object>
        {
            ["range"] = new Dictionary<string, object>
            {
                ["start"] = new Dictionary<string, object>
                {
                    ["line"] = lineNum,
                    ["character"] = col
                },
                ["end"] = new Dictionary<string, object>
                {
                    ["line"] = lineNum,
                    ["character"] = col + 1
                }
            },
            ["severity"] = 1, // 1 = Error, 2 = Warning, 3 = Information, 4 = Hint
            ["message"] = diagnosticMessage,
            ["source"] = "STRling",
            ["code"] = errorCode
        };
    }
}
