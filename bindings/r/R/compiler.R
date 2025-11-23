#' Compile AST to IR
#'
#' @description
#' Compiles an AST node into its Intermediate Representation (IR).
#'
#' @param node An S3 object representing an AST node.
#' @return A list representing the IR node.
#' @export
compile_ast <- function(node) {
  UseMethod("compile_ast")
}

#' @export
compile_ast.strling_literal <- function(node) {
  list(ir = "Lit", value = node$value)
}

#' @export
compile_ast.strling_sequence <- function(node) {
  parts <- lapply(node$parts, compile_ast)
  list(ir = "Seq", parts = parts)
}

#' @export
compile_ast.strling_alternation <- function(node) {
  branches <- lapply(node$branches, compile_ast)
  list(ir = "Alt", branches = branches)
}

#' @export
compile_ast.strling_character_class <- function(node) {
  list(ir = "CharClass", ranges = node$ranges, negated = node$negated)
}

#' @export
compile_ast.strling_quantifier <- function(node) {
  child <- compile_ast(node$child)
  list(ir = "Quant", child = child, min = node$min, max = node$max, greedy = node$greedy)
}

#' @export
compile_ast.strling_group <- function(node) {
  # Groups might be flattened or represented differently in IR depending on the spec.
  # For now, we'll assume a direct mapping or that the IR handles groups explicitly if needed.
  # If the IR doesn't have "Group", it might be just the child.
  # However, looking at typical regex IRs, capturing groups are often explicit.
  # Let's assume "Group" exists in IR for now, or check if we should just return the child.
  # Given the "Thin Wrapper" instruction, let's map it to "Group" if it's capturing, 
  # or just the child if it's non-capturing and the IR doesn't distinguish.
  # But wait, the prompt says "derive correctness solely from the Shared JSON AST Suite".
  # I'll assume a direct mapping for now:
  child <- compile_ast(node$child)
  list(ir = "Group", child = child, capturing = node$capturing, name = node$name)
}

#' @export
compile_ast.strling_anchor <- function(node) {
  list(ir = "Anchor", kind = node$kind)
}

#' @export
compile_ast.strling_dot <- function(node) {
  list(ir = "Dot")
}

#' @export
compile_ast.default <- function(node) {
  stop(paste("Unknown AST node class:", class(node)[1]))
}
