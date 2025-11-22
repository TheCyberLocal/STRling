#include "strling/compiler.hpp"
#include <stdexcept>
#include <iostream>

namespace strling {

ir::IRNodePtr compile(const ast::NodePtr& node) {
    if (!node) return nullptr;
    
    std::string type = node->get_type();

    if (type == "Literal") {
        auto n = static_cast<ast::Literal*>(node.get());
        auto ir_node = std::make_unique<ir::Lit>();
        ir_node->value = n->value;
        return ir_node;
    } else if (type == "Sequence") {
        auto n = static_cast<ast::Sequence*>(node.get());
        auto ir_node = std::make_unique<ir::Seq>();
        for (const auto& item : n->items) {
            auto compiled_item = compile(item);
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
            ir_node->branches.push_back(compile(item));
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
        ir_node->body = compile(n->child);
        ir_node->capturing = n->capturing;
        ir_node->atomic = n->atomic;
        ir_node->name = n->name;
        return ir_node;
    } else if (type == "Quantifier") {
        auto n = static_cast<ast::Quantifier*>(node.get());
        auto ir_node = std::make_unique<ir::Quant>();
        ir_node->child = compile(n->child);
        ir_node->min = n->min;
        ir_node->max = n->max;
        ir_node->mode = n->possessive ? "Possessive" : (n->greedy ? "Greedy" : "Lazy");
        return ir_node;
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
        ir_node->body = compile(n->child);
        ir_node->dir = "Ahead";
        ir_node->neg = !n->positive;
        return ir_node;
    } else if (type == "Lookbehind") {
        auto n = static_cast<ast::Lookbehind*>(node.get());
        auto ir_node = std::make_unique<ir::Look>();
        ir_node->body = compile(n->child);
        ir_node->dir = "Behind";
        ir_node->neg = !n->positive;
        return ir_node;
    }
    
    throw std::runtime_error("Compiler: Unknown AST node type: " + type);
}

} // namespace strling
