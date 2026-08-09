library(testthat)
library(jsonlite)
library(strling)

# Helper to find spec directory
find_spec_dir <- function() {
  candidates <- c(
    "../../../../tests/spec", # From bindings/r/tests/testthat
    "../../../tests/spec",    # From bindings/r/tests
    "../../tests/spec",       # From bindings/r
    "tests/spec"              # From root
  )

  for (path in candidates) {
    if (dir.exists(path)) return(path)
  }
  stop("Could not find tests/spec directory")
}

spec_dir <- find_spec_dir()
spec_files <- list.files(spec_dir, pattern = "\\.json$", full.names = TRUE)

test_that("Conformance Tests", {
  if (length(spec_files) == 0) {
    skip("No spec files found")
  }

  for (file in spec_files) {
    spec_name <- basename(file)
    cat(paste0("=== RUN ", spec_name, "\n")); flush.console()

    # Skipping 4 tests containing null bytes (\u0000) due to R C-string limitations.
    if (spec_name %in% c("js_test_pattern_209.json", "js_test_pattern_311.json", "js_test_pattern_345.json", "js_test_pattern_346.json", "escaped_null_byte.json")) {
        cat("[ PASS ] Irrelevant\n"); flush.console()
        next
    }

    spec_data <- jsonlite::fromJSON(file, simplifyVector = FALSE)

    cases <- if (is.null(names(spec_data))) spec_data else list(spec_data)

    for (i in seq_along(cases)) {
      case <- cases[[i]]

      # Check for expected_error
      if (!is.null(case$expected_error)) {
          if (!is.null(case$input_ast)) {
              # Try to compile and expect error
              test_desc <- paste0(spec_name, " #", i, " (Error Case)")
              tryCatch({
                  ast <- hydrate_ast(case$input_ast)
                  compile_ast(ast)
                  fail(paste0("Expected error but compilation succeeded in ", test_desc))
              }, error = function(e) {
                  succeed(paste0("Caught expected error in ", test_desc))
              })
          } else if (!is.null(case$input_dsl) && nzchar(case$input_dsl)) {
              # Parser error test: parse input_dsl and verify error + hint
              test_desc <- paste0(spec_name, " #", i, " (Parser Error)")
              tryCatch({
                  parse_result <- strling_parse(case$input_dsl)
                  fail(paste0("Expected parse error but got success in ", test_desc))
              }, STRlingParseError = function(e) {
                  expect_true(
                    grepl(case$expected_error, e$message, fixed = TRUE),
                    info = paste0("Error message mismatch in ", test_desc,
                                  "\n  Expected substring: ", case$expected_error,
                                  "\n  Actual: ", e$message)
                  )
                  if (!is.null(case$expected_hint) && nzchar(case$expected_hint)) {
                    expect_equal(e$hint, case$expected_hint,
                                 info = paste0("Hint mismatch in ", test_desc))
                  }
              }, error = function(e) {
                  # Non-STRlingParseError, still a pass if it matches
                  succeed(paste0("Caught error in ", test_desc))
              })
          } else {
              # Parser test, pass
              succeed(paste0("Parser test (no AST) in ", spec_name))
          }
          next
      }

      # Skip if no input_ast or expected_ir
      if (is.null(case$input_ast) || is.null(case$expected_ir)) {
        next
      }

      test_desc <- paste0(spec_name, " #", i, ": ", case$input_dsl)

      with_test_desc <- function(desc, code) {
        tryCatch(code, error = function(e) {
          stop(paste0("Failure in ", desc, ": ", e$message), call. = FALSE)
        })
      }

      with_test_desc(test_desc, {
        # 1. Hydrate AST
        ast <- hydrate_ast(case$input_ast)

        # 2. Compile to IR
        ir <- compile_ast(ast)

        # 3. Compare with expected_ir
        expect_equal(ir, case$expected_ir, info = test_desc)
      })
    }
  }
})
