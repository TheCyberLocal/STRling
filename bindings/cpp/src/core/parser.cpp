/**
 * @file parser.cpp
 * @brief Implementation of STRling Parser
 * @copyright Copyright (c) 2024 STRling Team
 * @license Apache License 2.0
 */

#include "strling/core/parser.hpp"
#include "strling/core/hint_engine.hpp"
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
    while (!eof()) {
        char ch = text[i];
        if (ch == ' ' || ch == '\t' || ch == '\r' || ch == '\n') {
            i++;
            continue;
        }
        if (ch == '#') {
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
    CONTROL_ESCAPES = {
        {"n", "\n"}, {"r", "\r"}, {"t", "\t"}, {"f", "\f"}, {"v", "\v"}
    };

    auto [parsed_flags, pattern] = parse_directives(text);
    flags = parsed_flags;
    src = pattern;

    cur.text = src;
    cur.i = 0;
    cur.extended_mode = flags.extended;
    cur.in_class = 0;
}

void Parser::raise_error(const std::string& message, size_t pos) {
    auto hint = getHintOrFallback(message, src, pos);
    throw STRlingParseError(message, static_cast<int>(pos), src, hint);
}

std::tuple<Flags, std::string> Parser::parse_directives(const std::string& text) {
    Flags flags;
    std::vector<std::string> pattern_lines;
    bool in_pattern = false;

    std::vector<std::string> lines;
    std::istringstream stream(text);
    std::string line;
    while (std::getline(stream, line)) {
        lines.push_back(line);
    }
    if (lines.empty()) {
        lines.push_back(text);
    }

    for (const auto& raw_line : lines) {
        std::string stripped = raw_line;
        size_t first = stripped.find_first_not_of(" \t\r\n");
        size_t last = stripped.find_last_not_of(" \t\r\n");
        if (first != std::string::npos) {
            stripped = stripped.substr(first, last - first + 1);
        } else {
            stripped = "";
        }

        if (!in_pattern && (stripped.empty() || stripped[0] == '#')) {
            continue;
        }

        if (stripped.size() > 0 && stripped[0] == '%') {
            if (in_pattern) {
                auto hint = getHintOrFallback("Directive after pattern", text, 0);
                throw STRlingParseError("Directive after pattern", 0, text, hint);
            }
            if (stripped.substr(0, 6) != "%flags") {
                auto hint = getHintOrFallback("Malformed directive", text, 0);
                throw STRlingParseError("Malformed directive", 0, text, hint);
            }

            size_t idx = raw_line.find("%flags");
            std::string after = (idx + 6 < raw_line.size()) ? raw_line.substr(idx + 6) : "";
            std::string allowed = " ,\t[]imsuxIMSUX";

            size_t j = 0;
            while (j < after.size() && allowed.find(after[j]) != std::string::npos) {
                j++;
            }

            std::string flags_token = after.substr(0, j);
            std::string remainder = (j < after.size()) ? after.substr(j) : "";

            std::string letters;
            for (char ch : flags_token) {
                if (std::isalpha(static_cast<unsigned char>(ch))) {
                    letters += std::tolower(ch);
                }
            }

            std::string valid_flags = "imsux";
            for (char ch : letters) {
                if (valid_flags.find(ch) == std::string::npos) {
                    std::string msg = std::string("Invalid flag '") + ch + "'";
                    auto hint = getHintOrFallback(msg, text, 0);
                    throw STRlingParseError(msg, 0, text, hint);
                }
            }

            if (!letters.empty()) {
                flags = Flags::fromLetters(letters);
            } else {
                // Check remainder for invalid flag
                size_t rem_first = remainder.find_first_not_of(" \t\r\n");
                if (rem_first != std::string::npos) {
                    char ch = remainder[rem_first];
                    std::string msg = std::string("Invalid flag '") + ch + "'";
                    auto hint = getHintOrFallback(msg, text, 0);
                    throw STRlingParseError(msg, 0, text, hint);
                }
            }

            // Check if there's pattern content in remainder
            size_t rem_first = remainder.find_first_not_of(" \t\r\n");
            if (rem_first != std::string::npos) {
                pattern_lines.push_back(remainder);
                in_pattern = true;
            }
            continue;
        }

        // Check for directive after pattern
        if (raw_line.find("%flags") != std::string::npos) {
            auto hint = getHintOrFallback("Directive after pattern", text, 0);
            throw STRlingParseError("Directive after pattern", 0, text, hint);
        }

        in_pattern = true;
        pattern_lines.push_back(raw_line);
    }

    std::string pattern;
    for (size_t i = 0; i < pattern_lines.size(); i++) {
        if (i > 0) pattern += "\n";
        pattern += pattern_lines[i];
    }

    return {flags, pattern};
}

NodePtr Parser::parse() {
    cur.skip_ws_and_comments();
    if (cur.eof()) {
        std::vector<NodePtr> empty;
        return std::make_unique<Seq>(std::move(empty));
    }

    NodePtr result = parse_alt();

    cur.skip_ws_and_comments();
    if (!cur.eof()) {
        if (cur.peek() == ")") {
            raise_error("Unmatched ')'", cur.i);
        }
        raise_error("Unexpected trailing input", cur.i);
    }

    return result;
}

NodePtr Parser::parse_alt() {
    cur.skip_ws_and_comments();

    if (cur.peek() == "|") {
        raise_error("Alternation lacks left-hand side", cur.i);
    }

    std::vector<NodePtr> branches;
    branches.push_back(parse_seq());

    cur.skip_ws_and_comments();
    while (cur.peek() == "|") {
        size_t pipe_pos = cur.i;
        cur.take(); // consume '|'
        cur.skip_ws_and_comments();

        if (cur.eof()) {
            raise_error("Alternation lacks right-hand side", pipe_pos);
        }
        if (cur.peek() == "|") {
            raise_error("Empty alternation", pipe_pos);
        }
        if (cur.peek() == ")") {
            raise_error("Alternation lacks right-hand side", pipe_pos);
        }

        branches.push_back(parse_seq());
        cur.skip_ws_and_comments();
    }

    if (branches.size() == 1) {
        return std::move(branches[0]);
    }

    return std::make_unique<Alt>(std::move(branches));
}

NodePtr Parser::parse_seq() {
    std::vector<NodePtr> parts;

    while (true) {
        cur.skip_ws_and_comments();
        std::string ch = cur.peek();
        if (ch.empty() || ch == "|" || ch == ")") break;

        NodePtr atom = parse_atom();
        if (!atom) break;

        cur.skip_ws_and_comments();
        atom = parse_quantifier(std::move(atom));
        parts.push_back(std::move(atom));
    }

    if (parts.empty()) {
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
        raise_error("Unexpected end of input", cur.i);
    }

    std::string ch = cur.peek();

    if (ch == ".") { cur.take(); return std::make_unique<Dot>(); }
    if (ch == "^") { cur.take(); return std::make_unique<Anchor>("Start"); }
    if (ch == "$") { cur.take(); return std::make_unique<Anchor>("End"); }
    if (ch == "(") { return parse_group(); }
    if (ch == "[") { return parse_class(); }
    if (ch == "\\") { return parse_escape(); }

    if (ch == "*" || ch == "+" || ch == "?") {
        raise_error("Invalid quantifier '" + ch + "'", cur.i);
    }

    if (ch == "{") {
        size_t save = cur.i;
        // Look ahead for brace content
        std::string look;
        size_t j = cur.i + 1;
        while (j < cur.text.size() && cur.text[j] != '}') {
            look += cur.text[j];
            j++;
        }
        if (j < cur.text.size() && !look.empty()) {
            // Check if content is valid quantifier format
            // Must be digits, optionally followed by comma and optional digits
            std::regex quant_re("^\\d+(,\\d*)?$");
            if (!std::regex_match(look, quant_re)) {
                raise_error("Brace quantifier: Invalid brace quantifier content", save);
            }
        }
        raise_error("Invalid quantifier '" + ch + "'", cur.i);
    }

    // Regular literal
    cur.take();
    return std::make_unique<Lit>(ch);
}

NodePtr Parser::parse_anchor() {
    // Not used in new design - anchors handled in parse_atom
    return nullptr;
}

NodePtr Parser::parse_quantifier(NodePtr child) {
    cur.skip_ws_and_comments();
    std::string ch = cur.peek();
    if (ch.empty()) return child;
    if (ch != "*" && ch != "+" && ch != "?" && ch != "{") return child;

    size_t start_pos = cur.i;
    int min = 0;
    std::variant<int, std::string> max_var = 0;

    if (ch == "*") {
        cur.take();
        min = 0; max_var = std::string("inf");
    } else if (ch == "+") {
        cur.take();
        min = 1; max_var = std::string("inf");
    } else if (ch == "?") {
        cur.take();
        min = 0; max_var = 1;
    } else if (ch == "{") {
        size_t save = cur.i;
        cur.take(); // consume '{'

        // Look ahead for invalid brace content
        std::string look;
        size_t j = cur.i;
        while (j < cur.text.size() && cur.text[j] != '}') {
            look += cur.text[j];
            j++;
        }
        if (j < cur.text.size() && !look.empty()) {
            std::regex quant_re("^\\d+(,\\d*)?$");
            if (!std::regex_match(look, quant_re)) {
                raise_error("Brace quantifier: Invalid brace quantifier content", save);
            }
        }

        std::string min_str;
        while (!cur.eof() && !cur.peek().empty() && std::isdigit(cur.peek()[0])) {
            min_str += cur.take();
        }
        if (min_str.empty()) {
            raise_error("Incomplete quantifier", cur.i);
        }
        min = std::stoi(min_str);

        if (cur.peek() == ",") {
            cur.take(); // consume ','
            if (cur.peek() == "}") {
                max_var = std::string("inf");
            } else {
                std::string max_str;
                while (!cur.eof() && !cur.peek().empty() && std::isdigit(cur.peek()[0])) {
                    max_str += cur.take();
                }
                if (max_str.empty()) {
                    raise_error("Incomplete quantifier", cur.i);
                }
                max_var = std::stoi(max_str);
            }
        } else {
            max_var = min;
        }

        if (!cur.match("}")) {
            raise_error("Incomplete quantifier", cur.i);
        }

        // Check range
        if (auto* max_int = std::get_if<int>(&max_var)) {
            if (min > *max_int) {
                raise_error("Invalid quantifier range", save);
            }
        }
    } else {
        return child;
    }

    // Cannot quantify anchor
    if (dynamic_cast<Anchor*>(child.get())) {
        raise_error("Cannot quantify anchor", start_pos);
    }

    std::string mode = "Greedy";
    if (cur.peek() == "?") { cur.take(); mode = "Lazy"; }
    else if (cur.peek() == "+") { cur.take(); mode = "Possessive"; }

    return std::make_unique<Quant>(std::move(child), min, max_var, mode);
}

NodePtr Parser::parse_group() {
    size_t start_pos = cur.i;
    cur.take(); // consume '('

    if (cur.peek() == "?") {
        cur.take(); // consume '?'
        std::string next = cur.peek();

        if (next == ":") {
            cur.take();
            NodePtr body = parse_alt();
            if (!cur.match(")")) {
                raise_error("Unterminated group", cur.i);
            }
            return std::make_unique<Group>(false, std::move(body));
        }
        if (next == "=") {
            cur.take();
            NodePtr body = parse_alt();
            if (!cur.match(")")) {
                raise_error("Unterminated lookahead", cur.i);
            }
            return std::make_unique<Look>("Ahead", false, std::move(body));
        }
        if (next == "!") {
            cur.take();
            NodePtr body = parse_alt();
            if (!cur.match(")")) {
                raise_error("Unterminated lookahead", cur.i);
            }
            return std::make_unique<Look>("Ahead", true, std::move(body));
        }
        if (next == "<") {
            cur.take();
            if (cur.peek() == "=") {
                cur.take();
                NodePtr body = parse_alt();
                if (!cur.match(")")) {
                    raise_error("Unterminated lookbehind", cur.i);
                }
                return std::make_unique<Look>("Behind", false, std::move(body));
            }
            if (cur.peek() == "!") {
                cur.take();
                NodePtr body = parse_alt();
                if (!cur.match(")")) {
                    raise_error("Unterminated lookbehind", cur.i);
                }
                return std::make_unique<Look>("Behind", true, std::move(body));
            }
            // Named group
            std::string name;
            while (!cur.eof() && cur.peek() != ">") {
                name += cur.take();
            }
            if (cur.eof()) {
                raise_error("Unterminated group name", cur.i);
            }
            cur.take(); // consume >

            // Validate group name
            if (name.empty() || (!std::isalpha(static_cast<unsigned char>(name[0])) && name[0] != '_')) {
                raise_error("Invalid group name '" + name + "'", start_pos);
            }
            for (size_t k = 1; k < name.size(); k++) {
                char c = name[k];
                if (!std::isalnum(static_cast<unsigned char>(c)) && c != '_') {
                    raise_error("Invalid group name '" + name + "'", start_pos);
                }
            }

            if (cap_names.count(name)) {
                raise_error("Duplicate group name '" + name + "'", start_pos);
            }
            cap_names.insert(name);
            cap_count++;

            NodePtr body = parse_alt();
            if (!cur.match(")")) {
                raise_error("Unterminated group", cur.i);
            }
            return std::make_unique<Group>(true, std::move(body), name);
        }
        if (next == ">") {
            cur.take();
            NodePtr body = parse_alt();
            if (!cur.match(")")) {
                raise_error("Unterminated atomic group", cur.i);
            }
            return std::make_unique<Group>(false, std::move(body), std::nullopt, true);
        }

        // Check for inline modifiers
        size_t save = cur.i;
        std::string scan;
        size_t j = save;
        while (j < cur.text.size() && (cur.text[j] == 'i' || cur.text[j] == 'm' ||
               cur.text[j] == 's' || cur.text[j] == 'u' || cur.text[j] == 'x')) {
            scan += cur.text[j];
            j++;
        }
        if (!scan.empty() && j < cur.text.size() && cur.text[j] == ')') {
            raise_error("Inline modifiers like (?" + scan + "...) are not supported", start_pos);
        }
        raise_error("Unknown group modifier: ?" + next, cur.i - 1);
    }

    // Capturing group
    cap_count++;
    NodePtr body = parse_alt();
    if (!cur.match(")")) {
        raise_error("Unterminated group", cur.i);
    }
    return std::make_unique<Group>(true, std::move(body));
}

NodePtr Parser::parse_class() {
    size_t start_pos = cur.i;
    cur.take(); // consume '['
    cur.in_class++;

    bool negated = false;
    if (cur.peek() == "^") {
        negated = true;
        cur.take();
    }

    // Check for empty/unterminated class: [] or [^]
    if (cur.peek() == "]") {
        cur.in_class--;
        raise_error("Unterminated character class", cur.i);
    }

    std::vector<ClassItemPtr> items;

    while (!cur.eof() && cur.peek() != "]") {
        auto item = parse_class_item();

        // Check for range
        if (cur.peek() == "-" && cur.peek(1) != "]" && !cur.eof()) {
            auto* cl = dynamic_cast<ClassLiteral*>(item.get());
            if (cl) {
                std::string from_ch = cl->ch;
                cur.take(); // consume '-'
                if (cur.eof() || cur.peek() == "]") {
                    items.push_back(std::move(item));
                    items.push_back(std::make_unique<ClassLiteral>("-"));
                    continue;
                }
                auto to_item = parse_class_item();
                auto* to_cl = dynamic_cast<ClassLiteral*>(to_item.get());
                if (to_cl) {
                    std::string to_ch = to_cl->ch;
                    if (to_ch < from_ch) {
                        cur.in_class--;
                        raise_error("Invalid character range", start_pos);
                    }
                    items.push_back(std::make_unique<ClassRange>(from_ch, to_ch));
                    continue;
                } else {
                    items.push_back(std::move(item));
                    items.push_back(std::make_unique<ClassLiteral>("-"));
                    items.push_back(std::move(to_item));
                    continue;
                }
            }
        }

        items.push_back(std::move(item));
    }

    if (cur.eof()) {
        cur.in_class--;
        raise_error("Unterminated character class", cur.i);
    }

    cur.take(); // consume ']'
    cur.in_class--;
    return std::make_unique<CharClass>(negated, std::move(items));
}

ClassItemPtr Parser::parse_class_item() {
    if (cur.peek() == "\\") {
        size_t start_pos = cur.i;
        cur.take(); // consume backslash
        if (cur.eof()) {
            raise_error("Incomplete escape sequence", start_pos);
        }
        std::string ch = cur.take();

        if (ch == "d" || ch == "D" || ch == "w" || ch == "W" ||
            ch == "s" || ch == "S") {
            return std::make_unique<ClassEscape>(ch);
        }
        if (ch == "b") return std::make_unique<ClassLiteral>(std::string(1, '\b'));
        if (ch == "0") return std::make_unique<ClassLiteral>(std::string(1, '\0'));
        if (ch == "n") return std::make_unique<ClassLiteral>("\n");
        if (ch == "r") return std::make_unique<ClassLiteral>("\r");
        if (ch == "t") return std::make_unique<ClassLiteral>("\t");
        if (ch == "f") return std::make_unique<ClassLiteral>("\f");
        if (ch == "v") return std::make_unique<ClassLiteral>("\v");
        if (ch == "x") {
            if (cur.peek() == "{") {
                cur.take();
                std::string hex;
                while (!cur.eof() && cur.peek() != "}" &&
                       std::isxdigit(static_cast<unsigned char>(cur.peek()[0]))) {
                    hex += cur.take();
                }
                if (!cur.match("}")) {
                    raise_error("Unterminated \\x{...}", start_pos);
                }
                unsigned long cp = std::stoul(hex, nullptr, 16);
                return std::make_unique<ClassLiteral>(std::string(1, static_cast<char>(cp)));
            }
            std::string hex;
            for (int i = 0; i < 2 && !cur.eof(); i++) hex += cur.take();
            if (hex.size() != 2) raise_error("Invalid \\xHH escape", start_pos);
            for (char c : hex) {
                if (!std::isxdigit(static_cast<unsigned char>(c)))
                    raise_error("Invalid \\xHH escape", start_pos);
            }
            unsigned long cp = std::stoul(hex, nullptr, 16);
            return std::make_unique<ClassLiteral>(std::string(1, static_cast<char>(cp)));
        }
        if (ch == "u") {
            if (cur.peek() == "{") {
                cur.take();
                std::string hex;
                while (!cur.eof() && cur.peek() != "}" &&
                       std::isxdigit(static_cast<unsigned char>(cur.peek()[0]))) {
                    hex += cur.take();
                }
                if (!cur.match("}")) {
                    raise_error("Unterminated \\u{...}", start_pos);
                }
                return std::make_unique<ClassLiteral>("?");
            }
            std::string hex;
            for (int i = 0; i < 4 && !cur.eof(); i++) hex += cur.take();
            if (hex.size() != 4) raise_error("Invalid \\uHHHH escape", start_pos);
            for (char c : hex) {
                if (!std::isxdigit(static_cast<unsigned char>(c)))
                    raise_error("Invalid \\uHHHH escape", start_pos);
            }
            return std::make_unique<ClassLiteral>("?");
        }
        if (ch == "p" || ch == "P") {
            if (cur.peek() != "{") {
                raise_error("Expected { after \\p/\\P", start_pos);
            }
            cur.take();
            std::string prop;
            while (!cur.eof() && cur.peek() != "}") { prop += cur.take(); }
            if (cur.eof()) { raise_error("Unterminated \\p{...}", start_pos); }
            cur.take();
            return std::make_unique<ClassEscape>(ch, prop);
        }
        if (std::isalnum(static_cast<unsigned char>(ch[0]))) {
            raise_error("Unknown escape sequence \\" + ch, start_pos);
        }
        return std::make_unique<ClassLiteral>(ch);
    }
    std::string ch = cur.take();
    return std::make_unique<ClassLiteral>(ch);
}

NodePtr Parser::parse_literal() {
    std::string ch = cur.peek();
    if (ch == "\\") { return parse_escape(); }
    if (!ch.empty() && ch[0] != '|' && ch[0] != ')') {
        cur.take();
        return std::make_unique<Lit>(ch);
    }
    return nullptr;
}

NodePtr Parser::parse_escape() {
    size_t start_pos = cur.i;
    cur.take(); // consume '\'
    if (cur.eof()) {
        raise_error("Incomplete escape sequence", start_pos);
    }
    std::string esc = cur.take();

    // Anchors
    if (esc == "b") return std::make_unique<Anchor>("WordBoundary");
    if (esc == "B") return std::make_unique<Anchor>("NotWordBoundary");
    if (esc == "A") return std::make_unique<Anchor>("AbsoluteStart");
    if (esc == "Z") return std::make_unique<Anchor>("EndBeforeFinalNewline");
    // NOTE: \z is NOT an anchor

    // Character class shortcuts
    if (esc == "d" || esc == "D" || esc == "w" || esc == "W" ||
        esc == "s" || esc == "S") {
        std::vector<ClassItemPtr> items;
        items.push_back(std::make_unique<ClassEscape>(esc));
        return std::make_unique<CharClass>(false, std::move(items));
    }

    // Control escapes
    if (CONTROL_ESCAPES.count(esc)) {
        return std::make_unique<Lit>(CONTROL_ESCAPES[esc]);
    }

    // Null byte
    if (esc == "0") {
        if (!cur.eof() && !cur.peek().empty() && std::isdigit(cur.peek()[0])) {
            raise_error("Forbidden octal escape \\0" + cur.peek(), start_pos);
        }
        return std::make_unique<Lit>(std::string(1, '\0'));
    }

    // Backreference by number
    if (std::isdigit(static_cast<unsigned char>(esc[0])) && esc[0] != '0') {
        std::string num_str = esc;
        while (!cur.eof() && !cur.peek().empty() && std::isdigit(cur.peek()[0])) {
            num_str += cur.take();
        }
        int num = std::stoi(num_str);
        if (num > cap_count) {
            raise_error("Backreference to undefined group \\" + std::to_string(num), start_pos);
        }
        return std::make_unique<Backref>(num);
    }

    // Named backreference
    if (esc == "k") {
        if (cur.peek() != "<") {
            raise_error("Expected '<' after \\k", cur.i);
        }
        cur.take(); // consume '<'
        std::string name;
        while (!cur.eof() && cur.peek() != ">") {
            name += cur.take();
        }
        if (cur.eof()) {
            raise_error("Unterminated named backref", cur.i);
        }
        cur.take(); // consume '>'
        if (cap_names.find(name) == cap_names.end()) {
            raise_error("Backreference to undefined group <" + name + ">", start_pos);
        }
        return std::make_unique<Backref>(std::nullopt, name);
    }

    // Hex escape
    if (esc == "x") {
        if (cur.peek() == "{") {
            cur.take();
            std::string hex;
            while (!cur.eof() && cur.peek() != "}" &&
                   std::isxdigit(static_cast<unsigned char>(cur.peek()[0]))) {
                hex += cur.take();
            }
            if (!cur.match("}")) {
                raise_error("Unterminated \\x{...}", start_pos);
            }
            unsigned long cp = std::stoul(hex, nullptr, 16);
            return std::make_unique<Lit>(std::string(1, static_cast<char>(cp)));
        }
        std::string hex;
        for (int i = 0; i < 2 && !cur.eof(); i++) hex += cur.take();
        if (hex.size() != 2) raise_error("Invalid \\xHH escape", start_pos);
        for (char c : hex) {
            if (!std::isxdigit(static_cast<unsigned char>(c)))
                raise_error("Invalid \\xHH escape", start_pos);
        }
        unsigned long cp = std::stoul(hex, nullptr, 16);
        return std::make_unique<Lit>(std::string(1, static_cast<char>(cp)));
    }

    // Unicode escape \u
    if (esc == "u") {
        if (cur.peek() == "{") {
            cur.take();
            std::string hex;
            while (!cur.eof() && cur.peek() != "}" &&
                   std::isxdigit(static_cast<unsigned char>(cur.peek()[0]))) {
                hex += cur.take();
            }
            if (!cur.match("}")) {
                raise_error("Unterminated \\u{...}", start_pos);
            }
            return std::make_unique<Lit>("?"); // placeholder
        }
        std::string hex;
        for (int i = 0; i < 4 && !cur.eof(); i++) hex += cur.take();
        if (hex.size() != 4) raise_error("Invalid \\uHHHH escape", start_pos);
        for (char c : hex) {
            if (!std::isxdigit(static_cast<unsigned char>(c)))
                raise_error("Invalid \\uHHHH escape", start_pos);
        }
        return std::make_unique<Lit>("?"); // placeholder
    }

    // Long Unicode escape \U
    if (esc == "U") {
        std::string hex;
        for (int i = 0; i < 8 && !cur.eof(); i++) hex += cur.take();
        if (hex.size() != 8) raise_error("Invalid \\UHHHHHHHH escape", start_pos);
        for (char c : hex) {
            if (!std::isxdigit(static_cast<unsigned char>(c)))
                raise_error("Invalid \\UHHHHHHHH escape", start_pos);
        }
        return std::make_unique<Lit>("?"); // placeholder
    }

    // Unicode property escapes
    if (esc == "p" || esc == "P") {
        if (cur.peek() != "{") {
            raise_error("Expected { after \\p/\\P", start_pos);
        }
        cur.take();
        std::string prop;
        while (!cur.eof() && cur.peek() != "}") {
            prop += cur.take();
        }
        if (cur.eof()) {
            raise_error("Unterminated \\p{...}", start_pos);
        }
        cur.take(); // consume }

        std::vector<ClassItemPtr> items;
        items.push_back(std::make_unique<ClassEscape>(esc, prop));
        return std::make_unique<CharClass>(false, std::move(items));
    }

    // Unknown alphanumeric escape
    if (std::isalnum(static_cast<unsigned char>(esc[0]))) {
        raise_error("Unknown escape sequence \\" + esc, start_pos);
    }

    // Identity escape (punctuation)
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
