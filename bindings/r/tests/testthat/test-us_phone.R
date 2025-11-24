library(testthat)

test_that("US Phone Number Pattern with Simply API", {
  # Build: ^(\d{3})[-. ]?(\d{3})[-. ]?(\d{4})$
  # This is the acceptance criterion from the issue
  phone <- sl_merge(
    sl_start(),
    sl_capture(sl_digit(3)),
    sl_may(sl_any_of("-. ")),
    sl_capture(sl_digit(3)),
    sl_may(sl_any_of("-. ")),
    sl_capture(sl_digit(4)),
    sl_end()
  )

  # Compile to IR
  ir <- sl_compile(phone)

  # Verify the IR structure
  expect_true(is.list(ir))
  expect_equal(ir$ir, "Seq")

  # Verify we have the expected parts
  parts <- ir$parts
  expect_true(length(parts) >= 7)  # start, 3 captures, 2 optionals, end

  # Check for start anchor
  expect_true(any(sapply(parts, function(p) {
    is.list(p) && p$ir == "Anchor" && p$at == "Start"
  })))

  # Check for end anchor
  expect_true(any(sapply(parts, function(p) {
    is.list(p) && p$ir == "Anchor" && p$at == "End"
  })))

  # Check for capturing groups with digit quantifiers
  capturing_groups <- Filter(function(p) {
    is.list(p) && p$ir == "Group" && isTRUE(p$capturing)
  }, parts)
  
  expect_true(length(capturing_groups) >= 3)

  # Check that each capturing group contains a quantifier with correct digit count
  # Pattern has 3 groups: digit(3), digit(3), digit(4)
  digit_counts <- sapply(capturing_groups, function(group) {
    body <- group$body
    expect_true(is.list(body))
    expect_equal(body$ir, "Quant")
    body$min
  })
  
  expect_equal(sort(digit_counts), c(3, 3, 4))

  # Check for optional character classes
  optionals <- Filter(function(p) {
    is.list(p) && p$ir == "Quant" && p$min == 0 && p$max == 1
  }, parts)
  
  expect_true(length(optionals) >= 2)  # Two optional separators
})

test_that("Simply API individual functions work correctly", {
  # Test sl_start
  start <- sl_start()
  expect_equal(start$type, "Anchor")
  expect_equal(start$at, "Start")

  # Test sl_end
  end <- sl_end()
  expect_equal(end$type, "Anchor")
  expect_equal(end$at, "End")

  # Test sl_digit with default
  digit1 <- sl_digit()
  expect_equal(digit1$type, "CharacterClass")
  expect_equal(digit1$items[[1]]$type, "ClassEscape")
  expect_equal(digit1$items[[1]]$type_, "d")

  # Test sl_digit with count
  digit3 <- sl_digit(3)
  expect_equal(digit3$type, "Quantifier")
  expect_equal(digit3$min, 3L)
  expect_equal(digit3$max, 3L)

  # Test sl_any_of
  chars <- sl_any_of("-. ")
  expect_equal(chars$type, "CharacterClass")
  expect_equal(length(chars$items), 3)
  expect_equal(chars$items[[1]]$char, "-")
  expect_equal(chars$items[[2]]$char, ".")
  expect_equal(chars$items[[3]]$char, " ")

  # Test sl_capture
  captured <- sl_capture(sl_digit(2))
  expect_equal(captured$type, "Group")
  expect_true(captured$capturing)

  # Test sl_may
  optional <- sl_may(sl_digit(1))
  expect_equal(optional$type, "Quantifier")
  expect_equal(optional$min, 0L)
  expect_equal(optional$max, 1L)

  # Test sl_merge
  merged <- sl_merge(sl_start(), sl_digit(3), sl_end())
  expect_equal(merged$type, "Sequence")
  expect_equal(length(merged$parts), 3)
})
