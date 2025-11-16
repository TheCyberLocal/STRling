/**
 * @file nodes.cpp
 * @brief Implementation of STRling AST nodes
 * 
 * @copyright Copyright (c) 2024 TheCyberLocal
 * @license MIT License
 */

#include "strling/core/nodes.hpp"
#include <sstream>

namespace strling {
namespace core {

// ---- Flags Implementation ----

std::map<std::string, bool> Flags::toDict() const {
    return {
        {"ignoreCase", ignoreCase},
        {"multiline", multiline},
        {"dotAll", dotAll},
        {"unicode", unicode},
        {"extended", extended}
    };
}

Flags Flags::fromLetters(const std::string& letters) {
    Flags f;
    for (char ch : letters) {
        if (ch == ',' || ch == ' ') {
            continue;
        }
        
        switch (ch) {
            case 'i':
                f.ignoreCase = true;
                break;
            case 'm':
                f.multiline = true;
                break;
            case 's':
                f.dotAll = true;
                break;
            case 'u':
                f.unicode = true;
                break;
            case 'x':
                f.extended = true;
                break;
            case '\0':
                break;
            default:
                // Unknown flags are ignored at parser stage; may be warned later
                break;
        }
    }
    return f;
}

// ---- Node Implementations ----

// Note: For simplicity, toDict() returns a simplified string-to-string map.
// A full implementation would use a JSON library or more complex data structure
// to properly represent nested structures.

std::map<std::string, std::string> Alt::toDict() const {
    std::map<std::string, std::string> result;
    result["kind"] = "Alt";
    // In a real implementation, we would serialize branches as a JSON array
    // For now, we just indicate the number of branches
    result["branches_count"] = std::to_string(branches.size());
    return result;
}

std::map<std::string, std::string> Seq::toDict() const {
    std::map<std::string, std::string> result;
    result["kind"] = "Seq";
    result["parts_count"] = std::to_string(parts.size());
    return result;
}

std::map<std::string, std::string> Lit::toDict() const {
    std::map<std::string, std::string> result;
    result["kind"] = "Lit";
    result["value"] = value;
    return result;
}

std::map<std::string, std::string> Dot::toDict() const {
    std::map<std::string, std::string> result;
    result["kind"] = "Dot";
    return result;
}

std::map<std::string, std::string> Anchor::toDict() const {
    std::map<std::string, std::string> result;
    result["kind"] = "Anchor";
    result["at"] = at;
    return result;
}

// ---- ClassItem Implementations ----

std::map<std::string, std::string> ClassRange::toDict() const {
    std::map<std::string, std::string> result;
    result["kind"] = "Range";
    result["from"] = from_ch;
    result["to"] = to_ch;
    return result;
}

std::map<std::string, std::string> ClassLiteral::toDict() const {
    std::map<std::string, std::string> result;
    result["kind"] = "Char";
    result["char"] = ch;
    return result;
}

std::map<std::string, std::string> ClassEscape::toDict() const {
    std::map<std::string, std::string> result;
    result["kind"] = "Esc";
    result["type"] = type;
    if (type == "p" || type == "P") {
        if (property.has_value()) {
            result["property"] = property.value();
        }
    }
    return result;
}

std::map<std::string, std::string> CharClass::toDict() const {
    std::map<std::string, std::string> result;
    result["kind"] = "CharClass";
    result["negated"] = negated ? "true" : "false";
    result["items_count"] = std::to_string(items.size());
    return result;
}

// ---- Complex Node Implementations ----

std::map<std::string, std::string> Quant::toDict() const {
    std::map<std::string, std::string> result;
    result["kind"] = "Quant";
    result["min"] = std::to_string(min);
    
    if (std::holds_alternative<int>(max)) {
        result["max"] = std::to_string(std::get<int>(max));
    } else {
        result["max"] = std::get<std::string>(max);
    }
    
    result["mode"] = mode;
    return result;
}

std::map<std::string, std::string> Group::toDict() const {
    std::map<std::string, std::string> result;
    result["kind"] = "Group";
    result["capturing"] = capturing ? "true" : "false";
    
    if (name.has_value()) {
        result["name"] = name.value();
    }
    
    if (atomic.has_value()) {
        result["atomic"] = atomic.value() ? "true" : "false";
    }
    
    return result;
}

std::map<std::string, std::string> Backref::toDict() const {
    std::map<std::string, std::string> result;
    result["kind"] = "Backref";
    
    if (byIndex.has_value()) {
        result["byIndex"] = std::to_string(byIndex.value());
    }
    
    if (byName.has_value()) {
        result["byName"] = byName.value();
    }
    
    return result;
}

std::map<std::string, std::string> Look::toDict() const {
    std::map<std::string, std::string> result;
    result["kind"] = "Look";
    result["dir"] = dir;
    result["neg"] = neg ? "true" : "false";
    return result;
}

} // namespace core
} // namespace strling
