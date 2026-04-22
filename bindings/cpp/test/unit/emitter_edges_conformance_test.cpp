/**
 * @file emitter_edges_conformance_test.cpp
 * @brief C++ runner for the global pathological-AST fixture.
 *
 * Mirrors `bindings/typescript/__tests__/unit/emitter_edges_conformance.test.ts`
 * and `bindings/c/tests/unit/emitter_edges_conformance_test.c` to verify
 * that the C++ compiler enforces the same three SSOT safety guards:
 *
 *   1. Variable-Length Lookbehind Rejection  — throws std::runtime_error
 *   2. AST Depth Limit Exceeded              — throws std::runtime_error
 *   3. ReDoS Risk Warning (nested `(a+)+`)   — surfaces in CompileResult.warnings
 *
 * The C++ AST is built directly with `std::make_unique` rather than via a
 * JSON adapter — this keeps the test hermetic and decoupled from the
 * shared JSON fixture's wire format, while still exercising the same
 * pathological shapes encoded in
 * `tests/conformance/inputs/emitter_edges/pathological.json`.
 */

#include <gtest/gtest.h>

#include "strling/ast.hpp"
#include "strling/compiler.hpp"

#include <memory>
#include <string>

using namespace strling;

namespace {

ast::NodePtr make_literal(const std::string& s) {
    auto n = std::make_unique<ast::Literal>();
    n->value = s;
    return n;
}

ast::NodePtr make_unbounded_quant(ast::NodePtr child, int min = 1) {
    auto q = std::make_unique<ast::Quantifier>();
    q->min = min;
    q->max = -1; // unbounded (matches TS / C `max=null` convention)
    q->greedy = true;
    q->child = std::move(child);
    return q;
}

ast::NodePtr make_group(ast::NodePtr child) {
    auto g = std::make_unique<ast::Group>();
    g->capturing = true;
    g->child = std::move(child);
    return g;
}

bool warning_mentions(const std::vector<std::string>& warnings,
                     const std::string& code,
                     const std::string& needle) {
    for (const auto& w : warnings) {
        if (w.find(code) != std::string::npos &&
            w.find(needle) != std::string::npos) {
            return true;
        }
    }
    return false;
}

} // namespace

// --- Vector 1: Variable-Length Lookbehind Rejection -----------------------
TEST(EmitterEdgesConformance, RejectsVariableLengthLookbehind) {
    // Lookbehind { content: Quantifier(min=1, max=null, Literal("a")) }
    auto lb_typed = std::make_unique<ast::Lookbehind>();
    lb_typed->positive = true;
    lb_typed->child = make_unbounded_quant(make_literal("a"));
    ast::NodePtr lb = std::move(lb_typed);

    try {
        (void)compile_with_diagnostics(lb);
        FAIL() << "Expected std::runtime_error for variable-length lookbehind";
    } catch (const std::runtime_error& e) {
        const std::string msg(e.what());
        EXPECT_NE(msg.find("PCRE2 does not support variable-length lookbehinds"),
                  std::string::npos)
            << "actual: " << msg;
    }
}

// --- Vector 2: AST Depth Limit Exceeded -----------------------------------
TEST(EmitterEdgesConformance, RejectsAstExceedingDepthLimit) {
    // Three nested groups, depth cap of 2 → must abort.
    auto deepest = make_literal("deep");
    auto g1 = make_group(std::move(deepest));
    auto g2 = make_group(std::move(g1));
    auto g3 = make_group(std::move(g2));

    try {
        (void)compile_with_diagnostics(g3, /*max_depth=*/2);
        FAIL() << "Expected std::runtime_error for depth-limit exceeded";
    } catch (const std::runtime_error& e) {
        const std::string msg(e.what());
        EXPECT_NE(msg.find("Maximum AST depth exceeded"), std::string::npos)
            << "actual: " << msg;
    }
}

// --- Vector 3: ReDoS Risk Warning (nested unbounded quantifiers) ----------
TEST(EmitterEdgesConformance, FlagsRedosRiskOnNestedUnboundedQuantifiers) {
    // (a+)+  →  Quantifier{ Quantifier{ Literal("a") } }
    auto inner = make_unbounded_quant(make_literal("a"));
    auto outer = make_unbounded_quant(std::move(inner));

    CompileResult result = compile_with_diagnostics(outer);
    ASSERT_NE(result.ir, nullptr);
    EXPECT_TRUE(warning_mentions(result.warnings,
                                 kStrlingWarningRedosRisk,
                                 "nested unbounded quantifiers"))
        << "expected REDOS_RISK warning; got " << result.warnings.size()
        << " warnings";
}

// --- Negative control: depth guard does not fire under the cap -----------
TEST(EmitterEdgesConformance, AllowsAstUnderDepthCap) {
    auto deepest = make_literal("ok");
    auto g1 = make_group(std::move(deepest));
    auto g2 = make_group(std::move(g1));

    CompileResult result = compile_with_diagnostics(g2, /*max_depth=*/5);
    EXPECT_NE(result.ir, nullptr);
    EXPECT_TRUE(result.warnings.empty());
}

// --- Negative control: simple literal raises no warnings -----------------
TEST(EmitterEdgesConformance, NonPathologicalPatternHasNoWarnings) {
    CompileResult result = compile_with_diagnostics(make_literal("abc"));
    ASSERT_NE(result.ir, nullptr);
    EXPECT_TRUE(result.warnings.empty());
}
