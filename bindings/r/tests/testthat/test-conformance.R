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
    spec_data <- jsonlite::fromJSON(file, simplifyVector = FALSE)
    
    # Iterate over test cases in the spec file
    # The spec file structure is a list of test cases? Or a single object?
    # Based on previous context, it seems to be a list of test cases or a single object with fields.
    # Let's assume it's a list of test cases if it's an array, or a single case if it's an object.
    # Actually, usually spec files are arrays of test cases.
    # But the previous runSubagent said:
    # "input_dsl", "input_ast", "expected_ir" are fields.
    # So maybe the file IS the test case? Or it contains a list?
    # "tests/spec/01_literals.json" suggests one file per category, containing multiple tests.
    # Let's check if spec_data is a list of lists (array of objects) or just a list (single object).
    
    cases <- if (is.null(names(spec_data))) spec_data else list(spec_data)
    
    for (i in seq_along(cases)) {
      case <- cases[[i]]
      
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
        # We need to ensure the structure matches exactly.
        # jsonlite::fromJSON with simplifyVector=FALSE gives lists.
        # Our compile_ast returns lists.
        # So expect_equal should work.
        expect_equal(ir, case$expected_ir, info = test_desc)
      })
    }
  }
})
