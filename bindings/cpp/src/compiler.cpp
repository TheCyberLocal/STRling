/**
 * @file compiler.cpp
 * @brief AST → IR lowering for the C++ binding.
 *
 * Parity with the TypeScript SSOT: this file threads an
 * `EmitContext` through the recursive walk so the same three safety
 * guards observed by the reference implementation are enforced here:
 *
 *   1. **AST depth limit** — refuses pathologically deep ASTs that
 *      could blow the host stack.
 *   2. **Variable-length lookbehind rejection** — PCRE2 (and most
 *      backends) cannot run a lookbehind whose body has variable width.
 *   3. **ReDoS risk warnings** — flags nested unbounded quantifiers
 *      (the classic `(a+)+` shape) so callers can surface them without
 *      aborting compilation.
 *
 * Error messages are kept verbatim with the TypeScript and C bindings to
 * preserve cross-binding parity assertions in conformance tests.
 */

#include "strling/compiler.hpp"

#include <stdexcept>
#include <string>
#include <vector>

namespace strling {

namespace {

/// Per-walk state shared by all recursive `compile_node` invocations.
struct EmitContext {
    int depth = 0;
    int max_depth = kStrlingDefaultMaxDepth;
    bool in_lookbehind = false;
    std::vector<std::string> warnings;

    void push_warning(const std::string& code, const std::string& msg) {
        warnings.push_back(code + ": " + msg);
    }
};

/// True if this AST node is a quantifier whose upper bound is unbounded.
/// Mirrors `_isUnboundedQuant` in the TypeScript reference implementation.
bool _is_unbounded_quant(const ast::Node* n) {
    if (!n) return false;
    if (n->get_type() != "Quantifier") return false;
    const auto* q = static_cast<const ast::Quantifier*>(n);
    /* Convention: max == -1 (or any negative) means infinity. */
    return q->max < 0;
}

/// True if every direct child of a sequence/alternation has a fixed
/// width (no variable-length quantifier and no nested variable-length
/// lookaround). Used by the lookbehind validator.
bool _is_fixed_length_body(const ast::Node* n);

bool _all_parts_fixed(const std::vector<ast::NodePtr>& items) {
    for (const auto& it : items) {
        if (!_is_fixed_length_body(it.get())) return false;
    }
    return true;
}

bool _is_fixed_length_body(const ast::Node* n) {
    if (!n) return true;
    const std::string t = n->get_type();
    if (t == "Quantifier") {
        const auto* q = static_cast<const ast::Quantifier*>(n);
        /* A {N,N} quantifier is fixed-length; any other shape is not. */
        if (q->max < 0) return false;
        if (q->min != q->max) return false;
        return _is_fixed_length_body(q->child.get());
    }
    if (t == "Sequence") {
        return _all_parts_fixed(static_cast<const ast::Sequence*>(n)->items);
    }
    if (t == "Alternation") {
        return _all_parts_fixed(static_cast<const ast::Alternation*>(n)->items);
    }
    if (t == "Group") {
        return _is_fixed_length_body(static_cast<const ast::Group*>(n)->child.get());
    }
    /* Literal, Range, Escape, Anchor, Dot, CharacterClass, Backref,
     * UnicodeProperty are all treated as fixed-width here — same shape
     * as the TS reference. Anchors are zero-width but that is fine. */
    return true;
}

/// True if `n` contains an unbounded quantifier nested inside another
/// unbounded quantifier — the canonical ReDoS pattern. Mirrors
/// `_hasNestedUnboundedQuant` in the TypeScript reference.
/// True when `n` is *itself* an unbounded quantifier OR (for transparent
/// wrappers like Group, single-part Sequence, Alternation) recursively
/// contains one in tail position. Mirrors `_hasNestedUnboundedQuant` in
/// the TypeScript reference and the matching C predicate.
bool _has_nested_unbounded_quant(const ast::Node* n) {
    if (!n) return false;
    const std::string t = n->get_type();
    if (t == "Quantifier") {
        return _is_unbounded_quant(n);
    }
    if (t == "Group") {
        return _has_nested_unbounded_quant(
            static_cast<const ast::Group*>(n)->child.get());
    }
    if (t == "Sequence") {
        const auto& items = static_cast<const ast::Sequence*>(n)->items;
        if (items.size() == 1) {
            return _has_nested_unbounded_quant(items[0].get());
        }
        return false;
    }
    if (t == "Alternation") {
        for (const auto& it : static_cast<const ast::Alternation*>(n)->items) {
            if (_has_nested_unbounded_quant(it.get())) return true;
        }
    }
    return false;
}

ir::IRNodePtr compile_node(const ast::NodePtr& node, EmitContext& ctx);

ir::IRNodePtr _compile_quantifier(const ast::Quantifier* n, EmitContext& ctx) {
    /* ReDoS risk fires before lowering the child so the warning text
     * reflects the outer-quantifier shape the user wrote. */
    if (_is_unbounded_quant(n) && _has_nested_unbounded_quant(n->child.get())) {
        ctx.push_warning(
            kStrlingWarningRedosRisk,
            "Pattern contains nested unbounded quantifiers and may exhibit "
            "catastrophic backtracking (ReDoS) on adversarial input.");
    }

    auto ir_node = std::make_unique<ir::Quant>();
    ir_node->child = compile_node(n->child, ctx);
    ir_node->min = n->min;
    ir_node->max = n->max;
    ir_node->mode = n->possessive ? "Possessive" : (n->greedy ? "Greedy" : "Lazy");
    return ir_node;
}

ir::IRNodePtr _compile_lookbehind(const ast::Lookbehind* n, EmitContext& ctx) {
    /* PCRE2 mandates a fixed-width body. Reject *before* recursion so
     * the user gets a single, precise error rather than a cascade. */
    if (!_is_fixed_length_body(n->child.get())) {
        throw std::runtime_error(
            "PCRE2 does not support variable-length lookbehinds.");
    }

    const bool prev = ctx.in_lookbehind;
    ctx.in_lookbehind = true;
    auto ir_node = std::make_unique<ir::Look>();
    ir_node->body = compile_node(n->child, ctx);
    ir_node->dir = "Behind";
    ir_node->neg = !n->positive;
    ctx.in_lookbehind = prev;
    return ir_node;
}

ir::IRNodePtr compile_node(const ast::NodePtr& node, EmitContext& ctx) {
    if (!node) return nullptr;

    /* Depth tracking happens at every recursion boundary. Increment on
     * entry, check, decrement on every return path via RAII. */
    struct DepthGuard {
        EmitContext& c;
        explicit DepthGuard(EmitContext& cx) : c(cx) { ++c.depth; }
        ~DepthGuard() { --c.depth; }
    } depth_guard(ctx);

    if (ctx.depth > ctx.max_depth) {
        throw std::runtime_error(
            "Maximum AST depth exceeded (" + std::to_string(ctx.max_depth) +
            "). The pattern is too deeply nested.");
    }

    const std::string type = node->get_type();

    if (type == "Literal") {
        auto n = static_cast<ast::Literal*>(node.get());
        auto ir_node = std::make_unique<ir::Lit>();
        ir_node->value = n->value;
        return ir_node;
    } else if (type == "Sequence") {
        auto n = static_cast<ast::Sequence*>(node.get());
        auto ir_node = std::make_unique<ir::Seq>();
        for (const auto& item : n->items) {
            auto compiled_item = compile_node(item, ctx);
            if (!ir_node->parts.empty()) {
                auto last_lit = dynamic_cast<ir::Lit*>(ir_node->parts.back().get());
                auto curr_lit = dynamic_cast<ir::Lit*>(compiled_item.get());
                if (last_lit && curr_lit) {
                    last_lit->value += curr_lit->value;
                    continue;
                }
            }
            ir_node->parts.push_back(std::move(compiled_item));
        }

        if (ir_node->parts.size() == 1) {
            return std::move(ir_node->parts[0]);
        }

        return ir_node;
    } else if (type == "Alternation") {
        auto n = static_cast<ast::Alternation*>(node.get());
        auto ir_node = std::make_unique<ir::Alt>();
        for (const auto& item : n->items) {
            ir_node->branches.push_back(compile_node(item, ctx));
        }
        return ir_node;
    } else if (type == "CharacterClass") {
        auto n = static_cast<ast::CharacterClass*>(node.get());
        auto ir_node = std::make_unique<ir::CharClass>();
        ir_node->negated = n->negated;
        for (const auto& item : n->members) {
            std::string item_type = item->get_type();
            if (item_type == "Literal") {
                auto lit = static_cast<ast::Literal*>(item.get());
                for (char c : lit->value) {
                    auto ch = std::make_unique<ir::Char>();
                    ch->value = std::string(1, c);
                    ir_node->items.push_back(std::move(ch));
                }
            } else if (item_type == "Range") {
                auto rng = static_cast<ast::Range*>(item.get());
                auto ir_rng = std::make_unique<ir::Range>();
                ir_rng->from = rng->from;
                ir_rng->to = rng->to;
                ir_node->items.push_back(std::move(ir_rng));
            } else if (item_type == "Escape") {
                 auto esc = static_cast<ast::Escape*>(item.get());
                 auto ir_esc = std::make_unique<ir::Esc>();
                 if (esc->kind == "word") ir_esc->type = "w";
                 else if (esc->kind == "digit") ir_esc->type = "d";
                 else if (esc->kind == "space") ir_esc->type = "s";
                 else if (esc->kind == "not-word") ir_esc->type = "W";
                 else if (esc->kind == "not-digit") ir_esc->type = "D";
                 else if (esc->kind == "not-space") ir_esc->type = "S";
                 else ir_esc->type = esc->kind;
                 ir_node->items.push_back(std::move(ir_esc));
            } else if (item_type == "UnicodeProperty") {
                 auto prop = static_cast<ast::UnicodeProperty*>(item.get());
                 auto ir_esc = std::make_unique<ir::Esc>();
                 ir_esc->type = prop->negated ? "P" : "p";
                 ir_esc->property = prop->value;
                 ir_node->items.push_back(std::move(ir_esc));
            }
        }
        return ir_node;
    } else if (type == "Anchor") {
        auto n = static_cast<ast::Anchor*>(node.get());
        auto ir_node = std::make_unique<ir::Anchor>();
        ir_node->at = (n->kind == "NonWordBoundary") ? "NotWordBoundary" : n->kind;
        return ir_node;
    } else if (type == "Dot") {
        return std::make_unique<ir::Dot>();
    } else if (type == "Group") {
        auto n = static_cast<ast::Group*>(node.get());
        auto ir_node = std::make_unique<ir::Group>();
        ir_node->body = compile_node(n->child, ctx);
        ir_node->capturing = n->capturing;
        ir_node->atomic = n->atomic;
        ir_node->name = n->name;
        return ir_node;
    } else if (type == "Quantifier") {
        return _compile_quantifier(static_cast<ast::Quantifier*>(node.get()), ctx);
    } else if (type == "Escape") {
        auto n = static_cast<ast::Escape*>(node.get());
        auto ir_node = std::make_unique<ir::Esc>();
        if (n->kind == "word") ir_node->type = "w";
        else if (n->kind == "digit") ir_node->type = "d";
        else if (n->kind == "space") ir_node->type = "s";
        else if (n->kind == "not-word") ir_node->type = "W";
        else if (n->kind == "not-digit") ir_node->type = "D";
        else if (n->kind == "not-space") ir_node->type = "S";
        else ir_node->type = n->kind;
        return ir_node;
    } else if (type == "Backreference") {
        auto n = static_cast<ast::Backreference*>(node.get());
        auto ir_node = std::make_unique<ir::Backref>();
        if (n->index) {
            ir_node->byIndex = *n->index;
        } else if (n->name) {
            ir_node->byName = *n->name;
        }
        return ir_node;
    } else if (type == "Lookahead") {
        auto n = static_cast<ast::Lookahead*>(node.get());
        auto ir_node = std::make_unique<ir::Look>();
        ir_node->body = compile_node(n->child, ctx);
        ir_node->dir = "Ahead";
        ir_node->neg = !n->positive;
        return ir_node;
    } else if (type == "Lookbehind") {
        return _compile_lookbehind(static_cast<ast::Lookbehind*>(node.get()), ctx);
    }

    throw std::runtime_error("Compiler: Unknown AST node type: " + type);
}

} // namespace

CompileResult compile_with_diagnostics(const ast::NodePtr& ast, int max_depth) {
    EmitContext ctx;
    ctx.max_depth = (max_depth > 0) ? max_depth : kStrlingDefaultMaxDepth;
    CompileResult out;
    out.ir = compile_node(ast, ctx);
    out.warnings = std::move(ctx.warnings);
    return out;
}

ir::IRNodePtr compile(const ast::NodePtr& ast) {
    return compile_with_diagnostics(ast, 0).ir;
}

} // namespace strling
