#include <iostream>
#include <fstream>
#include <filesystem>
#include <vector>
#include <nlohmann/json.hpp>
#include "strling/ast.hpp"
#include "strling/compiler.hpp"
#include "strling/ir.hpp"

namespace fs = std::filesystem;
using json = nlohmann::json;

#ifndef SPEC_DIR
#define SPEC_DIR "."
#endif

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

            // Check if it has input_ast and expected_ir
            if (!j.contains("input_ast") || !j.contains("expected_ir")) {
                // Maybe it's a different format or meta file
                continue;
            }

            total++;
            try {
                auto ast = strling::ast::from_json(j.at("input_ast"));
                auto ir = strling::compile(ast);
                json generated_ir = ir->to_json();
                json expected_ir = j.at("expected_ir");

                if (generated_ir == expected_ir) {
                    passed++;
                } else {
                    failed++;
                    std::cerr << "Test failed: " << entry.path().filename() << "\n";
                    std::cerr << "Expected: " << expected_ir.dump(2) << "\n";
                    std::cerr << "Got: " << generated_ir.dump(2) << "\n";
                }
            } catch (const std::exception& e) {
                failed++;
                std::cerr << "Test error: " << entry.path().filename() << " - " << e.what() << "\n";
            }
        }
    }

    std::cout << "Total: " << total << ", Passed: " << passed << ", Failed: " << failed << "\n";
    return failed > 0 ? 1 : 0;
}
