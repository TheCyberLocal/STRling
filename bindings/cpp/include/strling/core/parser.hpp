/**
 * @file parser.hpp
 * @brief STRling Parser - Recursive Descent Parser for STRling DSL
 * 
 * This module implements a hand-rolled recursive-descent parser that transforms
 * STRling pattern syntax into Abstract Syntax Tree (AST) nodes. The parser handles:
 *   - Alternation and sequencing
 *   - Character classes and ranges
 *   - Quantifiers (greedy, lazy, possessive)
 *   - Groups (capturing, non-capturing, named, atomic)
 *   - Lookarounds (lookahead and lookbehind, positive and negative)
 *   - Anchors and special escapes
 *   - Extended/free-spacing mode with comments
 * 
 * The parser produces AST nodes (defined in nodes.hpp) that can be compiled
 * to IR and ultimately emitted as target-specific regex patterns. It includes
 * comprehensive error handling with position tracking for helpful diagnostics.
 * 
 * @copyright Copyright (c) 2024 TheCyberLocal
 * @license MIT License
 */

#ifndef STRLING_CORE_PARSER_HPP
#define STRLING_CORE_PARSER_HPP

#include "strling/core/nodes.hpp"
#include "strling/core/strling_parse_error.hpp"
#include <string>
#include <tuple>
#include <memory>
#include <set>
#include <map>

namespace strling {
namespace core {

/// Alias for backward compatibility
using ParseError = STRlingParseError;

/**
 * @brief Cursor for tracking position during parsing
 * 
 * The cursor manages the current position in the input string and provides
 * methods for peeking, consuming characters, and handling whitespace in
 * extended mode.
 */
struct Cursor {
    std::string text;           ///< The input text being parsed
    size_t i = 0;               ///< Current position
    bool extended_mode = false; ///< Whether extended (free-spacing) mode is active
    int in_class = 0;           ///< Nesting count for character classes
    
    /**
     * @brief Check if we've reached end of input
     * @return true if at end of input
     */
    bool eof() const;
    
    /**
     * @brief Peek at a character without consuming it
     * @param n Offset from current position (default 0)
     * @return The character at position i+n, or empty string if past end
     */
    std::string peek(int n = 0) const;
    
    /**
     * @brief Consume and return the current character
     * @return The current character, or empty string if at end
     */
    std::string take();
    
    /**
     * @brief Try to match and consume a string
     * @param s The string to match
     * @return true if matched and consumed, false otherwise
     */
    bool match(const std::string& s);
    
    /**
     * @brief Skip whitespace and comments in extended mode
     * 
     * In free-spacing mode, ignores spaces/tabs/newlines and #-to-EOL comments.
     * Does nothing in normal mode or inside character classes.
     */
    void skip_ws_and_comments();
};

/**
 * @brief Main parser class for STRling patterns
 * 
 * The Parser implements a recursive descent parser that transforms STRling
 * DSL syntax into an Abstract Syntax Tree (AST) of Node objects.
 */
class Parser {
public:
    /**
     * @brief Construct a parser for the given pattern text
     * @param text The STRling pattern to parse (may include %flags directive)
     */
    explicit Parser(const std::string& text);
    
    /**
     * @brief Parse the pattern into an AST
     * @return The root Node of the parsed AST
     * @throws ParseError if the pattern is invalid
     */
    NodePtr parse();
    
    /**
     * @brief Get the parsed flags
     * @return The Flags object extracted from the pattern
     */
    const Flags& getFlags() const { return flags; }
    
private:
    std::string original_text;  ///< Original input for error reporting
    std::string src;            ///< Pattern source (without directives)
    Flags flags;                ///< Parsed flags
    Cursor cur;                 ///< Current parsing cursor
    int cap_count = 0;          ///< Count of capturing groups
    std::set<std::string> cap_names; ///< Names of named capturing groups
    
    /// Control escape sequences mapping
    std::map<std::string, std::string> CONTROL_ESCAPES;
    
    /**
     * @brief Raise a parse error with hint
     * @param message The error message
     * @param pos The position where the error occurred
     * @throws ParseError always
     */
    [[noreturn]] void raise_error(const std::string& message, size_t pos);
    
    /**
     * @brief Parse directives (%flags) from the input
     * @param text The full input text
     * @return Tuple of (flags, pattern_source)
     */
    std::tuple<Flags, std::string> parse_directives(const std::string& text);
    
    /**
     * @brief Parse an alternation (top-level)
     * @return The parsed Node (Alt if multiple branches, or single branch)
     */
    NodePtr parse_alt();
    
    /**
     * @brief Parse a sequence
     * @return The parsed Node (Seq if multiple parts, or single part)
     */
    NodePtr parse_seq();
    
    /**
     * @brief Parse an atom (literal, anchor, group, class, etc.)
     * @return The parsed Node, or nullptr if no atom found
     */
    NodePtr parse_atom();
    
    /**
     * @brief Parse a quantifier if present
     * @param child The node to quantify
     * @return Quant node if quantifier found, otherwise returns child unchanged
     */
    NodePtr parse_quantifier(NodePtr child);
    
    /**
     * @brief Parse an anchor (^, $, \b, \B, \A, \Z)
     * @return Anchor node if found, nullptr otherwise
     */
    NodePtr parse_anchor();
    
    /**
     * @brief Parse a group (capturing, non-capturing, atomic, etc.)
     * @return Group node
     */
    NodePtr parse_group();
    
    /**
     * @brief Parse a character class [...]
     * @return CharClass node
     */
    NodePtr parse_class();
    
    /**
     * @brief Parse a literal character or escape sequence
     * @return Lit node or other node type for special escapes
     */
    NodePtr parse_literal();
    
    /**
     * @brief Parse an escape sequence
     * @return The appropriate Node for the escape
     */
    NodePtr parse_escape();
};

/**
 * @brief Parse a STRling pattern and return flags and AST
 * 
 * This is the main entry point for parsing STRling patterns.
 * 
 * @param text The STRling pattern to parse
 * @return Tuple of (Flags, AST root node)
 * @throws ParseError if the pattern is invalid
 */
std::tuple<Flags, NodePtr> parse(const std::string& text);

} // namespace core
} // namespace strling

#endif // STRLING_CORE_PARSER_HPP
