/**
 * @file ir.cpp
 * @brief Implementation of STRling IR nodes
 * 
 * @copyright Copyright (c) 2024 TheCyberLocal
 * @license MIT License
 */

#include "strling/core/ir.hpp"
#include <sstream>

namespace strling {
namespace core {

// ---- IROp Implementations ----

std::map<std::string, std::string> IRAlt::toDict() const {
    std::map<std::string, std::string> result;
    result["ir"] = "Alt";
    result["branches_count"] = std::to_string(branches.size());
    return result;
}

std::map<std::string, std::string> IRSeq::toDict() const {
    std::map<std::string, std::string> result;
    result["ir"] = "Seq";
    result["parts_count"] = std::to_string(parts.size());
    return result;
}

std::map<std::string, std::string> IRLit::toDict() const {
    std::map<std::string, std::string> result;
    result["ir"] = "Lit";
    result["value"] = value;
    return result;
}

std::map<std::string, std::string> IRDot::toDict() const {
    std::map<std::string, std::string> result;
    result["ir"] = "Dot";
    return result;
}

std::map<std::string, std::string> IRAnchor::toDict() const {
    std::map<std::string, std::string> result;
    result["ir"] = "Anchor";
    result["at"] = at;
    return result;
}

// ---- IRClassItem Implementations ----

std::map<std::string, std::string> IRClassRange::toDict() const {
    std::map<std::string, std::string> result;
    result["ir"] = "Range";
    result["from"] = from_ch;
    result["to"] = to_ch;
    return result;
}

std::map<std::string, std::string> IRClassLiteral::toDict() const {
    std::map<std::string, std::string> result;
    result["ir"] = "Char";
    result["char"] = ch;
    return result;
}

std::map<std::string, std::string> IRClassEscape::toDict() const {
    std::map<std::string, std::string> result;
    result["ir"] = "Esc";
    result["type"] = type;
    if (property.has_value()) {
        result["property"] = property.value();
    }
    return result;
}

std::map<std::string, std::string> IRCharClass::toDict() const {
    std::map<std::string, std::string> result;
    result["ir"] = "CharClass";
    result["negated"] = negated ? "true" : "false";
    result["items_count"] = std::to_string(items.size());
    return result;
}

// ---- Complex IROp Implementations ----

std::map<std::string, std::string> IRQuant::toDict() const {
    std::map<std::string, std::string> result;
    result["ir"] = "Quant";
    result["min"] = std::to_string(min);
    
    if (std::holds_alternative<int>(max)) {
        result["max"] = std::to_string(std::get<int>(max));
    } else {
        result["max"] = std::get<std::string>(max);
    }
    
    result["mode"] = mode;
    return result;
}

std::map<std::string, std::string> IRGroup::toDict() const {
    std::map<std::string, std::string> result;
    result["ir"] = "Group";
    result["capturing"] = capturing ? "true" : "false";
    
    if (name.has_value()) {
        result["name"] = name.value();
    }
    
    if (atomic.has_value()) {
        result["atomic"] = atomic.value() ? "true" : "false";
    }
    
    return result;
}

std::map<std::string, std::string> IRBackref::toDict() const {
    std::map<std::string, std::string> result;
    result["ir"] = "Backref";
    
    if (byIndex.has_value()) {
        result["byIndex"] = std::to_string(byIndex.value());
    }
    
    if (byName.has_value()) {
        result["byName"] = byName.value();
    }
    
    return result;
}

std::map<std::string, std::string> IRLook::toDict() const {
    std::map<std::string, std::string> result;
    result["ir"] = "Look";
    result["dir"] = dir;
    result["neg"] = neg ? "true" : "false";
    return result;
}

} // namespace core
} // namespace strling
