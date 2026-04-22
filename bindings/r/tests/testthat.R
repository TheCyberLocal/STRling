library(testthat)
src <- list.files("../R", "\\.R$", full.names = TRUE)
for (f in src) source(f)
test_dir("testthat")
