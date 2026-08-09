
Sys.setenv(LC_ALL='C')
cat("START\n")
tryCatch({
  # Source the package files directly instead of using devtools::load_all()
  # This avoids the heavy devtools dependency in CI
  for (f in list.files("R", pattern = "\\.R$", full.names = TRUE)) {
    source(f)
  }
  cat("LOADED\n")

  res <- testthat::test_dir('tests/testthat', reporter=c('summary'), stop_on_failure=FALSE)
  df <- as.data.frame(res)

  cat(sprintf('[ FAIL %d | WARN %d | SKIP %d | PASS %d ]\n',
              sum(df$failed), sum(df$warning), sum(df$skipped), sum(df$passed)))

  # Exit with non-zero if any tests failed
  if (sum(df$failed) > 0) {
    quit(status = 1)
  }
}, error = function(e) {
  cat("ERROR: ", e$message, "\n")
  quit(status = 1)
})
