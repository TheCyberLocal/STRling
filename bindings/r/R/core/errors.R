# STRling Error Classes - Rich Error Handling for Instructional Diagnostics
#
# This module provides a helper to create a STRling-style parse error condition
# with position tracking, formatted messages, and optional hints. The
# implementation mirrors the Python `STRlingParseError` but uses R's condition
# system (simpleError + classes) for idiomatic error handling.

#' Format a STRling parse error message with context and caret
#'
#' @param message character short description of error
#' @param pos integer 0-based character position where error occurred
#' @param text character full input text (default: "")
#' @param hint character optional hint for users
#' @return None; throws a condition of class `STRlingParseError`
#' @export
strling_parse_error <- function(message, pos, text = "", hint = NULL) {
  # Build formatted message similar to Python implementation
  if (nzchar(text)) {
    lines <- strsplit(text, "\n", fixed = TRUE)[[1]]
    current_pos <- 0L
    line_num <- 1L
    line_text <- ""
    col <- as.integer(pos)

    for (i in seq_along(lines)) {
      line <- lines[[i]]
      line_len <- nchar(line, type = "chars") + 1L
      if (current_pos + line_len > pos) {
        line_num <- i
        line_text <- line
        col <- as.integer(pos - current_pos)
        break
      }
      current_pos <- current_pos + line_len
    }
    if (line_text == "") {
      if (length(lines) > 0) {
        line_num <- length(lines)
        line_text <- lines[[length(lines)]]
        col <- nchar(line_text, type = "chars")
      } else {
        line_text <- text
        col <- as.integer(pos)
      }
    }

    parts <- c(sprintf("STRling Parse Error: %s", message), "",
               sprintf("> %d | %s", line_num, line_text),
               sprintf(">   | %s^", paste0(rep(" ", col), collapse = "")))
    if (!is.null(hint)) {
      parts <- c(parts, "", sprintf("Hint: %s", hint))
    }
    full_msg <- paste(parts, collapse = "\n")
  } else {
    full_msg <- sprintf("%s at position %d", message, pos)
  }

  # Create a simpleError and attach fields for programmatic use
  e <- simpleError(full_msg)
  class(e) <- c("STRlingParseError", class(e))
  e$pos <- pos
  e$text <- text
  e$hint <- hint

  stop(e)
}

#' Convert a STRlingParseError to an LSP-like diagnostic (list)
#'
#' @param message character error message
#' @param pos integer 0-based char position
#' @param text character full input text
#' @param hint character optional
#' @return list representing an LSP diagnostic
#' @export
strling_error_to_lsp <- function(message, pos, text = "", hint = NULL) {
  lines <- if (nzchar(text)) strsplit(text, "\n", fixed = TRUE)[[1]] else character(0)
  current_pos <- 0L
  line_num <- 0L
  col <- as.integer(pos)

  if (length(lines) > 0) {
    for (i in seq_along(lines)) {
      line_len <- nchar(lines[[i]], type = "chars") + 1L
      if (current_pos + line_len > pos) {
        line_num <- i - 1L  # zero-index for LSP
        col <- as.integer(pos - current_pos)
        break
      }
      current_pos <- current_pos + line_len
    }
    if (current_pos + 1L <= pos) {
      line_num <- length(lines) - 1L
      col <- nchar(lines[[length(lines)]], type = "chars")
    }
  } else {
    line_num <- 0L
    col <- as.integer(pos)
  }

  diagnostic_message <- message
  if (!is.null(hint)) diagnostic_message <- paste0(diagnostic_message, "\n\nHint: ", hint)

  # Create error code from message (normalize to snake_case)
  error_code <- tolower(message)
  error_code <- gsub("[ '\\"()\[\]{}\\/\\\\]", "_", error_code)
  error_code <- gsub("_+", "_", error_code)
  error_code <- gsub("^_+|_+$", "", error_code)

  list(
    range = list(
      start = list(line = line_num, character = col),
      end = list(line = line_num, character = col + 1L)
    ),
    severity = 1L,
    message = diagnostic_message,
    source = "STRling",
    code = error_code
  )
}
