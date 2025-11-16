// Package core contains the fundamental data structures and types for the STRling
// compiler, including AST nodes, IR nodes, and error types.
package core

import (
	"fmt"
	"strings"
)

// STRlingParseError represents a rich parse error with position tracking and
// instructional hints.
//
// This error class transforms parse failures into learning opportunities by
// providing:
//   - The specific error message
//   - The exact position where the error occurred
//   - The full line of text containing the error
//   - A beginner-friendly hint explaining how to fix the issue
type STRlingParseError struct {
	// Message is a concise description of what went wrong
	Message string

	// Pos is the character position (0-indexed) where the error occurred
	Pos int

	// Text is the full input text being parsed
	Text string

	// Hint is an instructional hint explaining how to fix the error
	Hint string
}

// Error implements the error interface, returning a formatted error message.
func (e *STRlingParseError) Error() string {
	return e.formatError()
}

// formatError formats the error in the visionary state format.
func (e *STRlingParseError) formatError() string {
	if e.Text == "" {
		// Fallback to simple format if no text provided
		return fmt.Sprintf("%s at position %d", e.Message, e.Pos)
	}

	// Find the line containing the error
	lines := strings.Split(e.Text, "\n")
	currentPos := 0
	lineNum := 1
	lineText := ""
	col := e.Pos

	for i, line := range lines {
		lineLen := len(line) + 1 // +1 for newline
		if currentPos+lineLen > e.Pos {
			lineNum = i + 1
			lineText = line
			col = e.Pos - currentPos
			break
		}
		currentPos += lineLen
	}

	// If we didn't find the line (error beyond last line)
	if lineText == "" && len(lines) > 0 {
		lineNum = len(lines)
		lineText = lines[len(lines)-1]
		col = len(lineText)
	} else if lineText == "" {
		lineText = e.Text
		col = e.Pos
	}

	// Build the formatted error message
	var parts []string
	parts = append(parts, fmt.Sprintf("STRling Parse Error: %s", e.Message))
	parts = append(parts, "")
	parts = append(parts, fmt.Sprintf("> %d | %s", lineNum, lineText))
	parts = append(parts, fmt.Sprintf(">   | %s^", strings.Repeat(" ", col)))

	if e.Hint != "" {
		parts = append(parts, "")
		parts = append(parts, fmt.Sprintf("Hint: %s", e.Hint))
	}

	return strings.Join(parts, "\n")
}

// ToFormattedString returns the formatted error message.
// This is a backwards/JS-friendly alias for Error().
func (e *STRlingParseError) ToFormattedString() string {
	return e.formatError()
}

// LSPDiagnostic represents a Language Server Protocol diagnostic message.
type LSPDiagnostic struct {
	Range    LSPRange `json:"range"`
	Severity int      `json:"severity"`
	Message  string   `json:"message"`
	Source   string   `json:"source"`
	Code     string   `json:"code"`
}

// LSPRange represents a range in a document.
type LSPRange struct {
	Start LSPPosition `json:"start"`
	End   LSPPosition `json:"end"`
}

// LSPPosition represents a position in a document.
type LSPPosition struct {
	Line      int `json:"line"`
	Character int `json:"character"`
}

// ToLSPDiagnostic converts the error to LSP Diagnostic format.
//
// Returns a diagnostic compatible with the Language Server Protocol
// Diagnostic specification, which can be serialized to JSON for
// communication with LSP clients.
func (e *STRlingParseError) ToLSPDiagnostic() LSPDiagnostic {
	// Find the line and column containing the error
	lines := []string{}
	if e.Text != "" {
		lines = strings.Split(e.Text, "\n")
	}

	currentPos := 0
	lineNum := 0 // 0-indexed for LSP
	col := e.Pos

	for i, line := range lines {
		lineLen := len(line) + 1 // +1 for newline
		if currentPos+lineLen > e.Pos {
			lineNum = i
			col = e.Pos - currentPos
			break
		}
		currentPos += lineLen
	}

	// If error is beyond the last line
	if len(lines) > 0 && currentPos <= e.Pos {
		lineNum = len(lines) - 1
		col = len(lines[len(lines)-1])
	}

	// Build the diagnostic message
	diagnosticMessage := e.Message
	if e.Hint != "" {
		diagnosticMessage += fmt.Sprintf("\n\nHint: %s", e.Hint)
	}

	// Create error code from message (normalize to snake_case)
	errorCode := strings.ToLower(e.Message)
	replaceChars := []string{" ", "'", "\"", "(", ")", "[", "]", "{", "}", "\\", "/"}
	for _, char := range replaceChars {
		errorCode = strings.ReplaceAll(errorCode, char, "_")
	}
	// Clean up multiple underscores
	parts := strings.Split(errorCode, "_")
	filteredParts := []string{}
	for _, part := range parts {
		if part != "" {
			filteredParts = append(filteredParts, part)
		}
	}
	errorCode = strings.Join(filteredParts, "_")

	return LSPDiagnostic{
		Range: LSPRange{
			Start: LSPPosition{Line: lineNum, Character: col},
			End:   LSPPosition{Line: lineNum, Character: col + 1},
		},
		Severity: 1, // 1 = Error, 2 = Warning, 3 = Information, 4 = Hint
		Message:  diagnosticMessage,
		Source:   "STRling",
		Code:     errorCode,
	}
}
