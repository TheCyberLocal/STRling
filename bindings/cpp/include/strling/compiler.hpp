#ifndef STRLING_COMPILER_HPP
#define STRLING_COMPILER_HPP

#include "strling/ast.hpp"
#include "strling/ir.hpp"

namespace strling {

ir::IRNodePtr compile(const ast::NodePtr& ast);

} // namespace strling

#endif // STRLING_COMPILER_HPP
