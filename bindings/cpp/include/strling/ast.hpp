#ifndef STRLING_AST_HPP
#define STRLING_AST_HPP

#include <string>
#include <vector>
#include <memory>
#include <optional>
#include <nlohmann/json.hpp>

namespace strling {
namespace ast {

using json = nlohmann::json;

struct Node {
    virtual ~Node() = default;
    virtual std::string get_type() const = 0;
};

using NodePtr = std::unique_ptr<Node>;

struct Literal : Node {
    std::string value;
    std::string get_type() const override { return "Literal"; }
};

struct Sequence : Node {
    std::vector<NodePtr> items;
    std::string get_type() const override { return "Sequence"; }
};

struct Alternation : Node {
    std::vector<NodePtr> items;
    std::string get_type() const override { return "Alternation"; }
};

struct Range : Node {
    std::string from;
    std::string to;
    std::string get_type() const override { return "Range"; }
};

struct Escape : Node {
    std::string kind;
    std::string get_type() const override { return "Escape"; }
};

struct CharacterClass : Node {
    bool negated = false;
    std::vector<NodePtr> members;
    std::string get_type() const override { return "CharacterClass"; }
};

struct Anchor : Node {
    std::string kind; // "StartOfString", "EndOfString", "WordBoundary", "NonWordBoundary"
    std::string get_type() const override { return "Anchor"; }
};

struct Dot : Node {
    std::string get_type() const override { return "Dot"; }
};

struct Group : Node {
    NodePtr child;
    bool capturing = true;
    bool atomic = false;
    std::optional<std::string> name;
    std::string get_type() const override { return "Group"; }
};

struct Quantifier : Node {
    NodePtr child;
    int min = 0;
    int max = -1; // -1 for infinity
    bool greedy = true;
    bool possessive = false;
    std::string get_type() const override { return "Quantifier"; }
};

struct Backreference : Node {
    std::optional<std::string> name;
    std::optional<int> index;
    std::string get_type() const override { return "Backreference"; }
};

struct Lookahead : Node {
    NodePtr child;
    bool positive = true;
    std::string get_type() const override { return "Lookahead"; }
};

struct Lookbehind : Node {
    NodePtr child;
    bool positive = true;
    std::string get_type() const override { return "Lookbehind"; }
};

struct UnicodeProperty : Node {
    std::string value;
    bool negated = false;
    std::string get_type() const override { return "UnicodeProperty"; }
};

// Function to hydrate AST from JSON
NodePtr from_json(const json& j);

} // namespace ast
} // namespace strling

#endif // STRLING_AST_HPP
