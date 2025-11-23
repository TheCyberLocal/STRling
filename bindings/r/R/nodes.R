#' AST Node Constructors
#'
#' @description
#' S3 constructors for STRling AST nodes.

#' @export
strling_literal <- function(value) {
  structure(list(type = "Literal", value = value), class = c("strling_literal", "strling_node"))
}

#' @export
strling_sequence <- function(parts) {
  structure(list(type = "Sequence", parts = parts), class = c("strling_sequence", "strling_node"))
}

#' @export
strling_alternation <- function(branches) {
  structure(list(type = "Alternation", branches = branches), class = c("strling_alternation", "strling_node"))
}

#' @export
strling_character_class <- function(ranges, negated = FALSE) {
  structure(list(type = "CharacterClass", ranges = ranges, negated = negated), class = c("strling_character_class", "strling_node"))
}

#' @export
strling_quantifier <- function(child, min, max, greedy = TRUE) {
  structure(list(type = "Quantifier", child = child, min = min, max = max, greedy = greedy), class = c("strling_quantifier", "strling_node"))
}

#' @export
strling_group <- function(child, capturing = TRUE, name = NULL) {
  structure(list(type = "Group", child = child, capturing = capturing, name = name), class = c("strling_group", "strling_node"))
}

#' @export
strling_anchor <- function(kind) {
  structure(list(type = "Anchor", kind = kind), class = c("strling_anchor", "strling_node"))
}

#' @export
strling_dot <- function() {
  structure(list(type = "Dot"), class = c("strling_dot", "strling_node"))
}

#' Hydrate AST from JSON
#'
#' @param json_node A list parsed from JSON representing an AST node.
#' @return An S3 object representing the AST node.
#' @export
hydrate_ast <- function(json_node) {
  if (is.null(json_node)) return(NULL)
  
  type <- json_node$type
  
  if (is.null(type)) {
    stop("Invalid AST node: missing 'type' field")
  }
  
  if (type == "Literal") {
    return(strling_literal(json_node$value))
  } else if (type == "Sequence") {
    parts <- lapply(json_node$parts, hydrate_ast)
    return(strling_sequence(parts))
  } else if (type == "Alternation") {
    branches <- lapply(json_node$branches, hydrate_ast)
    return(strling_alternation(branches))
  } else if (type == "CharacterClass") {
    # ranges might be a list of lists or a matrix depending on jsonlite parsing
    # We expect a list of ranges, where each range is a list/vector of [start, end]
    ranges <- json_node$ranges
    # Ensure ranges is a list of lists if it came in as a matrix or something else
    if (is.matrix(ranges)) {
        ranges <- split(ranges, row(ranges))
        ranges <- lapply(ranges, as.list)
    }
    return(strling_character_class(ranges, isTRUE(json_node$negated)))
  } else if (type == "Quantifier") {
    child <- hydrate_ast(json_node$child)
    return(strling_quantifier(child, json_node$min, json_node$max, isTRUE(json_node$greedy)))
  } else if (type == "Group") {
    child <- hydrate_ast(json_node$child)
    return(strling_group(child, isTRUE(json_node$capturing), json_node$name))
  } else if (type == "Anchor") {
    return(strling_anchor(json_node$kind))
  } else if (type == "Dot") {
    return(strling_dot())
  } else {
    stop(paste("Unknown AST node type:", type))
  }
}
