/**
 * @file hint_engine.hpp
 * @brief STRling Hint Engine — Context-Aware Error Hints (C++ Binding)
 *
 * Provides intelligent, beginner-friendly hints for common syntax errors.
 * Maps specific error types and contexts to instructional messages that
 * help users understand and fix their mistakes.
 *
 * Mirrors the TypeScript reference implementation pattern-for-pattern.
 *
 * @copyright Copyright (c) 2024 STRling Team
 * @license MIT License
 */

#ifndef STRLING_CORE_HINT_ENGINE_HPP
#define STRLING_CORE_HINT_ENGINE_HPP

#include <string>
#include <optional>

namespace strling {
namespace core {

/// Generic fallback hint used when no specific hint pattern matches.
inline constexpr const char* GENERIC_HINT_FALLBACK =
    "Check the STRling documentation for help with this syntax.";

/**
 * @brief Get a context-aware hint for the given parse error.
 *
 * @param errorMessage The error message string from the parser
 * @param text The full input text being parsed
 * @param pos The position where the error occurred
 * @return A helpful hint string, or std::nullopt if no specific hint matches
 */
std::optional<std::string> getHint(const std::string& errorMessage,
                                    const std::string& text,
                                    size_t pos);

/**
 * @brief Get a hint for the given error, falling back to the generic hint.
 *
 * @param errorMessage The error message string from the parser
 * @param text The full input text being parsed
 * @param pos The position where the error occurred
 * @return A helpful hint string (never empty)
 */
std::string getHintOrFallback(const std::string& errorMessage,
                               const std::string& text,
                               size_t pos);

} // namespace core
} // namespace strling

#endif // STRLING_CORE_HINT_ENGINE_HPP
