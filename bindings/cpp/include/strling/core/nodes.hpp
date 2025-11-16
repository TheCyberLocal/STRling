/**
 * @file nodes.hpp
 * @brief STRling AST Node Definitions
 * 
 * This module defines the complete set of Abstract Syntax Tree (AST) node classes
 * that represent the parsed structure of STRling patterns. The AST is the direct
 * output of the parser and represents the syntactic structure of the pattern before
 * optimization and lowering to IR.
 * 
 * AST nodes are designed to:
 *   - Closely mirror the source pattern syntax
 *   - Be easily serializable to the Base TargetArtifact schema
 *   - Provide a clean separation between parsing and compilation
 *   - Support multiple target regex flavors through the compilation pipeline
 * 
 * Each AST node type corresponds to a syntactic construct in the STRling DSL
 * (alternation, sequencing, character classes, anchors, etc.) and can be
 * serialized to a dictionary representation for debugging or storage.
 * 
 * @copyright Copyright (c) 2024 TheCyberLocal
 * @license MIT License
 */

#ifndef STRLING_CORE_NODES_HPP
#define STRLING_CORE_NODES_HPP

#include <string>
#include <vector>
#include <memory>
#include <optional>
#include <variant>
#include <map>

namespace strling {
namespace core {

// Forward declarations
class Node;
class ClassItem;

// Type aliases for convenience
using NodePtr = std::unique_ptr<Node>;
using ClassItemPtr = std::unique_ptr<ClassItem>;

/**
 * @brief Container for regex flags/modifiers.
 * 
 * Flags control the behavior of pattern matching (case sensitivity, multiline
 * mode, etc.). This class encapsulates all standard regex flags.
 */
struct Flags {
    bool ignoreCase = false;  ///< Case-insensitive matching
    bool multiline = false;   ///< Multiline mode (^ and $ match line boundaries)
    bool dotAll = false;      ///< Dot matches all characters including newlines
    bool unicode = false;     ///< Unicode mode
    bool extended = false;    ///< Extended mode (ignore whitespace)
    
    /**
     * @brief Convert flags to dictionary representation
     * 
     * @return std::map<std::string, bool> Dictionary of flag names to values
     */
    std::map<std::string, bool> toDict() const;
    
    /**
     * @brief Create Flags object from string of flag letters
     * 
     * @param letters String containing flag letters (e.g., "im" for ignoreCase and multiline)
     * @return Flags object with appropriate flags set
     */
    static Flags fromLetters(const std::string& letters);
};

/**
 * @brief Base class for all AST nodes
 * 
 * All AST nodes inherit from this base class and must implement the toDict()
 * method for serialization.
 */
class Node {
public:
    virtual ~Node() = default;
    
    /**
     * @brief Serialize the node to a dictionary representation
     * 
     * @return std::map representing the node structure
     */
    virtual std::map<std::string, std::string> toDict() const = 0;
};

/**
 * @brief Alternation node (OR operation)
 * 
 * Represents a choice between multiple branches. In regex: (a|b|c)
 */
class Alt : public Node {
public:
    std::vector<NodePtr> branches;  ///< The alternative branches
    
    explicit Alt(std::vector<NodePtr> branches)
        : branches(std::move(branches)) {}
    
    std::map<std::string, std::string> toDict() const override;
};

/**
 * @brief Sequence node (concatenation)
 * 
 * Represents sequential matching of multiple parts. In regex: abc
 */
class Seq : public Node {
public:
    std::vector<NodePtr> parts;  ///< The sequential parts
    
    explicit Seq(std::vector<NodePtr> parts)
        : parts(std::move(parts)) {}
    
    std::map<std::string, std::string> toDict() const override;
};

/**
 * @brief Literal string node
 * 
 * Represents a literal string to match exactly.
 */
class Lit : public Node {
public:
    std::string value;  ///< The literal string value
    
    explicit Lit(const std::string& value)
        : value(value) {}
    
    std::map<std::string, std::string> toDict() const override;
};

/**
 * @brief Dot (wildcard) node
 * 
 * Represents the . metacharacter that matches any character (except newline by default).
 */
class Dot : public Node {
public:
    Dot() = default;
    
    std::map<std::string, std::string> toDict() const override;
};

/**
 * @brief Anchor node
 * 
 * Represents position anchors like start (^), end ($), word boundary (\b), etc.
 */
class Anchor : public Node {
public:
    std::string at;  ///< Anchor type: "Start"|"End"|"WordBoundary"|"NotWordBoundary"|Absolute* variants
    
    explicit Anchor(const std::string& at)
        : at(at) {}
    
    std::map<std::string, std::string> toDict() const override;
};

/**
 * @brief Base class for character class items
 * 
 * Character classes contain items that can be ranges, literals, or escape sequences.
 */
class ClassItem {
public:
    virtual ~ClassItem() = default;
    
    /**
     * @brief Serialize the class item to a dictionary representation
     * 
     * @return std::map representing the class item
     */
    virtual std::map<std::string, std::string> toDict() const = 0;
};

/**
 * @brief Character range in a character class
 * 
 * Represents a range like [a-z] or [0-9].
 */
class ClassRange : public ClassItem {
public:
    std::string from_ch;  ///< Start character of the range
    std::string to_ch;    ///< End character of the range
    
    ClassRange(const std::string& from_ch, const std::string& to_ch)
        : from_ch(from_ch), to_ch(to_ch) {}
    
    std::map<std::string, std::string> toDict() const override;
};

/**
 * @brief Literal character in a character class
 * 
 * Represents a single character like [a] or [*].
 */
class ClassLiteral : public ClassItem {
public:
    std::string ch;  ///< The literal character
    
    explicit ClassLiteral(const std::string& ch)
        : ch(ch) {}
    
    std::map<std::string, std::string> toDict() const override;
};

/**
 * @brief Escape sequence in a character class
 * 
 * Represents escape sequences like \d, \w, \s, \p{...}, etc.
 */
class ClassEscape : public ClassItem {
public:
    std::string type;                    ///< Escape type: d, D, w, W, s, S, p, P
    std::optional<std::string> property; ///< Unicode property for \p and \P
    
    explicit ClassEscape(const std::string& type, const std::optional<std::string>& property = std::nullopt)
        : type(type), property(property) {}
    
    std::map<std::string, std::string> toDict() const override;
};

/**
 * @brief Character class node
 * 
 * Represents a character class like [a-z0-9] or [^abc].
 */
class CharClass : public Node {
public:
    bool negated;                      ///< Whether the class is negated ([^...])
    std::vector<ClassItemPtr> items;   ///< The items in the character class
    
    CharClass(bool negated, std::vector<ClassItemPtr> items)
        : negated(negated), items(std::move(items)) {}
    
    std::map<std::string, std::string> toDict() const override;
};

/**
 * @brief Quantifier node
 * 
 * Represents quantification like *, +, ?, {n,m}, etc.
 */
class Quant : public Node {
public:
    NodePtr child;                       ///< The child node being quantified
    int min;                             ///< Minimum repetitions
    std::variant<int, std::string> max;  ///< Maximum repetitions (int or "Inf")
    std::string mode;                    ///< Quantifier mode: "Greedy" | "Lazy" | "Possessive"
    
    Quant(NodePtr child, int min, const std::variant<int, std::string>& max, const std::string& mode)
        : child(std::move(child)), min(min), max(max), mode(mode) {}
    
    std::map<std::string, std::string> toDict() const override;
};

/**
 * @brief Group node
 * 
 * Represents grouping with optional capturing like (...) or (?:...).
 */
class Group : public Node {
public:
    bool capturing;                ///< Whether the group is capturing
    NodePtr body;                  ///< The grouped content
    std::optional<std::string> name;    ///< Named capture group name
    std::optional<bool> atomic;    ///< Atomic group flag (extension)
    
    Group(bool capturing, NodePtr body, const std::optional<std::string>& name = std::nullopt,
          const std::optional<bool>& atomic = std::nullopt)
        : capturing(capturing), body(std::move(body)), name(name), atomic(atomic) {}
    
    std::map<std::string, std::string> toDict() const override;
};

/**
 * @brief Backreference node
 * 
 * Represents a backreference to a capturing group like \1 or \k<name>.
 */
class Backref : public Node {
public:
    std::optional<int> byIndex;         ///< Reference by index (1-based)
    std::optional<std::string> byName;  ///< Reference by name
    
    Backref(const std::optional<int>& byIndex = std::nullopt,
            const std::optional<std::string>& byName = std::nullopt)
        : byIndex(byIndex), byName(byName) {}
    
    std::map<std::string, std::string> toDict() const override;
};

/**
 * @brief Lookahead/Lookbehind node
 * 
 * Represents lookaround assertions like (?=...) or (?<!...).
 */
class Look : public Node {
public:
    std::string dir;  ///< Direction: "Ahead" | "Behind"
    bool neg;         ///< Whether the lookaround is negative
    NodePtr body;     ///< The lookaround content
    
    Look(const std::string& dir, bool neg, NodePtr body)
        : dir(dir), neg(neg), body(std::move(body)) {}
    
    std::map<std::string, std::string> toDict() const override;
};

} // namespace core
} // namespace strling

#endif // STRLING_CORE_NODES_HPP
