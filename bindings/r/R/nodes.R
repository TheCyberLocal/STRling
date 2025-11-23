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
strling_class_literal <- function(char) {
  structure(list(type = "ClassLiteral", char = char), class = c("strling_class_literal", "strling_node"))
}

#' @export
strling_class_range <- function(from, to) {
  structure(list(type = "ClassRange", from = from, to = to), class = c("strling_class_range", "strling_node"))
}

#' @export
strling_class_escape <- function(type, property = NULL) {
  structure(list(type = "ClassEscape", type_ = type, property = property), class = c("strling_class_escape", "strling_node"))
}

#' @export
strling_character_class <- function(items, negated = FALSE) {
  structure(list(type = "CharacterClass", items = items, negated = negated), class = c("strling_character_class", "strling_node"))
}

#' @export
strling_quantifier <- function(child, min, max, mode = "Greedy") {
  structure(list(type = "Quantifier", child = child, min = min, max = max, mode = mode), class = c("strling_quantifier", "strling_node"))
}

#' @export
strling_group <- function(child, capturing = TRUE, name = NULL, atomic = FALSE) {
  structure(list(type = "Group", child = child, capturing = capturing, name = name, atomic = atomic), class = c("strling_group", "strling_node"))
}

#' @export
strling_backreference <- function(index = NULL, name = NULL) {
  structure(list(type = "Backreference", index = index, name = name), class = c("strling_backreference", "strling_node"))
}

#' @export
strling_lookaround <- function(child, kind, negated = FALSE) {
  structure(list(type = "Lookaround", child = child, kind = kind, negated = negated), class = c("strling_lookaround", "strling_node"))
}

#' @export
strling_anchor <- function(at) {
  structure(list(type = "Anchor", at = at), class = c("strling_anchor", "strling_node"))   
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
    branches_data <- json_node$branches
    if (is.null(branches_data)) {
      branches_data <- json_node$alternatives
    }
    branches <- lapply(branches_data, hydrate_ast)
    return(strling_alternation(branches))
  } else if (type == "CharacterClass") {
    items <- list()
    if (!is.null(json_node$members)) {
      items <- lapply(json_node$members, function(member) {
        m_type <- member$type
        if (m_type == "Literal") {
          return(strling_class_literal(member$value))
        } else if (m_type == "Range") {
          return(strling_class_range(member$from, member$to))
        } else if (m_type == "Escape") {
          kind <- member$kind
          type_code <- switch(kind,
            "digit" = "d", "not-digit" = "D",
            "word" = "w", "not-word" = "W",
            "whitespace" = "s", "not-whitespace" = "S",
            "space" = "s", "not-space" = "S",
            "property" = "p", "not-property" = "P",
            stop(paste("Unknown escape kind:", kind))
          )
          prop <- if (kind %in% c("property", "not-property")) member$value else NULL
          return(strling_class_escape(type_code, prop))
        } else if (m_type == "UnicodeProperty") {
          type_code <- if (isTRUE(member$negated)) "P" else "p"
          return(strling_class_escape(type_code, member$value))
        } else {
          stop(paste("Unknown class member type:", m_type))
        }
      })
    } else if (!is.null(json_node$ranges)) {
        ranges <- json_node$ranges
        if (is.matrix(ranges)) {
            ranges <- split(ranges, row(ranges))
            ranges <- lapply(ranges, as.list)
        }
        items <- lapply(ranges, function(r) strling_class_range(r[[1]], r[[2]]))
    }
    return(strling_character_class(items, isTRUE(json_node$negated)))
  } else if (type == "Quantifier") {
    child <- hydrate_ast(json_node$target)
    mode <- "Greedy"
    if (isTRUE(json_node$possessive)) {
      mode <- "Possessive"
    } else if (isTRUE(json_node$lazy)) {
      mode <- "Lazy"
    }
    return(strling_quantifier(child, json_node$min, json_node$max, mode))
  } else if (type == "Group") {
    child <- hydrate_ast(json_node$expression)
    node <- strling_group(child, isTRUE(json_node$capturing), json_node$name, isTRUE(json_node$atomic))
    return(node)
  } else if (type == "Anchor") {
    at <- json_node$at
    if (at == "NonWordBoundary") {
      at <- "NotWordBoundary"
    }
    return(strling_anchor(at))
  } else if (type == "Backreference") {
    return(strling_backreference(json_node$index, json_node$name))
  } else if (type == "Lookahead") {
    child <- hydrate_ast(json_node$body)
    return(strling_lookaround(child, "Lookahead", FALSE))
  } else if (type == "NegativeLookahead") {
    child <- hydrate_ast(json_node$body)
    return(strling_lookaround(child, "Lookahead", TRUE))
  } else if (type == "Lookbehind") {
    child <- hydrate_ast(json_node$body)
    return(strling_lookaround(child, "Lookbehind", FALSE))
  } else if (type == "NegativeLookbehind") {
    child <- hydrate_ast(json_node$body)
    return(strling_lookaround(child, "Lookbehind", TRUE))
  } else if (type == "Dot") {
    return(strling_dot())
  } else {
    stop(paste("Unknown AST node type:", type))
  }
}
