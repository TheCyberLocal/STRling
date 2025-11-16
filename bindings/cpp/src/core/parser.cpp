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
    // Simplified directive parsing - full implementation would be more complex
    Flags f;
    std::string pattern = text;
    
    // Check for %flags directive at start
    if (text.find("%flags") == 0) {
        size_t end_of_line = text.find('\n');
        if (end_of_line != std::string::npos) {
            std::string flags_line = text.substr(0, end_of_line);
            pattern = text.substr(end_of_line + 1);
            
            // Extract flag letters
            std::string flag_letters;
            for (char ch : flags_line) {
                if (ch == 'i' || ch == 'm' || ch == 's' || ch == 'u' || ch == 'x') {
                    flag_letters += ch;
                }
            }
            
            f = Flags::fromLetters(flag_letters);
        }
    }
    
    return {f, pattern};
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
        // Empty sequence - return empty Lit
        return std::make_unique<Lit>("");
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
