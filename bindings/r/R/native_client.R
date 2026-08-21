.strling_interop_protocol_version <- "1.0.0"
.strling_max_request_bytes <- 10485760
.strling_empty_object <- structure(list(), names = character())

#' Load a canonical STRling native adapter
#' @export
strling_load_native <- function(library_path) {
  if (length(library_path) != 1L || !nzchar(library_path) || !grepl("^(?:/|[A-Za-z]:[/\\\\]|\\\\\\\\)", library_path)) {
    stop("native STRling library path must be absolute", call. = FALSE)
  }
  normalized <- normalizePath(library_path, mustWork = TRUE)
  structure(list(pointer = .Call(strling_r_open, normalized), library_path = normalized), class = "strling_native_client")
}

.strling_assert_client <- function(client) {
  if (!inherits(client, "strling_native_client") || is.null(client$pointer)) stop("native STRling client is invalid", call. = FALSE)
}

#' Execute a canonical interop request
#' @export
strling_execute <- function(client, request) {
  .strling_assert_client(client)
  encoded <- charToRaw(enc2utf8(.strling_encode_json(request)))
  if (length(encoded) > .strling_max_request_bytes) stop("interop request exceeds 10485760 bytes", call. = FALSE)
  response <- .strling_decode_object(.Call(strling_r_execute, client$pointer, encoded))
  if (!identical(response$interop_protocol_version, .strling_interop_protocol_version)) stop("interop response has an unsupported version", call. = FALSE)
  if (!is.character(response$status) || length(response$status) != 1L || !response$status %in% c("completed", "error")) {
    stop("interop response has an unsupported status", call. = FALSE)
  }
  if (identical(response$status, "completed") && !"result" %in% names(response)) stop("completed interop response has no result", call. = FALSE)
  if (identical(response$status, "error") &&
      (!is.list(response$error) || !is.character(response$error$code) || length(response$error$code) != 1L ||
       !is.character(response$error$path) || length(response$error$path) != 1L)) {
    stop("failed interop response has no stable code and path", call. = FALSE)
  }
  response
}

.strling_envelope <- function(operation, payload) list(interop_protocol_version = .strling_interop_protocol_version, operation = operation, payload = payload)
.strling_completed <- function(client, request) {
  response <- strling_execute(client, request)
  if (identical(response$status, "error")) stop(paste(response$error$code, "at", response$error$path), call. = FALSE)
  response$result
}

#' @export
strling_describe <- function(client) .strling_completed(client, .strling_envelope("describe", .strling_empty_object))
#' @export
strling_compile <- function(client, compile_request, target_profile = NULL) {
  payload <- list(compile_request = compile_request)
  if (!is.null(target_profile)) payload$target_profile <- target_profile
  .strling_completed(client, .strling_envelope("compile", payload))
}
#' @export
strling_inspect_target_profile <- function(client, target_profile) {
  .strling_completed(client, .strling_envelope("target_profile.inspect", list(target_profile = target_profile)))
}
#' @export
strling_simply_compile <- function(client, builder_request, target_profile = NULL) {
  payload <- list(builder_request = builder_request)
  if (!is.null(target_profile)) payload$target_profile <- target_profile
  .strling_completed(client, .strling_envelope("simply.compile", payload))
}
#' @export
strling_close <- function(client) { .strling_assert_client(client); invisible(.Call(strling_r_close, client$pointer)) }
#' @export
strling_is_closed <- function(client) { .strling_assert_client(client); isTRUE(.Call(strling_r_is_closed, client$pointer)) }
