//! STRling Error Classes - Rich Error Handling for Instructional Diagnostics
//!
//! This module provides enhanced error classes that deliver context-aware,
//! instructional error messages. The STRlingParseError class stores detailed
//! information about syntax errors including position, context, and beginner-friendly
//! hints for resolution.

use serde::{Deserialize, Serialize};
use std::error::Error;
use std::fmt;

/// Rich parse error with position tracking and instructional hints.
///
/// This error class transforms parse failures into learning opportunities by
/// providing:
/// - The specific error message
/// - The exact position where the error occurred
/// - The full line of text containing the error
/// - A beginner-friendly hint explaining how to fix the issue
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct STRlingParseError {
    /// A concise description of what went wrong
    pub message: String,
    /// The character position (0-indexed) where the error occurred
    pub pos: usize,
    /// The full input text being parsed
    pub text: String,
    /// An instructional hint explaining how to fix the error
    pub hint: Option<String>,
}

impl STRlingParseError {
    /// Initialize a STRlingParseError.
    ///
    /// # Arguments
    ///
    /// * `message` - A concise description of what went wrong
    /// * `pos` - The character position (0-indexed) where the error occurred
    /// * `text` - The full input text being parsed (default: "")
    /// * `hint` - An instructional hint explaining how to fix the error (default: None)
    pub fn new(message: String, pos: usize, text: String, hint: Option<String>) -> Self {
        STRlingParseError {
            message,
            pos,
            text,
            hint,
        }
    }

    /// Format the error in the visionary state format.
    ///
    /// Returns a formatted error message with context and hints.
    fn format_error(&self) -> String {
        if self.text.is_empty() {
            // Fallback to simple format if no text provided
            return format!("{} at position {}", self.message, self.pos);
        }

        // Find the line containing the error
        let lines: Vec<&str> = self.text.lines().collect();
        let mut current_pos = 0;
        let mut line_num = 1;
        let mut line_text = "";
        let mut col = self.pos;

        for (i, line) in lines.iter().enumerate() {
            let line_len = line.len() + 1; // +1 for newline
            if current_pos + line_len > self.pos {
                line_num = i + 1;
                line_text = line;
                col = self.pos - current_pos;
                break;
            }
            current_pos += line_len;
        }

        // Handle case where error is beyond the last line
        if line_text.is_empty() {
            if !lines.is_empty() {
                line_num = lines.len();
                line_text = lines[lines.len() - 1];
                col = line_text.len();
            } else {
                line_text = &self.text;
                col = self.pos;
            }
        }

        // Build the formatted error message
        let mut parts = vec![
            format!("STRling Parse Error: {}", self.message),
            String::new(),
            format!("> {} | {}", line_num, line_text),
            format!(">   | {}^", " ".repeat(col)),
        ];

        if let Some(ref hint) = self.hint {
            parts.push(String::new());
            parts.push(format!("Hint: {}", hint));
        }

        parts.join("\n")
    }

    /// Backwards/JS-friendly alias for getting the formatted error string.
    ///
    /// Returns the formatted error message (same as `Display` implementation).
    pub fn to_formatted_string(&self) -> String {
        self.format_error()
    }

    /// Convert the error to LSP Diagnostic format.
    ///
    /// Returns a dictionary compatible with the Language Server Protocol
    /// Diagnostic specification, which can be serialized to JSON for
    /// communication with LSP clients.
    ///
    /// # Returns
    ///
    /// A `serde_json::Value` containing:
    /// - range: The line/column range where the error occurred
    /// - severity: Error severity (1 = Error)
    /// - message: The error message with hint if available
    /// - source: "STRling"
    /// - code: A normalized error code derived from the message
    pub fn to_lsp_diagnostic(&self) -> serde_json::Value {
        // Find the line and column containing the error
        let lines: Vec<&str> = if !self.text.is_empty() {
            self.text.lines().collect()
        } else {
            vec![]
        };

        let mut current_pos = 0;
        let mut line_num = 0; // 0-indexed for LSP
        let mut col = self.pos;

        for (i, line) in lines.iter().enumerate() {
            let line_len = line.len() + 1; // +1 for newline
            if current_pos + line_len > self.pos {
                line_num = i;
                col = self.pos - current_pos;
                break;
            }
            current_pos += line_len;
        }

        // Handle case where error is beyond the last line
        if current_pos <= self.pos && !lines.is_empty() {
            line_num = lines.len() - 1;
            col = lines[lines.len() - 1].len();
        } else if lines.is_empty() {
            line_num = 0;
            col = self.pos;
        }

        // Build the diagnostic message
        let mut diagnostic_message = self.message.clone();
        if let Some(ref hint) = self.hint {
            diagnostic_message.push_str(&format!("\n\nHint: {}", hint));
        }

        // Create error code from message (normalize to snake_case)
        let mut error_code = self.message.to_lowercase();
        for ch in &[' ', '\'', '"', '(', ')', '[', ']', '{', '}', '\\', '/'] {
            error_code = error_code.replace(*ch, "_");
        }
        let error_code: String = error_code
            .split('_')
            .filter(|s| !s.is_empty())
            .collect::<Vec<_>>()
            .join("_");

        serde_json::json!({
            "range": {
                "start": {"line": line_num, "character": col},
                "end": {"line": line_num, "character": col + 1}
            },
            "severity": 1,  // 1 = Error, 2 = Warning, 3 = Information, 4 = Hint
            "message": diagnostic_message,
            "source": "STRling",
            "code": error_code
        })
    }
}

impl fmt::Display for STRlingParseError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(f, "{}", self.format_error())
    }
}

impl Error for STRlingParseError {}
