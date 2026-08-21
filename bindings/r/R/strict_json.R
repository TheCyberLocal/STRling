.strling_skip_whitespace <- function(text, index) {
  length <- nchar(text, type = "chars")
  while (index <= length && grepl(substr(text, index, index), " \t\r\n", fixed = TRUE)) index <- index + 1L
  index
}

.strling_scan_string <- function(text, index) {
  if (substr(text, index, index) != '"') stop("expected JSON string", call. = FALSE)
  start <- index
  index <- index + 1L
  length <- nchar(text, type = "chars")
  while (index <= length) {
    char <- substr(text, index, index)
    value <- utf8ToInt(char)
    index <- index + 1L
    if (char == '"') return(list(index = index, literal = substr(text, start, index - 1L)))
    if (length(value) == 1L && value < 32L) stop("unescaped control character in JSON string", call. = FALSE)
    if (char == "\\") {
      escape <- substr(text, index, index)
      index <- index + 1L
      if (escape == "u") {
        hex <- substr(text, index, index + 3L)
        if (!grepl("^[0-9a-fA-F]{4}$", hex)) stop("invalid Unicode escape", call. = FALSE)
        index <- index + 4L
      } else if (!grepl(escape, '"\\/bfnrt', fixed = TRUE)) {
        stop("invalid JSON escape", call. = FALSE)
      }
    }
  }
  stop("unterminated JSON string", call. = FALSE)
}

.strling_scan_value <- NULL

.strling_scan_object <- function(text, index) {
  index <- .strling_skip_whitespace(text, index + 1L)
  if (substr(text, index, index) == "}") return(index + 1L)
  keys <- new.env(hash = TRUE, parent = emptyenv())
  repeat {
    scanned <- .strling_scan_string(text, .strling_skip_whitespace(text, index))
    index <- scanned$index
    key <- jsonlite::fromJSON(scanned$literal, simplifyVector = FALSE)
    identity <- paste0("key:", key)
    if (exists(identity, envir = keys, inherits = FALSE)) stop(paste("duplicate property", scanned$literal), call. = FALSE)
    assign(identity, TRUE, envir = keys)
    index <- .strling_skip_whitespace(text, index)
    if (substr(text, index, index) != ":") stop("expected JSON colon", call. = FALSE)
    index <- .strling_scan_value(text, index + 1L)
    index <- .strling_skip_whitespace(text, index)
    delimiter <- substr(text, index, index)
    if (delimiter == "}") return(index + 1L)
    if (delimiter != ",") stop("expected JSON object delimiter", call. = FALSE)
    index <- index + 1L
  }
}

.strling_scan_array <- function(text, index) {
  index <- .strling_skip_whitespace(text, index + 1L)
  if (substr(text, index, index) == "]") return(index + 1L)
  repeat {
    index <- .strling_scan_value(text, index)
    index <- .strling_skip_whitespace(text, index)
    delimiter <- substr(text, index, index)
    if (delimiter == "]") return(index + 1L)
    if (delimiter != ",") stop("expected JSON array delimiter", call. = FALSE)
    index <- index + 1L
  }
}

.strling_scan_value <- function(text, index) {
  index <- .strling_skip_whitespace(text, index)
  char <- substr(text, index, index)
  if (char == "{") return(.strling_scan_object(text, index))
  if (char == "[") return(.strling_scan_array(text, index))
  if (char == '"') return(.strling_scan_string(text, index)$index)
  length <- nchar(text, type = "chars")
  finish <- index
  while (finish <= length && !grepl(substr(text, finish, finish), " \t\r\n,]}", fixed = TRUE)) finish <- finish + 1L
  if (finish == index) stop("invalid JSON token", call. = FALSE)
  finish
}

.strling_encode_json <- function(value) {
  jsonlite::toJSON(value, auto_unbox = TRUE, null = "null", na = "null", digits = NA, pretty = FALSE)
}

.strling_decode_object <- function(raw) {
  text <- rawToChar(raw)
  finish <- .strling_scan_value(text, 1L)
  if (.strling_skip_whitespace(text, finish) != nchar(text, type = "chars") + 1L) stop("trailing JSON content", call. = FALSE)
  value <- jsonlite::fromJSON(text, simplifyVector = FALSE)
  if (!is.list(value) || is.null(names(value))) stop("interop response must be an object", call. = FALSE)
  value
}
