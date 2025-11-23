#include "strling/ast.hpp"
#include <stdexcept>
#include <iostream>

namespace strling {
namespace ast {

NodePtr from_json(const json& j) {
    std::string type = j.at("type").get<std::string>();

    if (type == "Literal") {
        auto node = std::make_unique<Literal>();
        node->value = j.at("value").get<std::string>();
        return node;
    } else if (type == "Sequence") {
        auto node = std::make_unique<Sequence>();
        if (j.contains("parts")) {
            for (const auto& item : j.at("parts")) {
                node->items.push_back(from_json(item));
            }
        }
        return node;
    } else if (type == "Alternation") {
        auto node = std::make_unique<Alternation>();
        if (j.contains("alternatives")) {
            for (const auto& item : j.at("alternatives")) {
                node->items.push_back(from_json(item));
            }
        }
        return node;
    } else if (type == "CharacterClass") {
        auto node = std::make_unique<CharacterClass>();
        if (j.contains("negated")) node->negated = j.at("negated").get<bool>();
        if (j.contains("members")) {
            for (const auto& item : j.at("members")) {
                node->members.push_back(from_json(item));
            }
        }
        return node;
    } else if (type == "Range") {
        auto node = std::make_unique<Range>();
        node->from = j.at("from").get<std::string>();
        node->to = j.at("to").get<std::string>();
        return node;
    } else if (type == "Escape") {
        auto node = std::make_unique<Escape>();
        node->kind = j.at("kind").get<std::string>();
        return node;
    } else if (type == "Anchor") {
        auto node = std::make_unique<Anchor>();
        node->kind = j.at("at").get<std::string>();
        return node;
    } else if (type == "Dot") {
        return std::make_unique<Dot>();
    } else if (type == "Group") {
        auto node = std::make_unique<Group>();
        if (j.contains("expression")) {
            node->child = from_json(j.at("expression"));
        } else if (j.contains("body")) {
             node->child = from_json(j.at("body"));
        }
        if (j.contains("capturing")) node->capturing = j.at("capturing").get<bool>();
        if (j.contains("atomic")) node->atomic = j.at("atomic").get<bool>();
        if (j.contains("name") && !j.at("name").is_null()) node->name = j.at("name").get<std::string>();
        return node;
    } else if (type == "Quantifier") {
        auto node = std::make_unique<Quantifier>();
        node->child = from_json(j.at("target"));
        node->min = j.at("min").get<int>();
        if (j.at("max").is_null()) {
            node->max = -1;
        } else {
            node->max = j.at("max").get<int>();
        }
        if (j.contains("greedy")) node->greedy = j.at("greedy").get<bool>();
        if (j.contains("possessive")) node->possessive = j.at("possessive").get<bool>();
        return node;
    } else if (type == "Backreference") {
        auto node = std::make_unique<Backreference>();
        if (j.contains("name") && !j.at("name").is_null()) node->name = j.at("name").get<std::string>();
        if (j.contains("index") && !j.at("index").is_null()) node->index = j.at("index").get<int>();
        return node;
    } else if (type == "Lookahead") {
        auto node = std::make_unique<Lookahead>();
        node->child = from_json(j.at("body"));
        node->positive = true;
        return node;
    } else if (type == "NegativeLookahead") {
        auto node = std::make_unique<Lookahead>();
        node->child = from_json(j.at("body"));
        node->positive = false;
        return node;
    } else if (type == "Lookbehind") {
        auto node = std::make_unique<Lookbehind>();
        node->child = from_json(j.at("body"));
        node->positive = true;
        return node;
    } else if (type == "NegativeLookbehind") {
        auto node = std::make_unique<Lookbehind>();
        node->child = from_json(j.at("body"));
        node->positive = false;
        return node;
    } else if (type == "UnicodeProperty") {
        auto node = std::make_unique<UnicodeProperty>();
        if (j.contains("value")) node->value = j.at("value").get<std::string>();
        if (j.contains("negated")) node->negated = j.at("negated").get<bool>();
        return node;
    }

    // Fallback or error
    // For now, return nullptr or throw
    throw std::runtime_error("Unknown AST node type: " + type);
}

} // namespace ast
} // namespace strling
