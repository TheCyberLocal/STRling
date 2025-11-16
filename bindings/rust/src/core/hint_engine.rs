//! STRling Hint Engine - Context-Aware Error Hints
//!
//! This module provides intelligent, beginner-friendly hints for common syntax errors.
//! The hint engine maps specific error types and contexts to instructional messages
//! that help users understand and fix their mistakes.

/// Get a hint for a given error message and context
///
/// # Arguments
///
/// * `error_message` - The error message from the parser
/// * `text` - The full input text being parsed
/// * `pos` - The position where the error occurred
///
/// # Returns
///
/// An optional hint string providing guidance on how to fix the error
pub fn get_hint(error_message: &str, text: &str, pos: usize) -> Option<String> {
    // TODO: Implement full hint engine logic from Python
    
    if error_message.contains("Unterminated group") {
        return Some(
            "This group was opened with '(' but never closed. \
            Add a matching ')' to close the group.".to_string()
        );
    }
    
    if error_message.contains("Unterminated character class") {
        return Some(
            "This character class was opened with '[' but never closed. \
            Add a matching ']' to close the character class.".to_string()
        );
    }
    
    if error_message.contains("Empty character class") {
        return Some(
            "Character classes must contain at least one item. \
            Add characters, ranges, or escapes inside the brackets.".to_string()
        );
    }
    
    if error_message.contains("Invalid flag") {
        return Some(
            "Valid flags are: i (case-insensitive), m (multiline), s (dotall), \
            u (unicode), x (extended/free-spacing).".to_string()
        );
    }
    
    if error_message.contains("Alternation lacks left-hand side") {
        return Some(
            "An alternation '|' must have content on both sides. \
            Remove the leading '|' or add content before it.".to_string()
        );
    }
    
    if error_message.contains("Alternation lacks right-hand side") {
        return Some(
            "An alternation '|' must have content on both sides. \
            Remove the trailing '|' or add content after it.".to_string()
        );
    }
    
    if error_message.contains("Empty alternation branch") {
        return Some(
            "Each branch of an alternation must contain at least one item. \
            Remove the extra '|' or add content between the pipes.".to_string()
        );
    }
    
    if error_message.contains("Unexpected trailing input") {
        return Some(
            "There is unexpected content at the end of the pattern. \
            Check for unmatched parentheses or other syntax errors.".to_string()
        );
    }
    
    None
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_unterminated_group_hint() {
        let hint = get_hint("Unterminated group", "test", 0);
        assert!(hint.is_some());
        assert!(hint.unwrap().contains("matching ')'"));
    }

    #[test]
    fn test_invalid_flag_hint() {
        let hint = get_hint("Invalid flag 'z'", "test", 0);
        assert!(hint.is_some());
        assert!(hint.unwrap().contains("Valid flags"));
    }

    #[test]
    fn test_no_hint_for_unknown_error() {
        let hint = get_hint("Some unknown error", "test", 0);
        assert!(hint.is_none());
    }
}
