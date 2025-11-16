/**
 * @file ir.hpp
 * @brief STRling Intermediate Representation (IR) Node Definitions
 * 
 * This module defines the complete set of IR node classes that represent
 * language-agnostic regex constructs. The IR serves as an intermediate layer
 * between the parsed AST and the target-specific emitters (e.g., PCRE2).
 * 
 * IR nodes are designed to be:
 *   - Simple and composable
 *   - Easy to serialize (via toDict methods)
 *   - Independent of any specific regex flavor
 *   - Optimized for transformation and analysis
 * 
 * Each IR node corresponds to a fundamental regex operation (alternation,
 * sequencing, character classes, quantification, etc.) and can be serialized
 * to a dictionary representation for further processing or debugging.
 * 
 * @copyright Copyright (c) 2024 TheCyberLocal
 * @license MIT License
 */

#ifndef STRLING_CORE_IR_HPP
#define STRLING_CORE_IR_HPP

#include <string>
#include <vector>
#include <memory>
#include <optional>
#include <variant>
#include <map>

namespace strling {
namespace core {

// Forward declarations
class IROp;
class IRClassItem;

// Type aliases for convenience
using IROpPtr = std::unique_ptr<IROp>;
using IRClassItemPtr = std::unique_ptr<IRClassItem>;

/**
 * @brief Base class for all IR operations.
 * 
 * All IR nodes extend this base class and must implement the toDict() method
 * for serialization to a dictionary representation.
 */
class IROp {
public:
    virtual ~IROp() = default;
    
    /**
     * @brief Serialize the IR node to a dictionary representation.
     * 
     * @return The dictionary representation of this IR node.
     */
    virtual std::map<std::string, std::string> toDict() const = 0;
};

/**
 * @brief Represents an alternation (OR) operation in the IR.
 * 
 * Matches any one of the provided branches. Equivalent to the | operator
 * in traditional regex syntax.
 */
class IRAlt : public IROp {
public:
    std::vector<IROpPtr> branches;  ///< The alternative branches
    
    explicit IRAlt(std::vector<IROpPtr> branches)
        : branches(std::move(branches)) {}
    
    std::map<std::string, std::string> toDict() const override;
};

/**
 * @brief Represents a sequence (concatenation) operation in the IR.
 * 
 * Matches the parts in order, one after another.
 */
class IRSeq : public IROp {
public:
    std::vector<IROpPtr> parts;  ///< The sequential parts
    
    explicit IRSeq(std::vector<IROpPtr> parts)
        : parts(std::move(parts)) {}
    
    std::map<std::string, std::string> toDict() const override;
};

/**
 * @brief Represents a literal string in the IR.
 * 
 * Matches the exact string value.
 */
class IRLit : public IROp {
public:
    std::string value;  ///< The literal string value
    
    explicit IRLit(const std::string& value)
        : value(value) {}
    
    std::map<std::string, std::string> toDict() const override;
};

/**
 * @brief Represents the dot (wildcard) metacharacter in the IR.
 * 
 * Matches any character (behavior depends on flags like dotAll).
 */
class IRDot : public IROp {
public:
    IRDot() = default;
    
    std::map<std::string, std::string> toDict() const override;
};

/**
 * @brief Represents an anchor in the IR.
 * 
 * Anchors match positions rather than characters (start, end, boundaries).
 */
class IRAnchor : public IROp {
public:
    std::string at;  ///< Anchor type (e.g., "Start", "End", "WordBoundary")
    
    explicit IRAnchor(const std::string& at)
        : at(at) {}
    
    std::map<std::string, std::string> toDict() const override;
};

/**
 * @brief Base class for character class items in the IR.
 */
class IRClassItem {
public:
    virtual ~IRClassItem() = default;
    
    /**
     * @brief Serialize the class item to a dictionary representation
     * 
     * @return std::map representing the class item
     */
    virtual std::map<std::string, std::string> toDict() const = 0;
};

/**
 * @brief Represents a character range in the IR.
 * 
 * Matches characters in the range from from_ch to to_ch.
 */
class IRClassRange : public IRClassItem {
public:
    std::string from_ch;  ///< Start character of the range
    std::string to_ch;    ///< End character of the range
    
    IRClassRange(const std::string& from_ch, const std::string& to_ch)
        : from_ch(from_ch), to_ch(to_ch) {}
    
    std::map<std::string, std::string> toDict() const override;
};

/**
 * @brief Represents a literal character in a character class in the IR.
 * 
 * Matches a single specific character.
 */
class IRClassLiteral : public IRClassItem {
public:
    std::string ch;  ///< The literal character
    
    explicit IRClassLiteral(const std::string& ch)
        : ch(ch) {}
    
    std::map<std::string, std::string> toDict() const override;
};

/**
 * @brief Represents an escape sequence in a character class in the IR.
 * 
 * Represents escape sequences like \d, \w, \s, \p{...}, etc.
 */
class IRClassEscape : public IRClassItem {
public:
    std::string type;                    ///< Escape type: d, D, w, W, s, S, p, P
    std::optional<std::string> property; ///< Unicode property for \p and \P
    
    explicit IRClassEscape(const std::string& type, const std::optional<std::string>& property = std::nullopt)
        : type(type), property(property) {}
    
    std::map<std::string, std::string> toDict() const override;
};

/**
 * @brief Represents a character class in the IR.
 * 
 * Matches one character from the set of items, or not from the set if negated.
 */
class IRCharClass : public IROp {
public:
    bool negated;                        ///< Whether the class is negated
    std::vector<IRClassItemPtr> items;   ///< The items in the character class
    
    IRCharClass(bool negated, std::vector<IRClassItemPtr> items)
        : negated(negated), items(std::move(items)) {}
    
    std::map<std::string, std::string> toDict() const override;
};

/**
 * @brief Represents a quantifier in the IR.
 * 
 * Repeats the child pattern according to min/max bounds and mode.
 */
class IRQuant : public IROp {
public:
    IROpPtr child;                       ///< The child operation being quantified
    int min;                             ///< Minimum repetitions
    std::variant<int, std::string> max;  ///< Maximum repetitions (int or "Inf")
    std::string mode;                    ///< Quantifier mode: "Greedy"|"Lazy"|"Possessive"
    
    IRQuant(IROpPtr child, int min, const std::variant<int, std::string>& max, const std::string& mode)
        : child(std::move(child)), min(min), max(max), mode(mode) {}
    
    std::map<std::string, std::string> toDict() const override;
};

/**
 * @brief Represents a group in the IR.
 * 
 * Groups expressions together, optionally capturing for backreferences.
 */
class IRGroup : public IROp {
public:
    bool capturing;                ///< Whether the group captures
    IROpPtr body;                  ///< The grouped content
    std::optional<std::string> name;    ///< Named capture group name
    std::optional<bool> atomic;    ///< Atomic group flag
    
    IRGroup(bool capturing, IROpPtr body, const std::optional<std::string>& name = std::nullopt,
            const std::optional<bool>& atomic = std::nullopt)
        : capturing(capturing), body(std::move(body)), name(name), atomic(atomic) {}
    
    std::map<std::string, std::string> toDict() const override;
};

/**
 * @brief Represents a backreference in the IR.
 * 
 * Matches the same text as a previously captured group.
 */
class IRBackref : public IROp {
public:
    std::optional<int> byIndex;         ///< Reference by index (1-based)
    std::optional<std::string> byName;  ///< Reference by name
    
    IRBackref(const std::optional<int>& byIndex = std::nullopt,
              const std::optional<std::string>& byName = std::nullopt)
        : byIndex(byIndex), byName(byName) {}
    
    std::map<std::string, std::string> toDict() const override;
};

/**
 * @brief Represents a lookaround assertion in the IR.
 * 
 * Asserts that a pattern matches (or doesn't match) ahead or behind without consuming.
 */
class IRLook : public IROp {
public:
    std::string dir;  ///< Direction: "Ahead" | "Behind"
    bool neg;         ///< Whether the lookaround is negative
    IROpPtr body;     ///< The lookaround content
    
    IRLook(const std::string& dir, bool neg, IROpPtr body)
        : dir(dir), neg(neg), body(std::move(body)) {}
    
    std::map<std::string, std::string> toDict() const override;
};

} // namespace core
} // namespace strling

#endif // STRLING_CORE_IR_HPP
