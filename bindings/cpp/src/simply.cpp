#include "strling/simply.hpp"
#include <sstream>
#include <algorithm>
#include <utility>

namespace strling::simply {

struct Impl {
    enum class Kind { Empty, Literal, Digit, AnyOf, Seq, Anchor, Quantifier, Group } kind = Kind::Empty;

    // payloads
    std::string lit;               // for literal and anchor name
    int count = 0;                 // for digit count / quantifier min
    std::vector<std::shared_ptr<Impl>> parts; // for sequence
    bool capturing = false;        // for group

    Impl() = default;
};

// Helpers to construct nodes
static std::shared_ptr<Impl> make_literal(std::string_view s) {
    auto p = std::make_shared<Impl>();
    p->kind = Impl::Kind::Literal;
    p->lit = std::string(s);
    return p;
}

static std::shared_ptr<Impl> make_digit(int n) {
    auto p = std::make_shared<Impl>();
    p->kind = Impl::Kind::Digit;
    p->count = n;
    return p;
}

static std::shared_ptr<Impl> make_anyof(std::string_view s) {
    auto p = std::make_shared<Impl>();
    p->kind = Impl::Kind::AnyOf;
    p->lit = std::string(s);
    return p;
}

static std::shared_ptr<Impl> make_seq(const std::vector<Pattern>& parts) {
    auto p = std::make_shared<Impl>();
    p->kind = Impl::Kind::Seq;
    for (const auto &part : parts) p->parts.push_back(part.impl_ptr());
    return p;
}

static std::shared_ptr<Impl> make_anchor(std::string_view name) {
    auto p = std::make_shared<Impl>();
    p->kind = Impl::Kind::Anchor;
    p->lit = std::string(name);
    return p;
}

static std::shared_ptr<Impl> make_quant(std::shared_ptr<Impl> child, int min, int max = -1) {
    auto p = std::make_shared<Impl>();
    p->kind = Impl::Kind::Quantifier;
    p->parts.push_back(child);
    p->count = min;
    return p;
}

static std::shared_ptr<Impl> make_group(std::shared_ptr<Impl> child, bool capturing) {
    auto p = std::make_shared<Impl>();
    p->kind = Impl::Kind::Group;
    p->capturing = capturing;
    p->parts.push_back(child);
    return p;
}

// ----------------- Pattern implementation -----------------

Pattern::Pattern() : impl(std::make_shared<Impl>()) {}
Pattern::Pattern(std::shared_ptr<Impl> i) : impl(std::move(i)) {}

Pattern digit(int n) { return Pattern(make_digit(n)); }
Pattern literal(std::string_view s) { return Pattern(make_literal(s)); }
Pattern any_of(std::string_view s) { return Pattern(make_anyof(s)); }
Pattern start() { return Pattern(make_anchor("Start")); }
Pattern end()   { return Pattern(make_anchor("End")); }
Pattern merge(const std::vector<Pattern>& parts) { return Pattern(make_seq(parts)); }
Pattern merge(std::initializer_list<Pattern> parts) { return merge(std::vector<Pattern>(parts)); }

// returns a NEW Pattern (immutability)
Pattern Pattern::may() const {
    // wrap current impl in a quantifier (min=0, max=1)
    return Pattern(make_quant(this->impl, 0, 1));
}

Pattern Pattern::as_capture() const {
    // wrap current impl in a capturing group
    return Pattern(make_group(this->impl, true));
}

// Internal emitter helpers: escape a literal for usage outside of char classes
static std::string escape_literal(const std::string &s) {
    std::string out;
    for (char c : s) {
        switch (c) {
            case '\\': out += "\\\\"; break;
            case '^': case '$': case '.': case '|': case '?': case '*': case '+': case '(': case ')': case '[': case ']': case '{': case '}': case '/':
                out += '\\'; out.push_back(c); break;
            default: out.push_back(c);
        }
    }
    return out;
}

// Build a regex string for a given Impl
static std::string build_regex(const std::shared_ptr<Impl>& node) {
    if (!node) return "";
    using Kind = Impl::Kind;

    switch (node->kind) {
        case Kind::Empty: return "";
        case Kind::Literal: return escape_literal(node->lit);
        case Kind::Digit: {
            // \\d{n}
            std::ostringstream ss; ss << "\\d{" << node->count << "}"; return ss.str();
        }
        case Kind::AnyOf: {
            // build char class: keep characters as-is but escape ']' and '^' and '\\' appropriately
            std::string chars = node->lit;
            std::string cls;
            // If hyphen is present, put it first to avoid range semantics when possible
            // Keep the sequence stable so tests match TS output which uses [-. ] ordering when given "-. "
            cls.push_back('[');
            for (char c : chars) {
                // add literal or escape if necessary inside char class
                if (c == '\\' || c == ']' || c == '^') { cls.push_back('\\'); cls.push_back(c); }
                else cls.push_back(c);
            }
            cls.push_back(']');
            return cls;
        }
        case Kind::Seq: {
            std::string out;
            for (auto &p : node->parts) out += build_regex(p);
            return out;
        }
        case Kind::Anchor: {
            if (node->lit == "Start") return "^";
            if (node->lit == "End") return "$";
            // fallback literal
            return escape_literal(node->lit);
        }
        case Kind::Quantifier: {
            // present only as optional in this small emitter
            auto child = node->parts.empty() ? nullptr : node->parts[0];
            if (!child) return "";
            std::string c = build_regex(child);
            // If the child is a single character or a character class or group, append ? appropriately
            // Heuristic: if child looks like multi-character literal without grouping, wrap in group
            bool need_wrap = false;
            if (child->kind == Kind::Seq && child->parts.size() > 1) need_wrap = true;
            if (need_wrap) c = "(?:" + c + ")";
            return c + "?";
        }
        case Kind::Group: {
            auto child = node->parts.empty() ? nullptr : node->parts[0];
            std::string body = child ? build_regex(child) : std::string();
            if (node->capturing) {
                return "(" + body + ")";
            } else {
                return "(?:" + body + ")";
            }
        }
        default:
            return std::string();
    }
}

std::string Pattern::compile() const {
    // For now simply emit a builder-based regex string based on the Pattern tree
    return build_regex(this->impl);
}

std::string Pattern::debug_str() const {
    std::ostringstream ss;
    ss << "Pattern(kind=" << static_cast<int>(impl->kind) << ", lit='" << impl->lit << "')";
    return ss.str();
}

} // namespace strling::simply
