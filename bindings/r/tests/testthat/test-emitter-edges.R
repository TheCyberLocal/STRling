library(testthat)
library(jsonlite)

# Emitter Edges Conformance — R bridge.
#
# Drives the global pathological-AST fixture
# `tests/conformance/inputs/emitter_edges/pathological.json` through the
# R PCRE2 emitter and asserts each safety guard fires:
#   1. Variable-Length Lookbehind Rejection — STRlingCompilationError
#   2. AST Depth Limit Exceeded             — STRlingCompilationError
#   3. ReDoS Risk Warning (`(a+)+`)         — non-fatal STRlingWarning
#
# The local `ast_to_ir()` mirrors the TypeScript bridge so the test
# targets the emitter without coupling to the parser/compiler stages.
# Keep it minimal — supporting only node types currently appearing in
# `pathological.json` — so adapter omissions cannot mask emitter bugs by
# silently dropping nodes.

find_fixture <- function() {
  dir <- normalizePath(getwd(), mustWork = FALSE)
  for (i in seq_len(12)) {
    if (file.exists(file.path(dir, "toolchain.json"))) {
      return(file.path(dir, "tests", "conformance", "inputs", "emitter_edges", "pathological.json"))
    }
    parent <- dirname(dir)
    if (identical(parent, dir)) break
    dir <- parent
  }
  stop("could not locate workspace root from ", getwd())
}

ast_to_ir <- function(node) {
  type_v <- node$type
  if (is.null(type_v)) stop("ast_to_ir: missing type field")

  if (type_v == "Literal") {
    return(list(ir = "Lit", value = as.character(node$value %||% "")))
  }
  if (type_v == "Group") {
    return(list(ir = "Group", capturing = FALSE, body = ast_to_ir(node$content)))
  }
  if (type_v == "Quantifier") {
    raw_max <- node$max
    # NULL/missing in the user-facing AST means unbounded → IR sentinel "Inf".
    max_val <- if (is.null(raw_max)) "Inf" else raw_max
    return(list(
      ir = "Quant",
      child = ast_to_ir(node$content),
      min = as.integer(node$min %||% 0L),
      max = max_val,
      mode = "Greedy"
    ))
  }
  if (type_v == "Lookbehind") {
    return(list(ir = "Look", dir = "Behind", neg = FALSE, body = ast_to_ir(node$content)))
  }
  if (type_v == "NegativeLookbehind") {
    return(list(ir = "Look", dir = "Behind", neg = TRUE,  body = ast_to_ir(node$content)))
  }
  if (type_v == "Lookahead") {
    return(list(ir = "Look", dir = "Ahead",  neg = FALSE, body = ast_to_ir(node$content)))
  }
  if (type_v == "NegativeLookahead") {
    return(list(ir = "Look", dir = "Ahead",  neg = TRUE,  body = ast_to_ir(node$content)))
  }
  stop("ast_to_ir: unsupported pathological AST node type \"", type_v,
       "\". Extend the adapter when new pathological vectors are added.")
}

`%||%` <- function(a, b) if (is.null(a)) b else a

expected_substring <- function(prefixed) {
  if (startsWith(prefixed, "STRlingCompilationError:")) {
    return(sub("^STRlingCompilationError:\\s*", "", prefixed))
  }
  if (startsWith(prefixed, "STRlingWarning")) {
    idx <- regexpr("\\]", prefixed)
    if (idx > 0) {
      return(sub("^[: ]+", "", substr(prefixed, idx + 1L, nchar(prefixed))))
    }
  }
  prefixed
}

test_that("emitter edges — pathological.json fixture", {
  path <- find_fixture()
  doc <- jsonlite::fromJSON(path, simplifyVector = FALSE)
  cases <- doc$tests
  expect_gt(length(cases), 0)

  for (tc in cases) {
    name <- tc$name %||% "<unnamed>"
    ir <- ast_to_ir(tc$ast)
    max_depth <- as.integer(tc$depth_override_for_test %||% 0L)

    if (!is.null(tc$expected_error)) {
      needle <- expected_substring(as.character(tc$expected_error))
      caught <- NULL
      tryCatch(
        emit_pcre2_with_diagnostics(ir, NULL, max_depth),
        STRlingCompilationError = function(e) { caught <<- e },
        error = function(e) { caught <<- e }
      )
      expect_true(!is.null(caught), info = paste0("[", name, "] expected error"))
      msg <- conditionMessage(caught)
      expect_true(grepl(needle, msg, fixed = TRUE),
                  info = paste0("[", name, "] expected substring \"", needle, "\" in \"", msg, "\""))
    } else if (!is.null(tc$expected_warning)) {
      needle <- expected_substring(as.character(tc$expected_warning))
      result <- emit_pcre2_with_diagnostics(ir, NULL, max_depth)
      expect_gt(nchar(result$pattern), 0,
                label = paste0("[", name, "] expected non-empty pattern when only a warning fires"))
      hit <- FALSE
      for (w in result$warnings) {
        if (identical(w$code, "REDOS_RISK") && grepl(needle, w$message, fixed = TRUE)) {
          hit <- TRUE; break
        }
      }
      expect_true(hit, info = paste0("[", name, "] missing REDOS_RISK warning containing \"", needle, "\""))
    } else {
      fail(paste0("[", name, "] declares neither expected_error nor expected_warning"))
    }
  }
})

test_that("emitter edges — non-pathological emits no warnings", {
  result <- emit_pcre2_with_diagnostics(list(ir = "Lit", value = "abc"))
  expect_identical(result$pattern, "abc")
  expect_equal(length(result$warnings), 0L)
})

test_that("emitter edges — depth cap does not fire under limit", {
  ir <- list(ir = "Group", capturing = FALSE,
             body = list(ir = "Group", capturing = FALSE,
                         body = list(ir = "Lit", value = "ok")))
  result <- emit_pcre2_with_diagnostics(ir, NULL, 5L)
  expect_equal(length(result$warnings), 0L)
  expect_true(grepl("ok", result$pattern, fixed = TRUE))
})
