#' STRling Parser - Recursive Descent Parser for R
#'
#' Transforms STRling DSL patterns into AST nodes.
#' Mirrors the TypeScript reference implementation.

#' @export
STRlingParseError <- function(message, position, source, hint = NULL) {
  structure(
    list(message = message, position = position, source = source, hint = hint),
    class = c("STRlingParseError", "error", "condition")
  )
}

#' @export
print.STRlingParseError <- function(x, ...) {
  cat(sprintf("STRlingParseError: %s at position %d\n", x$message, x$position))
}

#' Flags container
#' @export
strling_flags <- function(ignoreCase = FALSE, multiline = FALSE, dotAll = FALSE,
                          unicode = FALSE, extended = FALSE) {
  structure(
    list(
      ignoreCase = ignoreCase,
      multiline = multiline,
      dotAll = dotAll,
      unicode = unicode,
      extended = extended
    ),
    class = "strling_flags"
  )
}

#' Create flags from letter string
#' @export
flags_from_letters <- function(letters) {
  f <- strling_flags()
  letters <- tolower(gsub("[,\\[\\]\\s]", "", letters))
  for (ch in strsplit(letters, "")[[1]]) {
    if (ch == "i") f$ignoreCase <- TRUE
    else if (ch == "m") f$multiline <- TRUE
    else if (ch == "s") f$dotAll <- TRUE
    else if (ch == "u") f$unicode <- TRUE
    else if (ch == "x") f$extended <- TRUE
  }
  f
}

# Control escape mappings
CONTROL_ESCAPES <- list(
  n = "\n",
  r = "\r",
  t = "\t",
  f = "\f",
  v = "\v"
)

# Cursor class for tracking position
Cursor <- function(text, extended_mode = FALSE) {
  env <- new.env(parent = emptyenv())
  env$text <- text
  env$i <- 1L  # R is 1-indexed
  env$extended_mode <- extended_mode
  env$in_class <- 0L
  env$len <- nchar(text)

  env$eof <- function() env$i > env$len

  env$peek <- function(offset = 0L) {
    j <- env$i + offset
    if (j > env$len) return("")
    substr(env$text, j, j)
  }

  env$take <- function() {
    if (env$eof()) return("")
    ch <- substr(env$text, env$i, env$i)
    env$i <- env$i + 1L
    ch
  }

  env$match <- function(s) {
    slen <- nchar(s)
    if (env$i + slen - 1L > env$len) return(FALSE)
    if (substr(env$text, env$i, env$i + slen - 1L) == s) {
      env$i <- env$i + slen
      return(TRUE)
    }
    FALSE
  }

  env$skip_ws_and_comments <- function() {
    if (!env$extended_mode || env$in_class > 0L) return()
    while (!env$eof()) {
      ch <- env$peek()
      if (ch %in% c(" ", "\t", "\r", "\n")) {
        env$i <- env$i + 1L
        next
      }
      if (ch == "#") {
        while (!env$eof() && !(env$peek() %in% c("\r", "\n"))) {
          env$i <- env$i + 1L
        }
        next
      }
      break
    }
  }

  env
}

# Parser class
Parser <- function(text) {
  env <- new.env(parent = emptyenv())
  env$original <- text

  # Parse directives
  result <- parse_directives(text)
  env$flags <- result$flags
  env$src <- result$pattern
  env$cur <- Cursor(env$src, env$flags$extended)
  env$cap_count <- 0L
  env$cap_names <- character(0)

  env
}

parse_directives <- function(text) {
  flags <- strling_flags()
  pattern <- text

  # Match %flags directive
  m <- regexpr("^\\s*%flags\\s*([imsux,\\[\\]\\s]*)", text, perl = TRUE)
  if (m > 0) {
    flag_str <- regmatches(text, m)
    flag_str <- sub("^\\s*%flags\\s*", "", flag_str)
    flag_str <- tolower(gsub("[,\\[\\]\\s]", "", flag_str))
    flags <- flags_from_letters(flag_str)

    # Remove directive lines
    lines <- strsplit(text, "\n")[[1]]
    pattern_lines <- character(0)
    in_pattern <- FALSE
    for (line in lines) {
      trimmed <- trimws(line)
      if (!in_pattern && (grepl("^%flags", trimmed) || trimmed == "" || grepl("^#", trimmed))) {
        next
      }
      in_pattern <- TRUE
      pattern_lines <- c(pattern_lines, line)
    }
    pattern <- paste(pattern_lines, collapse = "\n")
  }

  list(flags = flags, pattern = pattern)
}

#' Parse a STRling DSL string
#' @param src Source string to parse
#' @return List with flags and AST node
#' @export
strling_parse <- function(src) {
  p <- Parser(src)
  parse_main(p)
}

parse_main <- function(p) {
  node <- parse_alt(p)
  p$cur$skip_ws_and_comments()

  if (!p$cur$eof()) {
    ch <- p$cur$peek()
    if (ch == ")") {
      stop(STRlingParseError("Unmatched ')'", p$cur$i, p$src))
    }
    stop(STRlingParseError("Unexpected trailing input", p$cur$i, p$src))
  }

  list(flags = p$flags, node = node)
}

parse_alt <- function(p) {
  p$cur$skip_ws_and_comments()

  if (p$cur$peek() == "|") {
    stop(STRlingParseError("Alternation lacks left-hand side", p$cur$i, p$src))
  }

  branches <- list(parse_seq(p))
  p$cur$skip_ws_and_comments()

  while (p$cur$peek() == "|") {
    pipe_pos <- p$cur$i
    p$cur$take()
    p$cur$skip_ws_and_comments()

    if (p$cur$eof() || p$cur$peek() == "|") {
      stop(STRlingParseError("Alternation lacks right-hand side", pipe_pos, p$src))
    }

    branches <- c(branches, list(parse_seq(p)))
    p$cur$skip_ws_and_comments()
  }

  if (length(branches) == 1L) return(branches[[1]])
  strling_alternation(branches)
}

parse_seq <- function(p) {
  parts <- list()

  while (TRUE) {
    p$cur$skip_ws_and_comments()
    ch <- p$cur$peek()

    if (ch %in% c("*", "+", "?", "{") && length(parts) == 0L) {
      stop(STRlingParseError(sprintf("Invalid quantifier '%s'", ch), p$cur$i, p$src))
    }

    if (ch == "" || ch %in% c("|", ")")) break

    atom <- parse_atom(p)
    atom <- parse_quant_if_any(p, atom)
    parts <- c(parts, list(atom))
  }

  if (length(parts) == 1L) return(parts[[1]])
  strling_sequence(parts)
}

parse_atom <- function(p) {
  p$cur$skip_ws_and_comments()
  ch <- p$cur$peek()

  if (ch == ".") {
    p$cur$take()
    return(strling_dot())
  }
  if (ch == "^") {
    p$cur$take()
    return(strling_anchor("Start"))
  }
  if (ch == "$") {
    p$cur$take()
    return(strling_anchor("End"))
  }
  if (ch == "(") {
    return(parse_group_or_look(p))
  }
  if (ch == "[") {
    return(parse_char_class(p))
  }
  if (ch == "\\") {
    return(parse_escape_atom(p))
  }
  if (ch == ")") {
    stop(STRlingParseError("Unmatched ')'", p$cur$i, p$src))
  }

  strling_literal(p$cur$take())
}

parse_quant_if_any <- function(p, child) {
  ch <- p$cur$peek()
  min <- NULL
  max <- NULL
  greedy <- TRUE
  lazy <- FALSE
  possessive <- FALSE

  if (ch == "*") {
    min <- 0L
    max <- NULL
    p$cur$take()
  } else if (ch == "+") {
    min <- 1L
    max <- NULL
    p$cur$take()
  } else if (ch == "?") {
    min <- 0L
    max <- 1L
    p$cur$take()
  } else if (ch == "{") {
    save <- p$cur$i
    p$cur$take()

    m <- read_int_optional(p)
    if (is.null(m)) {
      p$cur$i <- save
      return(child)
    }

    min <- m
    max <- m

    if (p$cur$peek() == ",") {
      p$cur$take()
      max <- read_int_optional(p)
    }

    if (p$cur$peek() != "}") {
      stop(STRlingParseError("Incomplete quantifier", p$cur$i, p$src))
    }
    p$cur$take()
  } else {
    return(child)
  }

  if (inherits(child, "strling_anchor")) {
    stop(STRlingParseError("Cannot quantify anchor", p$cur$i, p$src))
  }

  nxt <- p$cur$peek()
  if (nxt == "?") {
    greedy <- FALSE
    lazy <- TRUE
    p$cur$take()
  } else if (nxt == "+") {
    greedy <- FALSE
    possessive <- TRUE
    p$cur$take()
  }

  mode <- if (lazy) "Lazy" else if (possessive) "Possessive" else "Greedy"
  strling_quantifier(child, min, max, mode)
}

read_int_optional <- function(p) {
  s <- ""
  while (grepl("^[0-9]$", p$cur$peek())) {
    s <- paste0(s, p$cur$take())
  }
  if (s == "") return(NULL)
  as.integer(s)
}

parse_group_or_look <- function(p) {
  p$cur$take()  # consume '('

  if (p$cur$match("?:")) {
    body <- parse_alt(p)
    if (!p$cur$match(")")) {
      stop(STRlingParseError("Unterminated group", p$cur$i, p$src))
    }
    return(strling_group(body, capturing = FALSE))
  }

  if (p$cur$match("?<=")) {
    body <- parse_alt(p)
    if (!p$cur$match(")")) {
      stop(STRlingParseError("Unterminated lookbehind", p$cur$i, p$src))
    }
    return(strling_lookaround(body, kind = "Behind", negated = FALSE))
  }

  if (p$cur$match("?<!")) {
    body <- parse_alt(p)
    if (!p$cur$match(")")) {
      stop(STRlingParseError("Unterminated lookbehind", p$cur$i, p$src))
    }
    return(strling_lookaround(body, kind = "Behind", negated = TRUE))
  }

  if (p$cur$match("?<")) {
    name <- ""
    while (p$cur$peek() != ">" && p$cur$peek() != "") {
      name <- paste0(name, p$cur$take())
    }
    if (!p$cur$match(">")) {
      stop(STRlingParseError("Unterminated group name", p$cur$i, p$src))
    }
    if (name %in% p$cap_names) {
      stop(STRlingParseError(sprintf("Duplicate group name <%s>", name), p$cur$i, p$src))
    }
    p$cap_count <- p$cap_count + 1L
    p$cap_names <- c(p$cap_names, name)

    body <- parse_alt(p)
    if (!p$cur$match(")")) {
      stop(STRlingParseError("Unterminated group", p$cur$i, p$src))
    }
    return(strling_group(body, capturing = TRUE, name = name))
  }

  if (p$cur$match("?>")) {
    body <- parse_alt(p)
    if (!p$cur$match(")")) {
      stop(STRlingParseError("Unterminated atomic group", p$cur$i, p$src))
    }
    return(strling_group(body, capturing = FALSE, atomic = TRUE))
  }

  if (p$cur$match("?=")) {
    body <- parse_alt(p)
    if (!p$cur$match(")")) {
      stop(STRlingParseError("Unterminated lookahead", p$cur$i, p$src))
    }
    return(strling_lookaround(body, kind = "Ahead", negated = FALSE))
  }

  if (p$cur$match("?!")) {
    body <- parse_alt(p)
    if (!p$cur$match(")")) {
      stop(STRlingParseError("Unterminated lookahead", p$cur$i, p$src))
    }
    return(strling_lookaround(body, kind = "Ahead", negated = TRUE))
  }

  p$cap_count <- p$cap_count + 1L
  body <- parse_alt(p)
  if (!p$cur$match(")")) {
    stop(STRlingParseError("Unterminated group", p$cur$i, p$src))
  }
  strling_group(body, capturing = TRUE)
}

parse_char_class <- function(p) {
  p$cur$take()  # consume '['
  p$cur$in_class <- p$cur$in_class + 1L

  neg <- FALSE
  if (p$cur$peek() == "^") {
    neg <- TRUE
    p$cur$take()
  }

  members <- list()

  while (!p$cur$eof() && p$cur$peek() != "]") {
    if (p$cur$peek() == "\\") {
      members <- c(members, list(parse_class_escape(p)))
    } else {
      ch <- p$cur$take()

      if (p$cur$peek() == "-" && p$cur$peek(1L) != "]") {
        p$cur$take()  # consume '-'
        end_ch <- p$cur$take()
        members <- c(members, list(strling_class_range(ch, end_ch)))
      } else {
        members <- c(members, list(strling_class_literal(ch)))
      }
    }
  }

  if (p$cur$eof()) {
    stop(STRlingParseError("Unterminated character class", p$cur$i, p$src))
  }

  p$cur$take()  # consume ']'
  p$cur$in_class <- p$cur$in_class - 1L

  strling_character_class(members, negated = neg)
}

parse_class_escape <- function(p) {
  start_pos <- p$cur$i
  p$cur$take()  # consume '\'

  nxt <- p$cur$peek()

  if (nxt %in% c("d", "D", "w", "W", "s", "S")) {
    ch <- p$cur$take()
    type_code <- switch(ch,
      "d" = "d", "D" = "D",
      "w" = "w", "W" = "W",
      "s" = "s", "S" = "S"
    )
    return(strling_class_escape(type_code))
  }

  if (nxt %in% c("p", "P")) {
    tp <- p$cur$take()
    if (!p$cur$match("{")) {
      stop(STRlingParseError("Expected '{' after \\p/\\P", start_pos, p$src))
    }
    prop <- ""
    while (p$cur$peek() != "}" && p$cur$peek() != "") {
      prop <- paste0(prop, p$cur$take())
    }
    if (!p$cur$match("}")) {
      stop(STRlingParseError("Unterminated \\p{...}", start_pos, p$src))
    }
    type_code <- if (tp == "P") "P" else "p"
    return(strling_class_escape(type_code, prop))
  }

  if (!is.null(CONTROL_ESCAPES[[nxt]])) {
    p$cur$take()
    return(strling_class_literal(CONTROL_ESCAPES[[nxt]]))
  }

  if (nxt == "b") {
    p$cur$take()
    return(strling_class_literal("\b"))
  }

  if (nxt == "0") {
    p$cur$take()
    return(strling_class_literal("\\0"))
  }

  strling_class_literal(p$cur$take())
}

parse_escape_atom <- function(p) {
  start_pos <- p$cur$i
  p$cur$take()  # consume '\'

  nxt <- p$cur$peek()

  # Backreference
  if (grepl("^[1-9]$", nxt)) {
    num <- 0L
    while (grepl("^[0-9]$", p$cur$peek())) {
      num <- num * 10L + as.integer(p$cur$take())
      if (num > p$cap_count) {
        stop(STRlingParseError(sprintf("Backreference to undefined group \\%d", num), start_pos, p$src))
      }
    }
    return(strling_backreference(index = num))
  }

  if (nxt == "b") {
    p$cur$take()
    return(strling_anchor("WordBoundary"))
  }
  if (nxt == "B") {
    p$cur$take()
    return(strling_anchor("NotWordBoundary"))
  }
  if (nxt == "A") {
    p$cur$take()
    return(strling_anchor("AbsoluteStart"))
  }
  if (nxt == "Z") {
    p$cur$take()
    return(strling_anchor("EndBeforeFinalNewline"))
  }

  if (nxt == "k") {
    p$cur$take()
    if (!p$cur$match("<")) {
      stop(STRlingParseError("Expected '<' after \\k", start_pos, p$src))
    }
    name <- ""
    while (p$cur$peek() != ">" && p$cur$peek() != "") {
      name <- paste0(name, p$cur$take())
    }
    if (!p$cur$match(">")) {
      stop(STRlingParseError("Unterminated named backref", start_pos, p$src))
    }
    if (!(name %in% p$cap_names)) {
      stop(STRlingParseError(sprintf("Backreference to undefined group <%s>", name), start_pos, p$src))
    }
    return(strling_backreference(name = name))
  }

  if (nxt %in% c("d", "D", "w", "W", "s", "S")) {
    ch <- p$cur$take()
    type_code <- switch(ch,
      "d" = "d", "D" = "D",
      "w" = "w", "W" = "W",
      "s" = "s", "S" = "S"
    )
    return(strling_character_class(list(strling_class_escape(type_code)), negated = FALSE))
  }

  if (nxt %in% c("p", "P")) {
    tp <- p$cur$take()
    if (!p$cur$match("{")) {
      stop(STRlingParseError("Expected '{' after \\p/\\P", start_pos, p$src))
    }
    prop <- ""
    while (p$cur$peek() != "}" && p$cur$peek() != "") {
      prop <- paste0(prop, p$cur$take())
    }
    if (!p$cur$match("}")) {
      stop(STRlingParseError("Unterminated \\p{...}", start_pos, p$src))
    }
    type_code <- if (tp == "P") "P" else "p"
    return(strling_character_class(list(strling_class_escape(type_code, prop)), negated = FALSE))
  }

  if (!is.null(CONTROL_ESCAPES[[nxt]])) {
    p$cur$take()
    return(strling_literal(CONTROL_ESCAPES[[nxt]]))
  }

  if (nxt == "x") {
    p$cur$take()
    return(strling_literal(parse_hex_escape(p, start_pos)))
  }

  if (nxt %in% c("u", "U")) {
    return(strling_literal(parse_unicode_escape(p, start_pos)))
  }

  if (nxt == "0") {
    p$cur$take()
    return(strling_literal("\\0"))
  }

  strling_literal(p$cur$take())
}

parse_hex_escape <- function(p, start_pos) {
  if (p$cur$match("{")) {
    hex <- ""
    while (grepl("^[0-9A-Fa-f]$", p$cur$peek())) {
      hex <- paste0(hex, p$cur$take())
    }
    if (!p$cur$match("}")) {
      stop(STRlingParseError("Unterminated \\x{...}", start_pos, p$src))
    }
    code <- strtoi(if (hex == "") "0" else hex, base = 16L)
    return(intToUtf8(code))
  }

  h1 <- p$cur$take()
  h2 <- p$cur$take()
  if (!grepl("^[0-9A-Fa-f]$", h1) || !grepl("^[0-9A-Fa-f]$", h2)) {
    stop(STRlingParseError("Invalid \\xHH escape", start_pos, p$src))
  }
  intToUtf8(strtoi(paste0(h1, h2), base = 16L))
}

parse_unicode_escape <- function(p, start_pos) {
  tp <- p$cur$take()

  if (tp == "u" && p$cur$match("{")) {
    hex <- ""
    while (grepl("^[0-9A-Fa-f]$", p$cur$peek())) {
      hex <- paste0(hex, p$cur$take())
    }
    if (!p$cur$match("}")) {
      stop(STRlingParseError("Unterminated \\u{...}", start_pos, p$src))
    }
    code <- strtoi(if (hex == "") "0" else hex, base = 16L)
    return(intToUtf8(code))
  }

  if (tp == "u") {
    hex <- ""
    for (i in 1:4) {
      hex <- paste0(hex, p$cur$take())
    }
    if (!grepl("^[0-9A-Fa-f]{4}$", hex)) {
      stop(STRlingParseError("Invalid \\uHHHH escape", start_pos, p$src))
    }
    return(intToUtf8(strtoi(hex, base = 16L)))
  }

  if (tp == "U") {
    hex <- ""
    for (i in 1:8) {
      hex <- paste0(hex, p$cur$take())
    }
    if (!grepl("^[0-9A-Fa-f]{8}$", hex)) {
      stop(STRlingParseError("Invalid \\UHHHHHHHH escape", start_pos, p$src))
    }
    return(intToUtf8(strtoi(hex, base = 16L)))
  }

  stop(STRlingParseError("Invalid unicode escape", start_pos, p$src))
}
