#ifndef STRLING_IR_HPP
#define STRLING_IR_HPP

#include <string>
#include <vector>
#include <memory>
#include <optional>
#include <variant>
#include <nlohmann/json.hpp>

namespace strling {
namespace ir {

using json = nlohmann::json;

struct IRNode {
    virtual ~IRNode() = default;
    virtual json to_json() const = 0;
};

using IRNodePtr = std::unique_ptr<IRNode>;

struct Lit : IRNode {
    std::string value;
    json to_json() const override {
        return {{"ir", "Lit"}, {"value", value}};
    }
};

struct Char : IRNode {
    std::string value;
    json to_json() const override {
        return {{"ir", "Char"}, {"char", value}};
    }
};

struct Seq : IRNode {
    std::vector<IRNodePtr> parts;
    json to_json() const override {
        json j = {{"ir", "Seq"}, {"parts", json::array()}};
        for (const auto& item : parts) {
            j["parts"].push_back(item->to_json());
        }
        return j;
    }
};

struct Alt : IRNode {
    std::vector<IRNodePtr> branches;
    json to_json() const override {
        json j = {{"ir", "Alt"}, {"branches", json::array()}};
        for (const auto& item : branches) {
            j["branches"].push_back(item->to_json());
        }
        return j;
    }
};

struct Range : IRNode {
    std::string from;
    std::string to;
    json to_json() const override {
        return {{"ir", "Range"}, {"from", from}, {"to", to}};
    }
};

struct CharClass : IRNode {
    bool negated = false;
    std::vector<IRNodePtr> items;
    json to_json() const override {
        json j = {{"ir", "CharClass"}, {"negated", negated}, {"items", json::array()}};
        for (const auto& item : items) {
            j["items"].push_back(item->to_json());
        }
        return j;
    }
};

struct Anchor : IRNode {
    std::string at;
    json to_json() const override {
        return {{"ir", "Anchor"}, {"at", at}};
    }
};

struct Dot : IRNode {
    json to_json() const override {
        return {{"ir", "Dot"}};
    }
};

struct Group : IRNode {
    IRNodePtr body;
    bool capturing = true;
    std::optional<std::string> name;
    bool atomic = false;
    json to_json() const override {
        json j = {{"ir", "Group"}, {"body", body->to_json()}, {"capturing", capturing}};
        if (name) j["name"] = *name;
        if (atomic) j["atomic"] = atomic;
        return j;
    }
};

struct Quant : IRNode {
    IRNodePtr child;
    int min = 0;
    int max = -1; // -1 for infinity
    std::string mode = "greedy";
    json to_json() const override {
        json j = {{"ir", "Quant"}, {"child", child->to_json()}, {"min", min}, {"mode", mode}};
        if (max == -1) j["max"] = "Inf";
        else j["max"] = max;
        return j;
    }
};

struct Backref : IRNode {
    std::optional<int> byIndex;
    std::optional<std::string> byName;
    json to_json() const override {
        json j = {{"ir", "Backref"}};
        if (byIndex) j["byIndex"] = *byIndex;
        if (byName) j["byName"] = *byName;
        return j;
    }
};

struct Esc : IRNode {
    std::string type;
    std::optional<std::string> property;
    json to_json() const override {
        json j = {{"ir", "Esc"}, {"type", type}};
        if (property) j["property"] = *property;
        return j;
    }
};

struct Look : IRNode {
    IRNodePtr body;
    std::string dir; // "ahead" or "behind"
    bool neg = false;
    json to_json() const override {
        return {{"ir", "Look"}, {"body", body->to_json()}, {"dir", dir}, {"neg", neg}};
    }
};

} // namespace ir
} // namespace strling

#endif // STRLING_IR_HPP
