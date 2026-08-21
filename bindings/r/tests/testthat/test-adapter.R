test_that("canonical requests and lexical helpers are projected", {
  request <- strling_source_compile_request('literal "hello"')
  expect_identical(request$contract_version, "1.0.0")
  expect_identical(request$input$document$frontend$id, "semantic_strling")
  expect_identical(sl_email("root")$arguments$helper_id, "stdlib.email")
  expect_true("version" %in% names(sl_uuid("root")$arguments$parameters))
})

test_that("stdlib helpers consume the canonical Essential fixture", {
  fixture <- jsonlite::fromJSON(
    file.path("..", "..", "..", "..", "spec", "stdlib", "essential_5.json"),
    simplifyVector = FALSE
  )
  steps <- list(
    dateTime = sl_date_time("date-time"),
    email = sl_email("email"),
    ip = sl_ip("ip"),
    url = sl_url("url"),
    uuid = sl_uuid("uuid")
  )
  expect_identical(sort(names(steps)), sort(names(fixture$patterns)))
  for (name in names(steps)) {
    helper_id <- if (name == "dateTime") "date_time" else name
    expect_identical(steps[[name]]$arguments$helper_id, paste0("stdlib.", helper_id))
  }
})

test_that("relative paths fail closed", {
  expect_error(strling_load_native("libstrling_interop.so"), "absolute")
})

test_that("the certification probe executes when supplied", {
  path <- Sys.getenv("STRLING_DYNAMIC_PROBE", unset = NA_character_)
  skip_if(is.na(path), "certification probe unavailable")
  client <- strling_load_native(path)
  expected <- list(unicode = "雪")
  results <- list(
    describe = strling_describe(client),
    compile = strling_compile(client, strling_source_compile_request('literal "雪"')),
    target_profile.inspect = strling_inspect_target_profile(client, list(contract_version = "1.0.0")),
    simply.compile = strling_simply_compile(client, strling_simply_builder_request(list(sl_email("root")), "root"))
  )
  for (result in results) expect_identical(result, expected)
  evidence_dir <- Sys.getenv("STRLING_DYNAMIC_EVIDENCE_DIR", unset = NA_character_)
  if (!is.na(evidence_dir)) {
    writeLines(
      jsonlite::toJSON(results, auto_unbox = TRUE, null = "null", digits = NA, pretty = FALSE),
      file.path(evidence_dir, "r.json"),
      useBytes = TRUE
    )
  }
  strling_close(client)
  expect_true(strling_is_closed(client))
  strling_close(client)
  expect_error(strling_describe(client), "closed")
})

test_that("adversarial transport probes fail closed", {
  executed <- FALSE
  for (name in c("STRLING_DYNAMIC_ABI_PROBE", "STRLING_DYNAMIC_OVERSIZE_PROBE", "STRLING_DYNAMIC_DUPLICATE_PROBE", "STRLING_DYNAMIC_INVALID_UTF8_PROBE", "STRLING_DYNAMIC_RELEASE_FAILURE_PROBE")) {
    path <- Sys.getenv(name, unset = NA_character_)
    if (!is.na(path)) {
      executed <- TRUE
      expect_error(strling_describe(strling_load_native(path)))
    }
  }
  skip_if_not(executed, "certification probes unavailable")
})
