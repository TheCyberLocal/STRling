<?php

namespace STRling\Core;

use Exception;

/**
 * STRling Error Classes - Rich Error Handling for Instructional Diagnostics
 * 
 * This module provides enhanced error classes that deliver context-aware,
 * instructional error messages. The STRlingParseError class stores detailed
 * information about syntax errors including position, context, and beginner-friendly
 * hints for resolution.
 * 
 * @package STRling\Core
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
 */
class STRlingParseError extends Exception
{
    /**
     * @var int The character position (0-indexed) where the error occurred
     */
    public int $pos;
    
    /**
     * @var string The full input text being parsed
     */
    public string $text;
    
    /**
     * @var string|null An instructional hint explaining how to fix the error
     */
    public ?string $hint;
    
    /**
     * Initialize a STRlingParseError.
     * 
     * @param string $message A concise description of what went wrong
     * @param int $pos The character position (0-indexed) where the error occurred
     * @param string $text The full input text being parsed (default: "")
     * @param string|null $hint An instructional hint explaining how to fix the error (default: null)
     */
    public function __construct(
        string $message,
        int $pos,
        string $text = "",
        ?string $hint = null
    ) {
        $this->pos = $pos;
        $this->text = $text;
        $this->hint = $hint;
        
        // Call parent constructor with formatted message
        parent::__construct($this->formatError(), 0, null);
    }
    
    /**
     * Format the error in the visionary state format.
     * 
     * @return string A formatted error message with context and hints
     */
    private function formatError(): string
    {
        if (empty($this->text)) {
            // Fallback to simple format if no text provided
            return $this->message . " at position " . $this->pos;
        }
        
        // Find the line containing the error
        $lines = explode("\n", $this->text);
        $currentPos = 0;
        $lineNum = 1;
        $lineText = "";
        $col = $this->pos;
        
        foreach ($lines as $i => $line) {
            $lineLen = strlen($line) + 1;  // +1 for newline
            if ($currentPos + $lineLen > $this->pos) {
                $lineNum = $i + 1;
                $lineText = $line;
                $col = $this->pos - $currentPos;
                break;
            }
            $currentPos += $lineLen;
        }
        
        // If we didn't find the line (error is beyond the last line)
        if ($lineText === "" && count($lines) > 0) {
            $lineNum = count($lines);
            $lineText = $lines[count($lines) - 1];
            $col = strlen($lineText);
        } elseif ($lineText === "") {
            $lineText = $this->text;
            $col = $this->pos;
        }
        
        // Build the formatted error message
        $parts = ["STRling Parse Error: " . $this->message, ""];
        $parts[] = "> " . $lineNum . " | " . $lineText;
        $parts[] = ">   | " . str_repeat(' ', $col) . "^";
        
        if ($this->hint !== null) {
            $parts[] = "";
            $parts[] = "Hint: " . $this->hint;
        }
        
        return implode("\n", $parts);
    }
    
    /**
     * Return the formatted error message.
     * 
     * @return string The formatted error message
     */
    public function __toString(): string
    {
        return $this->formatError();
    }
    
    /**
     * Backwards/JS-friendly alias for getting the formatted error string.
     * 
     * @return string The formatted error message (same as __toString())
     */
    public function toFormattedString(): string
    {
        return $this->formatError();
    }
    
    /**
     * Convert the error to LSP Diagnostic format.
     * 
     * Returns an array compatible with the Language Server Protocol
     * Diagnostic specification, which can be serialized to JSON for
     * communication with LSP clients.
     * 
     * @return array<string, mixed> An array containing:
     *   - range: The line/column range where the error occurred
     *   - severity: Error severity (1 = Error)
     *   - message: The error message with hint if available
     *   - source: "STRling"
     *   - code: A normalized error code derived from the message
     */
    public function toLspDiagnostic(): array
    {
        // Find the line and column containing the error
        $lines = !empty($this->text) ? explode("\n", $this->text) : [];
        $currentPos = 0;
        $lineNum = 0;  // 0-indexed for LSP
        $col = $this->pos;
        
        foreach ($lines as $i => $line) {
            $lineLen = strlen($line) + 1;  // +1 for newline
            if ($currentPos + $lineLen > $this->pos) {
                $lineNum = $i;
                $col = $this->pos - $currentPos;
                break;
            }
            $currentPos += $lineLen;
        }
        
        // Error is beyond the last line
        if ($currentPos <= $this->pos && count($lines) > 0) {
            $lineNum = count($lines) - 1;
            $col = strlen($lines[count($lines) - 1]);
        } elseif (count($lines) === 0) {
            $lineNum = 0;
            $col = $this->pos;
        }
        
        // Build the diagnostic message
        $diagnosticMessage = $this->message;
        if ($this->hint !== null) {
            $diagnosticMessage .= "\n\nHint: " . $this->hint;
        }
        
        // Create error code from message (normalize to snake_case)
        $errorCode = strtolower($this->message);
        $charsToReplace = [' ', "'", '"', '(', ')', '[', ']', '{', '}', '\\', '/'];
        $errorCode = str_replace($charsToReplace, '_', $errorCode);
        $errorCode = implode('_', array_filter(explode('_', $errorCode)));
        
        return [
            'range' => [
                'start' => ['line' => $lineNum, 'character' => $col],
                'end' => ['line' => $lineNum, 'character' => $col + 1]
            ],
            'severity' => 1,  // 1 = Error, 2 = Warning, 3 = Information, 4 = Hint
            'message' => $diagnosticMessage,
            'source' => 'STRling',
            'code' => $errorCode
        ];
    }
}
