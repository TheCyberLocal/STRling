#' STRling PCRE2 Emitter - R Implementation
#'
#' Transforms STRling IR into PCRE2-compatible regex strings.
#' Iron Law: Emitters are pure functions with signature emit(ir, flags) → string.

# Special characters that need escaping in PCRE2 literals
LITERAL_SPECIAL <- "[\\]^$.|?*+(){}"

# Special characters inside character class
CLASS_SPECIAL <- "[\\]^-"

#' Default upper bound on IR nesting depth before the emitter aborts.
#' Mirrors the SSOT in the TypeScript reference.
#' @export
DEFAULT_MAX_DEPTH <- 250L

.REDOS_MESSAGE <- paste0(
  "The pattern contains overlapping alternations or nested unbounded ",
  "quantifiers (e.g., (a+)+). This can lead to catastrophic backtracking ",
  "and exponential CPU spikes. Consider using possessive quantifiers ",
  "(++ or *+) or atomic groups to guarantee execution safety."
)

# Reference-semantics emit context. R uses copy-on-modify for lists, so
# we use an environment to thread depth + warnings through the recursive
# emitter without rewriting every internal helper signature.
.new_emit_context <- function(max_depth = 0L) {
  ctx <- new.env(parent = emptyenv())
  ctx$depth <- 0L
  ctx$max_depth <- if (is.numeric(max_depth) && max_depth > 0) as.integer(max_depth) else DEFAULT_MAX_DEPTH
  ctx$in_lookbehind <- FALSE
  ctx$warnings <- list()
  ctx
}

# Implicit context — emit_pcre2() is the public, single-pattern entry
# point and creates a fresh ctx per call. Internal helpers grab it from
# .pcre2_emit_ctx via getOption() to stay backward-compatible with the
# legacy function signatures.
.get_ctx <- function() {
  ctx <- getOption(".pcre2_emit_ctx", default = NULL)
  if (is.null(ctx)) {
    ctx <- .new_emit_context()
    options(.pcre2_emit_ctx = ctx)
  }
  ctx
}

#' Check if character is in special set
contains_char <- function(str, ch) {
  grepl(ch, str, fixed = TRUE)
}

#' Escape a literal string for use outside character classes
escape_literal <- function(s) {
  chars <- strsplit(s, "")[[1]]
  result <- character(length(chars))
  for (i in seq_along(chars)) {
    ch <- chars[i]
    if (contains_char(LITERAL_SPECIAL, ch)) {
      result[i] <- paste0("\\", ch)
    } else {
      result[i] <- ch
    }
  }
  paste0(result, collapse = "")
}

#' Escape a character for use inside character classes
escape_class_char <- function(ch) {
  if (contains_char(CLASS_SPECIAL, ch)) {
    return(paste0("\\", ch))
  }
  ch
}

#' Emit PCRE2 pattern from IR
#'
#' @param ir IR representation (list from compile_ast)
#' @param flags Optional flags
#' @return Compiled PCRE2 regex string
#' @export
emit_pcre2 <- function(ir, flags = NULL) {
  res <- emit_pcre2_with_diagnostics(ir, flags)
  res$pattern
}

#' Emit PCRE2 pattern AND surface non-fatal diagnostics.
#'
#' Pass `max_depth <= 0` to use [DEFAULT_MAX_DEPTH].
#'
#' @param ir IR representation.
#' @param flags Optional flags.
#' @param max_depth Optional override for [DEFAULT_MAX_DEPTH].
#' @return [CompileResult]
#' @export
emit_pcre2_with_diagnostics <- function(ir, flags = NULL, max_depth = 0L) {
  ctx <- .new_emit_context(max_depth)
  prev <- getOption(".pcre2_emit_ctx", default = NULL)
  options(.pcre2_emit_ctx = ctx)
  on.exit(options(.pcre2_emit_ctx = prev), add = TRUE)
  pattern <- .emit_node(ir, ctx)
  CompileResult(pattern, ctx$warnings)
}

.emit_node <- function(ir, ctx) {
  ctx$depth <- ctx$depth + 1L
  on.exit(ctx$depth <- ctx$depth - 1L, add = TRUE)
  if (ctx$depth > ctx$max_depth) {
    stop(STRlingCompilationError(
      paste0(
        "Maximum AST depth exceeded (limit: ", ctx$max_depth, "). ",
        "This pattern is too deeply nested and risks host stack ",
        "exhaustion during emission. Refactor the pattern to reduce ",
        "nesting, or flatten capturing groups where possible."
      ),
      "MAX_DEPTH"
    ))
  }
  .dispatch(ir)
}

.dispatch <- function(ir) {
  ir_type <- ir$ir
  
  if (ir_type == "Lit") {
    return(emit_lit(ir))
  } else if (ir_type == "Seq") {
    return(emit_seq(ir))
  } else if (ir_type == "Alt") {
    return(emit_alt(ir))
  } else if (ir_type == "Group") {
    return(emit_group(ir))
  } else if (ir_type == "Quant") {
    return(emit_quant(ir))
  } else if (ir_type == "CharClass") {
    return(emit_char_class(ir))
  } else if (ir_type == "Anchor") {
    return(emit_anchor(ir))
  } else if (ir_type == "Dot") {
    return(".")
  } else if (ir_type == "Backref") {
    return(emit_backref(ir))
  } else if (ir_type == "Look") {
    return(emit_look(ir))
  } else if (ir_type == "Esc") {
    return(emit_esc(ir))
  } else {
    stop(paste("Unknown IR type:", ir_type))
  }
}

# --- Safety predicates --------------------------------------------------

.is_unbounded_quant <- function(q) {
  is.null(q$max) || identical(q$max, "Inf")
}

.is_variable_length_quant <- function(q) {
  if (.is_unbounded_quant(q)) return(TRUE)
  !identical(q$max, q$min)
}

.is_fixed_length_body <- function(node) {
  t <- node$ir
  if (is.null(t)) return(TRUE)
  if (t == "Quant") {
    return((!.is_variable_length_quant(node)) && .is_fixed_length_body(node$child))
  }
  if (t == "Seq") {
    return(all(vapply(node$parts, .is_fixed_length_body, logical(1))))
  }
  if (t == "Alt") {
    return(all(vapply(node$branches, .is_fixed_length_body, logical(1))))
  }
  if (t == "Group") {
    return(.is_fixed_length_body(node$body))
  }
  if (t == "Look") return(TRUE)
  TRUE
}

.has_nested_unbounded_quant <- function(child) {
  t <- child$ir
  if (is.null(t)) return(FALSE)
  if (t == "Quant") return(.is_unbounded_quant(child))
  if (t == "Group") return(.has_nested_unbounded_quant(child$body))
  if (t == "Seq") {
    return(length(child$parts) == 1L && .has_nested_unbounded_quant(child$parts[[1]]))
  }
  if (t == "Alt") {
    return(any(vapply(child$branches, .has_nested_unbounded_quant, logical(1))))
  }
  FALSE
}

.push_redos_warning <- function(ctx) {
  for (w in ctx$warnings) {
    if (identical(w$code, "REDOS_RISK")) return(invisible())
  }
  ctx$warnings <- c(ctx$warnings, list(STRlingWarning("REDOS_RISK", .REDOS_MESSAGE)))
}

emit_lit <- function(ir) {
  escape_literal(ir$value)
}

emit_seq <- function(ir) {
  ctx <- .get_ctx()
  parts <- vapply(ir$parts, function(p) .emit_node(p, ctx), character(1))
  paste0(parts, collapse = "")
}

emit_alt <- function(ir) {
  ctx <- .get_ctx()
  branches <- vapply(ir$branches, function(b) .emit_node(b, ctx), character(1))
  paste0(branches, collapse = "|")
}

emit_group <- function(ir) {
  ctx <- .get_ctx()
  body <- .emit_node(ir$body, ctx)
  capturing <- isTRUE(ir$capturing)
  name <- ir$name
  atomic <- isTRUE(ir$atomic)
  
  if (atomic) {
    return(paste0("(?>", body, ")"))
  }
  if (!is.null(name)) {
    return(paste0("(?<", name, ">", body, ")"))
  }
  if (capturing) {
    return(paste0("(", body, ")"))
  }
  paste0("(?:", body, ")")
}

emit_quant <- function(ir) {
  ctx <- .get_ctx()
  child <- ir$child
  min_val <- ir$min
  max_val <- ir$max
  mode <- if (is.null(ir$mode)) "Greedy" else ir$mode

  # ReDoS guard: only flag when the *outer* quantifier is itself
  # unbounded. A bounded outer like `(a+){0,3}` cannot produce
  # exponential backtracking on its own.
  if (.is_unbounded_quant(ir) && .has_nested_unbounded_quant(child)) {
    .push_redos_warning(ctx)
  }

  child_str <- .emit_node(child, ctx)
  
  # Check if we need parentheses
  needs_parens <- needs_quantifier_parens(child, child_str)
  if (needs_parens) {
    child_str <- paste0("(?:", child_str, ")")
  }
  
  # Build quantifier suffix
  quant_str <- ""
  if (identical(max_val, "Inf") || is.null(max_val)) {
    if (min_val == 0) {
      quant_str <- "*"
    } else if (min_val == 1) {
      quant_str <- "+"
    } else {
      quant_str <- paste0("{", min_val, ",}")
    }
  } else if (min_val == max_val) {
    if (min_val == 0) {
      return("")  # Matches nothing
    } else if (min_val == 1) {
      quant_str <- ""
    } else {
      quant_str <- paste0("{", min_val, "}")
    }
  } else if (min_val == 0 && max_val == 1) {
    quant_str <- "?"
  } else {
    quant_str <- paste0("{", min_val, ",", max_val, "}")
  }
  
  # Add mode suffix
  if (mode == "Lazy") {
    quant_str <- paste0(quant_str, "?")
  } else if (mode == "Possessive") {
    quant_str <- paste0(quant_str, "+")
  }
  
  paste0(child_str, quant_str)
}

needs_quantifier_parens <- function(child, child_str) {
  ir_type <- child$ir
  if (ir_type == "Seq") return(TRUE)
  if (ir_type == "Alt") return(TRUE)
  if (ir_type == "Lit") {
    return(nchar(child_str) > 1 && !startsWith(child_str, "\\"))
  }
  if (ir_type == "Quant") return(TRUE)
  FALSE
}

emit_char_class <- function(ir) {
  negated <- isTRUE(ir$negated)
  items <- ir$items
  
  # Single-item shorthand optimization
  if (length(items) == 1) {
    item <- items[[1]]
    item_ir <- item$ir
    
    if (item_ir == "Esc") {
      type_val <- item$type
      
      # Handle d, w, s with negation flipping
      if (type_val %in% c("d", "w", "s")) {
        if (negated) {
          return(paste0("\\", toupper(type_val)))
        }
        return(paste0("\\", type_val))
      }
      
      # Handle D, W, S
      if (type_val %in% c("D", "W", "S")) {
        if (negated) {
          return(paste0("\\", tolower(type_val)))
        }
        return(paste0("\\", type_val))
      }
      
      # Handle \p{...} and \P{...}
      if (type_val %in% c("p", "P")) {
        prop <- item$property
        if (!is.null(prop)) {
          should_negate <- negated != (type_val == "P")
          use <- if (should_negate) "P" else "p"
          return(paste0("\\", use, "{", prop, "}"))
        }
      }
    }
  }
  
  # Build bracket class
  parts <- character(0)
  has_hyphen <- FALSE
  
  for (item in items) {
    item_ir <- item$ir
    
    if (item_ir == "Char") {
      ch <- item$char
      if (ch == "-") {
        has_hyphen <- TRUE
      } else {
        parts <- c(parts, escape_class_char(ch))
      }
    } else if (item_ir == "Range") {
      from <- item$from
      to <- item$to
      parts <- c(parts, paste0(escape_class_char(from), "-", escape_class_char(to)))
    } else if (item_ir == "Esc") {
      type_val <- item$type
      prop <- item$property
      if (!is.null(prop)) {
        parts <- c(parts, paste0("\\", type_val, "{", prop, "}"))
      } else {
        parts <- c(parts, paste0("\\", type_val))
      }
    }
  }
  
  # Hyphen at start to avoid ambiguity
  inner <- if (has_hyphen) paste0("-", paste0(parts, collapse = "")) else paste0(parts, collapse = "")
  neg <- if (negated) "^" else ""
  paste0("[", neg, inner, "]")
}

emit_anchor <- function(ir) {
  at <- ir$at
  if (at == "Start") return("^")
  if (at == "End") return("$")
  if (at == "WordBoundary") return("\\b")
  if (at == "NotWordBoundary") return("\\B")
  if (at == "AbsoluteStart") return("\\A")
  if (at == "AbsoluteEnd") return("\\z")
  if (at == "EndBeforeFinalNewline") return("\\Z")
  stop(paste("Unknown anchor type:", at))
}

emit_backref <- function(ir) {
  by_index <- ir$byIndex
  by_name <- ir$byName
  
  if (!is.null(by_name)) {
    return(paste0("\\k<", by_name, ">"))
  }
  if (!is.null(by_index)) {
    return(paste0("\\", by_index))
  }
  stop("Backref must have byIndex or byName")
}

emit_look <- function(ir) {
  ctx <- .get_ctx()
  dir <- ir$dir
  neg <- isTRUE(ir$neg)

  # Variable-length lookbehind guard: PCRE2 mandates a fixed-width
  # lookbehind body. Detect the violation here so the user sees a
  # Signpost-pattern error rather than an opaque PCRE2 compile failure
  # leaking from the runtime.
  if (identical(dir, "Behind") && !.is_fixed_length_body(ir$body)) {
    stop(STRlingCompilationError(
      paste0(
        "PCRE2 does not support variable-length lookbehinds. The ",
        "lookbehind body contains a quantifier that makes its length ",
        "unpredictable. Rewrite the assertion using a fixed-length ",
        "range (e.g. `{1,8}` instead of `+`), or restructure the ",
        "pattern using a Lookahead, or extract the quantified portion ",
        "outside the assertion."
      ),
      "VLB_NOT_SUPPORTED"
    ))
  }

  was_in_lb <- ctx$in_lookbehind
  if (identical(dir, "Behind")) ctx$in_lookbehind <- TRUE
  body <- .emit_node(ir$body, ctx)
  ctx$in_lookbehind <- was_in_lb

  if (dir == "Ahead") {
    if (neg) {
      return(paste0("(?!", body, ")"))
    } else {
      return(paste0("(?=", body, ")"))
    }
  } else {
    if (neg) {
      return(paste0("(?<!", body, ")"))
    } else {
      return(paste0("(?<=", body, ")"))
    }
  }
}

emit_esc <- function(ir) {
  type_val <- ir$type
  prop <- ir$property
  
  if (!is.null(prop)) {
    return(paste0("\\", type_val, "{", prop, "}"))
  }
  paste0("\\", type_val)
}
