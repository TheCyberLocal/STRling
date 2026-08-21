# Generated from the canonical standard-library registry. Do not edit.
# These lexical helpers record Simply recipes; they do not validate semantics.
.strling_stdlib_source_sha256 <- "36779a57c8016a0ff4a1ba00e9c6cb198246bf8e170edb1e0d627c0ed91f19a0"
.strling_stdlib_registry_version <- "1.0.0"
.strling_stdlib_helper_ids <- c("stdlib.date_time", "stdlib.email", "stdlib.ip", "stdlib.url", "stdlib.uuid")

#' @export
sl_date_time <- function(step_id) strling_stdlib_helper(step_id, "stdlib.date_time")
#' @export
sl_email <- function(step_id) strling_stdlib_helper(step_id, "stdlib.email")
#' @export
sl_ip <- function(step_id, version = NULL) strling_stdlib_helper(step_id, "stdlib.ip", list(version = version))
#' @export
sl_url <- function(step_id) strling_stdlib_helper(step_id, "stdlib.url")
#' @export
sl_uuid <- function(step_id, version = NULL) strling_stdlib_helper(step_id, "stdlib.uuid", list(version = version))
