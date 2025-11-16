/**
 * @file strling_parse_error.hpp
 * @brief STRling Error Classes - Rich Error Handling for Instructional Diagnostics
 * 
 * This module provides enhanced error classes that deliver context-aware,
 * instructional error messages. The STRlingParseError class stores detailed
 * information about syntax errors including position, context, and beginner-friendly
 * hints for resolution.
 * 
 * @copyright Copyright (c) 2024 TheCyberLocal
 * @license MIT License
 */

#ifndef STRLING_CORE_STRLING_PARSE_ERROR_HPP
#define STRLING_CORE_STRLING_PARSE_ERROR_HPP

#include <exception>
#include <string>
#include <optional>
#include <map>

namespace strling {
namespace core {

/**
 * @brief Rich parse error with position tracking and instructional hints.
 * 
 * This error class transforms parse failures into learning opportunities by
 * providing:
 * - The specific error message
 * - The exact position where the error occurred
 * - The full line of text containing the error
 * - A beginner-friendly hint explaining how to fix the issue
 */
class STRlingParseError : public std::exception {
public:
    /**
     * @brief Construct a new STRlingParseError object
     * 
     * @param message A concise description of what went wrong
     * @param pos The character position (0-indexed) where the error occurred
     * @param text The full input text being parsed (default: "")
     * @param hint An instructional hint explaining how to fix the error (default: std::nullopt)
     */
    STRlingParseError(
        const std::string& message,
        int pos,
        const std::string& text = "",
        const std::optional<std::string>& hint = std::nullopt
    );
    
    /**
     * @brief Get the error message (override from std::exception)
     * 
     * @return const char* The formatted error message
     */
    const char* what() const noexcept override;
    
    /**
     * @brief Get the concise error message
     * 
     * @return const std::string& The error message
     */
    const std::string& getMessage() const { return message_; }
    
    /**
     * @brief Get the error position
     * 
     * @return int The character position where the error occurred
     */
    int getPos() const { return pos_; }
    
    /**
     * @brief Get the input text
     * 
     * @return const std::string& The full input text
     */
    const std::string& getText() const { return text_; }
    
    /**
     * @brief Get the hint (if any)
     * 
     * @return const std::optional<std::string>& The hint explaining how to fix the error
     */
    const std::optional<std::string>& getHint() const { return hint_; }
    
    /**
     * @brief Get the formatted error string
     * 
     * Returns the error in a visionary state format with context and hints.
     * 
     * @return std::string The formatted error message
     */
    std::string toFormattedString() const;
    
    /**
     * @brief Convert the error to LSP Diagnostic format
     * 
     * Returns a dictionary compatible with the Language Server Protocol
     * Diagnostic specification, which can be serialized to JSON for
     * communication with LSP clients.
     * 
     * @return std::map<std::string, std::map<std::string, std::variant<...>>> LSP diagnostic data
     */
    std::map<std::string, std::string> toLspDiagnostic() const;

private:
    std::string message_;              ///< A concise description of what went wrong
    int pos_;                          ///< The character position (0-indexed) where the error occurred
    std::string text_;                 ///< The full input text being parsed
    std::optional<std::string> hint_;  ///< An instructional hint explaining how to fix the error
    mutable std::string formatted_;    ///< Cached formatted error message
    
    /**
     * @brief Format the error in the visionary state format
     * 
     * @return std::string The formatted error message with context and hints
     */
    std::string formatError() const;
};

} // namespace core
} // namespace strling

#endif // STRLING_CORE_STRLING_PARSE_ERROR_HPP
