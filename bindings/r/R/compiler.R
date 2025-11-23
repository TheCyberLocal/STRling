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
  
  # Merge adjacent literals
  merged_parts <- list()
  if (length(parts) > 0) {
    current <- parts[[1]]
    if (length(parts) > 1) {
      for (i in 2:length(parts)) {
        next_part <- parts[[i]]
        if (current$ir == "Lit" && next_part$ir == "Lit") {
          current$value <- paste0(current$value, next_part$value)
        } else {
          merged_parts <- c(merged_parts, list(current))
          current <- next_part
        }
      }
    }
    merged_parts <- c(merged_parts, list(current))
  }
  
  if (length(merged_parts) == 1) {
    return(merged_parts[[1]])
  } else {
    list(ir = "Seq", parts = merged_parts)
  }
}

#' @export
compile_ast.strling_alternation <- function(node) {
  branches <- lapply(node$branches, compile_ast)
  list(ir = "Alt", branches = branches)
}

#' @export
compile_ast.strling_character_class <- function(node) {
  items <- lapply(node$items, compile_ast)
  list(ir = "CharClass", negated = node$negated, items = items)
}

#' @export
compile_ast.strling_class_literal <- function(node) {
  list(ir = "Char", char = node$char)
}

#' @export
compile_ast.strling_class_range <- function(node) {
  list(ir = "Range", from = node$from, to = node$to)
}

#' @export
compile_ast.strling_class_escape <- function(node) {
  res <- list(ir = "Esc", type = node$type_)
  if (!is.null(node$property)) {
    res$property <- node$property
  }
  res
}

#' @export
compile_ast.strling_quantifier <- function(node) {
  child <- compile_ast(node$child)
  max_val <- if (is.null(node$max)) "Inf" else node$max
  list(ir = "Quant", child = child, min = node$min, max = max_val, mode = node$mode)
}

#' @export
compile_ast.strling_group <- function(node) {
  child <- compile_ast(node$child)
  res <- list(ir = "Group", capturing = node$capturing, body = child)
  if (!is.null(node$name)) {
    res$name <- node$name
  }
  if (isTRUE(node$atomic)) {
    res$atomic <- TRUE
  }
  res
}

#' @export
compile_ast.strling_anchor <- function(node) {
  list(ir = "Anchor", at = node$at)
}

#' @export
compile_ast.strling_backreference <- function(node) {
  res <- list(ir = "Backref")
  if (!is.null(node$index)) res$byIndex <- node$index
  if (!is.null(node$name)) res$byName <- node$name
  res
}

#' @export
compile_ast.strling_lookaround <- function(node) {
  child <- compile_ast(node$child)
  dir <- if (node$kind == "Lookahead") "Ahead" else "Behind"
  list(ir = "Look", dir = dir, neg = node$negated, body = child)
}

#' @export
compile_ast.strling_dot <- function(node) {
  list(ir = "Dot")
}

#' @export
compile_ast.default <- function(node) {
  stop(paste("Unknown AST node class:", class(node)[1]))
}
