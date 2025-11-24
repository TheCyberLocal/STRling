#' Simply Fluent API for STRling
#'
#' @description
#' High-level fluent API functions for building STRling patterns without
#' manually constructing AST nodes. This provides a cleaner, more intuitive
#' interface matching the Gold Standard naming conventions across all STRling bindings.

#' Match the start of a line (^)
#'
#' @return A STRling AST node representing the start anchor
#' @export
#' @examples
#' sl_start()
sl_start <- function() {
  strling_anchor("Start")
}

#' Match the end of a line ($)
#'
#' @return A STRling AST node representing the end anchor
#' @export
#' @examples
#' sl_end()
sl_end <- function() {
  strling_anchor("End")
}

#' Match exactly n digits
#'
#' @param n Number of digits to match. Must be a positive integer.
#' @return A STRling AST node matching n digits
#' @export
#' @examples
#' sl_digit(3)  # Matches exactly 3 digits
#' sl_digit()   # Matches exactly 1 digit
sl_digit <- function(n = 1L) {
  if (!is.numeric(n) || length(n) != 1) {
    stop("sl_digit expects a single numeric value for n")
  }
  
  if (n <= 0) {
    warning(sprintf("sl_digit: n must be a positive integer, received %s. Defaulting to 1", n))
    n <- 1L
  }
  
  digit_class <- strling_character_class(
    list(strling_class_escape("d")),
    negated = FALSE
  )
  
  if (n == 1L) {
    return(digit_class)
  }
  
  strling_quantifier(digit_class, min = as.integer(n), max = as.integer(n))
}

#' Create a character class matching any of the provided characters
#'
#' @param chars A string where each character is an option to match
#' @return A STRling AST node representing a character class
#' @export
#' @examples
#' sl_any_of("-. ")  # Matches hyphen, period, or space
#' sl_any_of("abc")  # Matches a, b, or c
sl_any_of <- function(chars) {
  if (!is.character(chars) || length(chars) != 1) {
    stop(sprintf(
      "sl_any_of expects a single character string, but received: %s. Example: sl_any_of('abc')",
      paste(class(chars), collapse = ", ")
    ))
  }
  
  char_vec <- strsplit(chars, "")[[1]]
  items <- lapply(char_vec, function(ch) strling_class_literal(ch))
  
  strling_character_class(items, negated = FALSE)
}

#' Merge/concatenate multiple patterns into a sequence
#'
#' @param ... One or more STRling AST nodes to merge in sequence
#' @return A STRling AST node representing the sequence
#' @export
#' @examples
#' sl_merge(sl_start(), sl_digit(3), sl_end())
sl_merge <- function(...) {
  patterns <- list(...)
  
  if (length(patterns) == 0) {
    return(strling_sequence(list()))
  }
  
  if (length(patterns) == 1) {
    return(patterns[[1]])
  }
  
  strling_sequence(patterns)
}

#' Create a capturing group around a pattern
#'
#' @param inner The STRling AST node to wrap in a capturing group
#' @return A STRling AST node representing a capturing group
#' @export
#' @examples
#' sl_capture(sl_digit(3))
sl_capture <- function(inner) {
  strling_group(inner, capturing = TRUE)
}

#' Make a pattern optional (match 0 or 1 times)
#'
#' @param inner The STRling AST node to make optional
#' @return A STRling AST node representing an optional pattern
#' @export
#' @examples
#' sl_may(sl_any_of("-. "))  # Optional separator
sl_may <- function(inner) {
  strling_quantifier(inner, min = 0L, max = 1L)
}

#' Compile a STRling pattern to Intermediate Representation (IR)
#'
#' @param pattern A STRling AST node to compile
#' @return The compiled IR (a nested list structure)
#' @export
#' @examples
#' phone <- sl_merge(sl_start(), sl_digit(3), sl_end())
#' ir <- sl_compile(phone)
sl_compile <- function(pattern) {
  compile_ast(pattern)
}
