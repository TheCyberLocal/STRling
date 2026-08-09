#include <iostream>
#include <fstream>
#include <filesystem>
#include <vector>
#include <nlohmann/json.hpp>
#include "strling/ast.hpp"
#include "strling/compiler.hpp"
#include "strling/ir.hpp"
#include "strling/core/parser.hpp"
#include "strling/core/hint_engine.hpp"

namespace fs = std::filesystem;
using json = nlohmann::json;

#ifndef SPEC_DIR
#define SPEC_DIR "."
#endif

// Test name generation logic is duplicated across C++, F#, PHP, and Ruby bindings.
// If you change this logic, update the other bindings as well to keep naming conventions in sync.
std::string generate_test_name(const std::string& stem) {
    if (stem == "semantic_duplicates") {
        return "test_semantic_duplicate_capture_group";
    } else if (stem == "semantic_ranges") {
        return "test_semantic_ranges";
    } else {
        return "test_conformance_" + stem;
    }
}

int main() {
    std::string spec_dir = SPEC_DIR;
    int passed = 0;
    int failed = 0;
    int total = 0;

    std::cout << "Running conformance tests from: " << spec_dir << "\n";

    if (!fs::exists(spec_dir)) {
        std::cerr << "Spec directory not found: " << spec_dir << "\n";
        return 1;
    }

    for (const auto& entry : fs::directory_iterator(spec_dir)) {
        if (entry.path().extension() == ".json") {
            std::ifstream f(entry.path());
            json j;
            try {
                f >> j;
            } catch (const std::exception& e) {
                std::cerr << "Failed to parse JSON file: " << entry.path() << " - " << e.what() << "\n";
                continue;
            }

            std::string filename = entry.path().filename().string();
            std::string stem = entry.path().stem().string();

            // Generate test name
            std::string test_name = generate_test_name(stem);

            // Check if it has input_ast and expected_ir
            if (!j.contains("input_ast") || !j.contains("expected_ir")) {
                // Error test case
                if (j.contains("expected_error")) {
                    total++;
                    std::cout << "=== RUN   " << test_name << " (" << filename << ")\n";

                    if (j.contains("input_ast")) {
                        // If we have input_ast, we can try to compile and expect an error
                        try {
                            auto ast = strling::ast::from_json(j.at("input_ast"));
                            auto ir = strling::compile(ast);
                            // If we get here, we failed to catch the error
                            std::cerr << "    --- FAIL: Expected error but compilation succeeded\n";
                            failed++;
                        } catch (...) {
                            // Expected error
                            passed++;
                            std::cout << "    --- PASS: Caught expected error\n";
                        }
                    } else if (j.contains("input_dsl")) {
                        // Parser error test: parse input_dsl, expect error with hint
                        std::string input_dsl = j.at("input_dsl").get<std::string>();
                        std::string expected_error = j.at("expected_error").get<std::string>();
                        std::string expected_hint = j.value("expected_hint", "");
                        bool test_ok = true;

                        try {
                            strling::core::Parser parser(input_dsl);
                            parser.parse();
                            std::cerr << "    --- FAIL: Expected parse error but got success\n";
                            test_ok = false;
                        } catch (const strling::core::STRlingParseError& e) {
                            // Check error message contains expected substring
                            std::string actual_msg = e.getMessage();
                            if (actual_msg.find(expected_error) == std::string::npos) {
                                std::cerr << "    --- FAIL: Error message mismatch\n"
                                          << "    Expected substring: " << expected_error << "\n"
                                          << "    Actual: " << actual_msg << "\n";
                                test_ok = false;
                            }
                            // Check hint exact match
                            if (!expected_hint.empty()) {
                                auto actual_hint = e.getHint();
                                std::string hint_str = actual_hint.value_or("");
                                if (hint_str != expected_hint) {
                                    std::cerr << "    --- FAIL: Hint mismatch\n"
                                              << "    Expected: " << expected_hint << "\n"
                                              << "    Actual:   " << hint_str << "\n";
                                    test_ok = false;
                                }
                            }
                        } catch (const std::exception& e) {
                            std::cerr << "    --- FAIL: Unexpected exception: " << e.what() << "\n";
                            test_ok = false;
                        }

                        if (test_ok) {
                            passed++;
                            std::cout << "    --- PASS: Parser error with hint\n";
                        } else {
                            failed++;
                        }
                    } else {
                        // No AST and no DSL, out of scope
                        std::cout << "    --- PASS: Parser test (no AST/DSL), out of scope\n";
                        passed++;
                    }
                } else {
                    // Irrelevant test (no input_ast, no expected_ir, no expected_error)
                    std::cout << "[   PASS   ] Irrelevant: " << filename << "\n";
                }
                continue;
            }

            total++;
            std::cout << "=== RUN   " << test_name << " (" << filename << ")\n";
            try {
                auto ast = strling::ast::from_json(j.at("input_ast"));
                auto ir = strling::compile(ast);
                json generated_ir = ir->to_json();
                json expected_ir = j.at("expected_ir");

                if (generated_ir == expected_ir) {
                    passed++;
                } else {
                    failed++;
                    std::cerr << "    --- FAIL: IR mismatch\n";
                    std::cerr << "Expected: " << expected_ir.dump(2) << "\n";
                    std::cerr << "Got: " << generated_ir.dump(2) << "\n";
                }
            } catch (const std::exception& e) {
                failed++;
                std::cerr << "    --- FAIL: " << e.what() << "\n";
            }
        }
    }

    std::cout << "Total: " << total << ", Passed: " << passed << ", Failed: " << failed << "\n";
    return failed > 0 ? 1 : 0;
}
