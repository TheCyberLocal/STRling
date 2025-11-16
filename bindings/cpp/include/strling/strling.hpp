/**
 * @file strling.hpp
 * @brief Main public API header for STRling C++ binding
 * 
 * This is the primary include file for the STRling C++ library. It provides
 * access to all public APIs for parsing, compiling, and working with STRling
 * patterns.
 * 
 * STRling is a next-generation production-grade syntax designed as a user
 * interface for writing powerful regular expressions with an object-oriented
 * approach and instructional error handling.
 * 
 * @copyright Copyright (c) 2024 TheCyberLocal
 * @license MIT License
 */

#ifndef STRLING_HPP
#define STRLING_HPP

#include <string>
#include <memory>

namespace strling {

/**
 * @brief Main parser class for STRling patterns (stub for Task 2)
 * 
 * The Parser class is responsible for parsing STRling pattern syntax into
 * an Abstract Syntax Tree (AST). This is a stub that will be implemented
 * in Task 2.
 */
class Parser {
public:
    /**
     * @brief Parse a STRling pattern string into an AST (stub)
     * 
     * @param pattern The STRling pattern to parse
     * @return Parsed AST representation (to be implemented)
     */
    // Implementation will be added in Task 2
    
private:
    // Internal implementation details to be added in Task 2
};

/**
 * @brief Main compiler class for converting AST to IR (stub for Task 2)
 * 
 * The Compiler class is responsible for transforming the Abstract Syntax Tree
 * into the Intermediate Representation (IR) for further processing. This is
 * a stub that will be implemented in Task 2.
 */
class Compiler {
public:
    /**
     * @brief Compile an AST to IR (stub)
     * 
     * @param ast The AST to compile
     * @return IR representation (to be implemented)
     */
    // Implementation will be added in Task 2
    
private:
    // Internal implementation details to be added in Task 2
};

} // namespace strling

#endif // STRLING_HPP
