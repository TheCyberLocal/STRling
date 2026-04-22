library(testthat)
library(jsonlite)

find_spec <- function() {
  dir <- "."
  for (i in 1:10) {
    p <- file.path(dir, "spec/stdlib/essential_5.json")
    if (file.exists(p)) return(p)
    dir <- file.path(dir, "..")
  }
  stop("essential_5.json not found")
}

spec <- jsonlite::fromJSON(find_spec(), simplifyVector = FALSE)

compile_re <- function(node) {
  body <- emit_pcre2(compile_ast(node))
  paste0("^(?:", body, ")$")
}

assert_all_match <- function(node, samples) {
  re <- compile_re(node)
  for (s in samples) {
    expect_true(grepl(re, s, perl = TRUE), info = paste("expected match:", s))
  }
}

assert_none_match <- function(node, samples) {
  re <- compile_re(node)
  for (s in samples) {
    expect_false(grepl(re, s, perl = TRUE), info = paste("unexpected match:", s))
  }
}

fx <- function(p, k) spec$patterns[[p]]$fixtures[[k]]

test_that("email matches RFC 5322 fixtures",   { assert_all_match(sl_email(),  fx("email", "valid")) })
test_that("email rejects malformed inputs",    { assert_none_match(sl_email(), fx("email", "invalid")) })
test_that("url matches RFC 3986 fixtures",     { assert_all_match(sl_url(),    fx("url", "valid")) })
test_that("url rejects malformed inputs",      { assert_none_match(sl_url(),   fx("url", "invalid")) })
test_that("uuid default valid",                { assert_all_match(sl_uuid(),   fx("uuid", "valid_default")) })
test_that("uuid default invalid",              { assert_none_match(sl_uuid(),  fx("uuid", "invalid_default")) })
test_that("uuid v4 valid",                     { assert_all_match(sl_uuid(4L), fx("uuid", "valid_v4")) })
test_that("uuid v4 invalid",                   { assert_none_match(sl_uuid(4L), fx("uuid", "invalid_v4")) })
test_that("ip v4 valid",                       { assert_all_match(sl_ip(4L),   fx("ip", "valid_v4")) })
test_that("ip v4 invalid",                     { assert_none_match(sl_ip(4L),  fx("ip", "invalid_v4")) })
test_that("ip v6 valid",                       { assert_all_match(sl_ip(6L),   fx("ip", "valid_v6")) })
test_that("ip v6 invalid",                     { assert_none_match(sl_ip(6L),  fx("ip", "invalid_v6")) })
test_that("ip any matches v4 fixtures",        { assert_all_match(sl_ip(),     fx("ip", "valid_v4")) })
test_that("ip any matches v6 fixtures",        { assert_all_match(sl_ip(),     fx("ip", "valid_v6")) })
test_that("dateTime valid",                    { assert_all_match(sl_date_time(), fx("dateTime", "valid")) })
test_that("dateTime invalid",                  { assert_none_match(sl_date_time(), fx("dateTime", "invalid")) })
