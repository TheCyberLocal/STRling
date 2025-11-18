/**
 * @file parser.cpp
 * @brief Implementation of STRling Parser
 * 
 * This is a PARTIAL implementation demonstrating the pattern for porting
 * the Python parser to C++. A full implementation would require significant
 * additional development (est. 1000+ lines of complex parsing logic).
 * 
 * @copyright Copyright (c) 2024 TheCyberLocal
 * @license MIT License
 */

#include "strling/core/parser.hpp"
#include <algorithm>
#include <sstream>
#include <regex>
#include <cctype>

namespace strling {
namespace core {

// ============================================================================
// Cursor Implementation
// ============================================================================

bool Cursor::eof() const {
    return i >= text.length();
}

std::string Cursor::peek(int n) const {
    size_t j = i + n;
    if (j >= text.length()) {
        return "";
    }
    return std::string(1, text[j]);
}

std::string Cursor::take() {
    if (eof()) {
        return "";
    }
    std::string ch(1, text[i]);
    i++;
    return ch;
}

bool Cursor::match(const std::string& s) {
    if (text.substr(i, s.length()) == s) {
        i += s.length();
        return true;
    }
    return false;
}

void Cursor::skip_ws_and_comments() {
    if (!extended_mode || in_class > 0) {
        return;
    }
    // In free-spacing mode, ignore spaces/tabs/newlines and #-to-EOL comments
    while (!eof()) {
        char ch = text[i];
        if (ch == ' ' || ch == '\t' || ch == '\r' || ch == '\n') {
            i++;
            continue;
        }
        if (ch == '#') {
            // Skip comment to end of line
            while (!eof() && text[i] != '\r' && text[i] != '\n') {
                i++;
            }
            continue;
        }
        break;
    }
}

// ============================================================================
// Parser Implementation
// ============================================================================

Parser::Parser(const std::string& text)
    : original_text(text)
{
    // Initialize control escapes
    CONTROL_ESCAPES = {
        {"n", "\n"},
        {"r", "\r"},
        {"t", "\t"},
        {"f", "\f"},
        {"v", "\v"}
    };
    
    // Parse directives and extract pattern
    auto [parsed_flags, pattern] = parse_directives(text);
    flags = parsed_flags;
    src = pattern;
    
    // Initialize cursor
    cur.text = src;
    cur.i = 0;
    cur.extended_mode = flags.extended;
    cur.in_class = 0;
}

void Parser::raise_error(const std::string& message, size_t pos) {
    // For now, simplified error - would need hint_engine implementation
    throw STRlingParseError(message, static_cast<int>(pos), src, "");
}

std::tuple<Flags, std::string> Parser::parse_directives(const std::string& text) {
    Flags flags;
    std::vector<std::string> pattern_lines;
    bool in_pattern = false;
    
    // Split into lines preserving line endings
    std::vector<std::string> lines;
    size_t start = 0;
    size_t pos = 0;
    while (pos < text.length()) {
        if (text[pos] == '\n') {
            lines.push_back(text.substr(start, pos - start + 1));
            start = pos + 1;
        }
        pos++;
    }
    if (start < text.length()) {
        lines.push_back(text.substr(start));
    }
    if (lines.empty()) {
        lines.push_back(text);
    }
    
    size_t line_num = 0;
    for (const auto& line : lines) {
        line_num++;
        
        // Trim whitespace for checking
        std::string stripped = line;
        size_t first = stripped.find_first_not_of(" \t\r\n");
        size_t last = stripped.find_last_not_of(" \t\r\n");
        if (first != std::string::npos) {
            stripped = stripped.substr(first, last - first + 1);
        } else {
            stripped = "";
        }
        
        // Skip leading blank lines or comments
        if (!in_pattern && (stripped.empty() || stripped[0] == '#')) {
            continue;
        }
        
        // Process %flags directive
        if (!in_pattern && stripped.find("%flags") == 0) {
            size_t idx = line.find("%flags");
            std::string after;
            if (idx + 7 < line.length()) {
                after = line.substr(idx + 7);  // 7 = len("%flags")
            }
            
            // Scan for valid flag characters
            std::string allowed_chars = " ,\t[]imsuxIMSUX\r\n";
            size_t j = 0;
            while (j < after.length() && allowed_chars.find(after[j]) != std::string::npos) {
                j++;
            }
            
            std::string flags_token = after.substr(0, j);
            std::string remainder = j < after.length() ? after.substr(j) : "";
            
            // Normalize and extract flag letters
            std::string letters;
            for (char ch : flags_token) {
                if (ch == 'i' || ch == 'm' || ch == 's' || ch == 'u' || ch == 'x' ||
                    ch == 'I' || ch == 'M' || ch == 'S' || ch == 'U' || ch == 'X') {
                    letters += std::tolower(ch);
                }
            }
            
            // Check if we have remainder that isn't just whitespace (invalid flag)
            if (j < after.length()) {
                std::string rem_check = remainder;
                size_t first_non_ws = rem_check.find_first_not_of(" \t\r\n");
                if (first_non_ws != std::string::npos) {
                    char invalid_char = rem_check[first_non_ws];
                    size_t error_pos = 0;
                    for (size_t i = 0; i < line_num - 1; i++) {
                        error_pos += lines[i].length();
                    }
                    error_pos += idx + 7 + j + first_non_ws;
                    raise_error(std::string("Invalid flag '") + invalid_char + "'", error_pos);
                }
            }
            
            // Check for invalid flags
            std::string valid_flags = "imsux";
            for (char ch : letters) {
                if (valid_flags.find(ch) == std::string::npos && ch != ' ') {
                    size_t error_pos = 0;
                    for (size_t i = 0; i < line_num - 1; i++) {
                        error_pos += lines[i].length();
                    }
                    error_pos += idx;
                    raise_error(std::string("Invalid flag '") + ch + "'", error_pos);
                }
            }
            
            // Set flags
            if (!letters.empty()) {
                flags = Flags::fromLetters(letters);
            }
            
            // Check if there's pattern content on the same line
            std::string remainder_trimmed = remainder;
            size_t rem_first = remainder_trimmed.find_first_not_of(" \t\r\n");
            if (rem_first != std::string::npos) {
                remainder_trimmed = remainder_trimmed.substr(rem_first);
                if (!remainder_trimmed.empty()) {
                    in_pattern = true;
                    pattern_lines.push_back(remainder);
                }
            }
            continue;
        }
        
        // Skip other directives, but check for malformed %flags
        if (!in_pattern && stripped[0] == '%') {
            // Check if it looks like a malformed %flags directive
            if (stripped.length() >= 5 && stripped.substr(0, 5) == "%flag" && 
                stripped.substr(0, 6) != "%flags") {
                // Malformed %flags directive
                size_t error_pos = 0;
                for (size_t i = 0; i < line_num - 1; i++) {
                    error_pos += lines[i].length();
                }
                error_pos += line.find("%flag");
                raise_error("Unknown directive (did you mean %flags?)", error_pos);
            }
            continue;
        }
        
        // This is pattern content
        // Check if %flags appears anywhere in this line (would be misplaced)
        if (line.find("%flags") != std::string::npos) {
            size_t error_pos = 0;
            for (size_t i = 0; i < line_num - 1; i++) {
                error_pos += lines[i].length();
            }
            error_pos += line.find("%flags");
            raise_error("Directive after pattern content", error_pos);
        }
        
        // All other lines are pattern content
        in_pattern = true;
        pattern_lines.push_back(line);
    }
    
    // Join all pattern lines
    std::string pattern;
    for (const auto& pline : pattern_lines) {
        pattern += pline;
    }
    
    return {flags, pattern};
}

NodePtr Parser::parse() {
    NodePtr result = parse_alt();
    
    // Ensure we consumed all input
    cur.skip_ws_and_comments();
    if (!cur.eof()) {
        raise_error("Unexpected trailing input", cur.i);
    }
    
    return result;
}

NodePtr Parser::parse_alt() {
    std::vector<NodePtr> branches;
    branches.push_back(parse_seq());
    
    while (cur.peek() == "|") {
        cur.take(); // consume '|'
        cur.skip_ws_and_comments();
        branches.push_back(parse_seq());
    }
    
    if (branches.size() == 1) {
        return std::move(branches[0]);
    }
    
    return std::make_unique<Alt>(std::move(branches));
}

NodePtr Parser::parse_seq() {
    std::vector<NodePtr> parts;
    
    cur.skip_ws_and_comments();
    
    while (!cur.eof()) {
        // Check for sequence terminators
        std::string peek_ch = cur.peek();
        if (peek_ch == "|" || peek_ch == ")") {
            break;
        }
        
        NodePtr atom = parse_atom();
        if (!atom) {
            break;
        }
        
        // Try to parse quantifier
        atom = parse_quantifier(std::move(atom));
        parts.push_back(std::move(atom));
        
        cur.skip_ws_and_comments();
    }
    
    if (parts.empty()) {
        // Empty sequence - return empty Seq
        return std::make_unique<Seq>(std::vector<NodePtr>());
    }
    
    if (parts.size() == 1) {
        return std::move(parts[0]);
    }
    
    return std::make_unique<Seq>(std::move(parts));
}

NodePtr Parser::parse_atom() {
    cur.skip_ws_and_comments();
    
    if (cur.eof()) {
        return nullptr;
    }
    
    // Try anchor first
    NodePtr anchor = parse_anchor();
    if (anchor) {
        return anchor;
    }
    
    std::string ch = cur.peek();
    
    // Dot
    if (ch == ".") {
        cur.take();
        return std::make_unique<Dot>();
    }
    
    // Group
    if (ch == "(") {
        return parse_group();
    }
    
    // Character class
    if (ch == "[") {
        return parse_class();
    }
    
    // Literal or escape
    return parse_literal();
}

NodePtr Parser::parse_anchor() {
    std::string ch = cur.peek();
    
    if (ch == "^") {
        cur.take();
        return std::make_unique<Anchor>("Start");
    }
    
    if (ch == "$") {
        cur.take();
        return std::make_unique<Anchor>("End");
    }
    
    // Check for escape sequences
    if (ch == "\\") {
        std::string next = cur.peek(1);
        
        if (next == "b") {
            cur.take(); // consume '\'
            cur.take(); // consume 'b'
            return std::make_unique<Anchor>("WordBoundary");
        }
        
        if (next == "B") {
            cur.take(); // consume '\'
            cur.take(); // consume 'B'
            return std::make_unique<Anchor>("NotWordBoundary");
        }
        
        if (next == "A") {
            cur.take(); // consume '\'
            cur.take(); // consume 'A'
            return std::make_unique<Anchor>("AbsoluteStart");
        }
        
        if (next == "Z") {
            cur.take(); // consume '\'
            cur.take(); // consume 'Z'
            return std::make_unique<Anchor>("EndBeforeFinalNewline");
        }
    }
    
    return nullptr;
}

NodePtr Parser::parse_quantifier(NodePtr child) {
    // Check if child can be quantified
    if (dynamic_cast<Anchor*>(child.get())) {
        // Check if next char is a quantifier
        std::string ch = cur.peek();
        if (ch == "*" || ch == "+" || ch == "?" || ch == "{") {
            raise_error("Cannot quantify anchor", cur.i);
        }
        return child;
    }
    
    std::string ch = cur.peek();
    
    if (ch == "*") {
        cur.take();
        // Check for lazy/possessive mode
        std::string mode = "Greedy";
        if (cur.peek() == "?") {
            cur.take();
            mode = "Lazy";
        } else if (cur.peek() == "+") {
            cur.take();
            mode = "Possessive";
        }
        return std::make_unique<Quant>(std::move(child), 0, "inf", mode);
    }
    
    if (ch == "+") {
        cur.take();
        std::string mode = "Greedy";
        if (cur.peek() == "?") {
            cur.take();
            mode = "Lazy";
        } else if (cur.peek() == "+") {
            cur.take();
            mode = "Possessive";
        }
        return std::make_unique<Quant>(std::move(child), 1, "inf", mode);
    }
    
    if (ch == "?") {
        cur.take();
        std::string mode = "Greedy";
        if (cur.peek() == "?") {
            cur.take();
            mode = "Lazy";
        } else if (cur.peek() == "+") {
            cur.take();
            mode = "Possessive";
        }
        return std::make_unique<Quant>(std::move(child), 0, 1, mode);
    }
    
    // TODO: Handle {m,n} quantifiers
    
    return child;
}

NodePtr Parser::parse_group() {
    if (cur.peek() != "(") {
        raise_error("Expected '('", cur.i);
    }
    
    cur.take(); // consume '('
    
    // Check for group modifiers
    bool capturing = true;
    bool atomic = false;
    std::optional<std::string> name;
    std::string look_dir;
    bool look_neg = false;
    
    if (cur.peek() == "?") {
        cur.take(); // consume '?'
        std::string modifier = cur.peek();
        
        if (modifier == ":") {
            cur.take();
            capturing = false;
        } else if (modifier == ">") {
            cur.take();
            capturing = false;
            atomic = true;
        } else if (modifier == "=") {
            // Positive lookahead
            cur.take();
            NodePtr body = parse_alt();
            if (cur.peek() != ")") {
                raise_error("Expected ')'", cur.i);
            }
            cur.take();
            return std::make_unique<Look>("Ahead", false, std::move(body));
        } else if (modifier == "!") {
            // Negative lookahead
            cur.take();
            NodePtr body = parse_alt();
            if (cur.peek() != ")") {
                raise_error("Expected ')'", cur.i);
            }
            cur.take();
            return std::make_unique<Look>("Ahead", true, std::move(body));
        } else if (modifier == "<") {
            // Lookbehind
            cur.take();
            std::string next = cur.peek();
            if (next == "=") {
                cur.take();
                look_neg = false;
            } else if (next == "!") {
                cur.take();
                look_neg = true;
            }
            NodePtr body = parse_alt();
            if (cur.peek() != ")") {
                raise_error("Expected ')'", cur.i);
            }
            cur.take();
            return std::make_unique<Look>("Behind", look_neg, std::move(body));
        }
        // TODO: Handle named groups
    }
    
    // Parse group body
    NodePtr body = parse_alt();
    
    if (cur.peek() != ")") {
        raise_error("Expected ')'", cur.i);
    }
    cur.take(); // consume ')'
    
    if (capturing) {
        cap_count++;
    }
    
    auto group = std::make_unique<Group>(capturing, std::move(body), name, atomic);
    
    return group;
}

NodePtr Parser::parse_class() {
    // Simplified character class parsing
    if (cur.peek() != "[") {
        raise_error("Expected '['", cur.i);
    }
    
    cur.take(); // consume '['
    cur.in_class++;
    
    bool negated = false;
    if (cur.peek() == "^") {
        cur.take();
        negated = true;
    }
    
    std::vector<ClassItemPtr> items;
    
    // Parse class items (simplified)
    while (!cur.eof() && cur.peek() != "]") {
        std::string ch = cur.peek();
        
        if (ch == "\\") {
            // Escape sequence
            cur.take();
            std::string esc = cur.take();
            
            if (esc == "d" || esc == "D" || esc == "w" || esc == "W" || 
                esc == "s" || esc == "S") {
                items.push_back(std::make_unique<ClassEscape>(esc));
            } else {
                // Literal escaped character
                items.push_back(std::make_unique<ClassLiteral>(esc));
            }
        } else {
            // Check for range
            std::string next = cur.peek(1);
            if (next == "-" && cur.peek(2) != "]") {
                std::string from_ch = cur.take();
                cur.take(); // consume '-'
                std::string to_ch = cur.take();
                items.push_back(std::make_unique<ClassRange>(from_ch, to_ch));
            } else {
                // Literal character
                std::string lit = cur.take();
                items.push_back(std::make_unique<ClassLiteral>(lit));
            }
        }
    }
    
    if (cur.peek() != "]") {
        raise_error("Expected ']'", cur.i);
    }
    
    cur.take(); // consume ']'
    cur.in_class--;
    
    return std::make_unique<CharClass>(negated, std::move(items));
}

NodePtr Parser::parse_literal() {
    std::string ch = cur.peek();
    
    if (ch == "\\") {
        return parse_escape();
    }
    
    // Regular literal character
    if (!ch.empty() && ch[0] != '|' && ch[0] != ')' && ch[0] != '*' && 
        ch[0] != '+' && ch[0] != '?' && ch[0] != '{') {
        cur.take();
        return std::make_unique<Lit>(ch);
    }
    
    return nullptr;
}

NodePtr Parser::parse_escape() {
    if (cur.peek() != "\\") {
        raise_error("Expected '\\'", cur.i);
    }
    
    cur.take(); // consume '\'
    std::string esc = cur.peek();
    
    if (esc.empty()) {
        raise_error("Incomplete escape sequence", cur.i - 1);
    }
    
    cur.take(); // consume escape character
    
    // Control escapes
    if (CONTROL_ESCAPES.count(esc)) {
        return std::make_unique<Lit>(CONTROL_ESCAPES[esc]);
    }
    
    // Character class shortcuts
    if (esc == "d" || esc == "D" || esc == "w" || esc == "W" || 
        esc == "s" || esc == "S") {
        // These should return CharClass nodes, but for simplicity treating as escape
        std::vector<ClassItemPtr> items;
        items.push_back(std::make_unique<ClassEscape>(esc));
        bool negated = (esc == "D" || esc == "W" || esc == "S");
        return std::make_unique<CharClass>(negated, std::move(items));
    }
    
    // Backreference
    if (std::isdigit(esc[0])) {
        int num = esc[0] - '0';
        return std::make_unique<Backref>(num);
    }
    
    // Unknown escape - for now, treat as literal
    // Full implementation would have comprehensive escape handling
    if (esc == "z") {
        raise_error("Unknown escape sequence \\z", cur.i - 2);
    }
    
    // Literal escaped character
    return std::make_unique<Lit>(esc);
}

// ============================================================================
// Public Parse Function
// ============================================================================

std::tuple<Flags, NodePtr> parse(const std::string& text) {
    Parser parser(text);
    NodePtr ast = parser.parse();
    return {parser.getFlags(), std::move(ast)};
}

} // namespace core
} // namespace strling
