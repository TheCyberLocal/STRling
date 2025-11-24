library(testthat)

# Placeholder test file for STRling R binding.
# Functional tests will be added in Task 2.

test_that("placeholder", {
  expect_true(TRUE)
})

test_that("phone AST compiles to IR sequence", {
  phone <- strling_sequence(parts = list(
    strling_anchor("Start"),
    strling_group(
      strling_quantifier(strling_character_class(list(strling_class_escape("d"))), min = 3L, max = 3L),
      capturing = TRUE
    ),
    strling_quantifier(strling_character_class(list(strling_class_literal("-"), strling_class_literal("."), strling_class_literal(" "))), min = 0L, max = 1L),
    strling_group(strling_quantifier(strling_character_class(list(strling_class_escape("d"))), min = 3L, max = 3L), capturing = TRUE),
    strling_quantifier(strling_character_class(list(strling_class_literal("-"), strling_class_literal("."), strling_class_literal(" "))), min = 0L, max = 1L),
    strling_group(strling_quantifier(strling_character_class(list(strling_class_escape("d"))), min = 4L, max = 4L), capturing = TRUE),
    strling_anchor("End")
  ))

  ir <- compile_ast(phone)

  # top level should be a sequence (IR Seq)
  expect_true(is.list(ir))
  expect_equal(ir$ir, "Seq")

  # ensure it contains group / quantifier parts
  parts <- ir$parts
  expect_true(length(parts) >= 3)
  # at least one part should be a quantifier for digits (min >= 3)
  has_digits_quant <- any(sapply(parts, function(p) {
    is.list(p) && p$ir == "Quant" && !is.null(p$min) && p$min >= 3
  }))
  expect_true(has_digits_quant)
})
