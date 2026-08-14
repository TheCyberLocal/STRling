#' Essential standard-library patterns for STRling.
#'
#' Provides compatibility lexical-shape helpers for common formats. They do
#' not establish semantic validity or standards conformance. Each helper composes existing AST
#' primitives so the compiled output flows through the standard pipeline.

.letter_items <- function() list(
  strling_class_range("A", "Z"),
  strling_class_range("a", "z")
)

.digit_items <- function() list(strling_class_escape("d"))

.hex_items <- function() list(
  strling_class_range("A", "F"),
  strling_class_range("a", "f"),
  strling_class_range("0", "9")
)

.chars_items <- function(s) {
  chars <- strsplit(s, "")[[1]]
  lapply(chars, strling_class_literal)
}

.class_of <- function(items, min, max) {
  cc <- strling_character_class(items, negated = FALSE)
  strling_quantifier(cc, min = min, max = max)
}

.dig_n  <- function(min, max) .class_of(.digit_items(),  min, max)
.hex_n  <- function(min, max) .class_of(.hex_items(),    min, max)
.lett_n <- function(min, max) .class_of(.letter_items(), min, max)

.lit <- function(s) strling_literal(s)

.opt <- function(node) {
  grouped <- strling_group(node, capturing = FALSE)
  strling_quantifier(grouped, min = 0L, max = 1L)
}

.alt <- function(branches) strling_alternation(branches)
.seq <- function(parts)    strling_sequence(parts)

#' Email-like lexical shape; RFC 5322 conformance is not claimed.
#' @export
sl_email <- function() {
  local_  <- .class_of(c(.letter_items(), .digit_items(), .chars_items("._%+-")), 1L, "Inf")
  domain  <- .class_of(c(.letter_items(), .digit_items(), .chars_items(".-")),    1L, "Inf")
  tld     <- .lett_n(2L, "Inf")
  .seq(list(local_, .lit("@"), domain, .lit("."), tld))
}

#' HTTP(S) URL-like lexical shape; RFC 3986 conformance is not claimed.
#' @export
sl_url <- function() {
  base      <- c(.letter_items(), .digit_items(), .chars_items("/_-.~%&=:@!$'()*+,;"))
  with_q    <- c(base, .chars_items("?"))
  with_frag <- c(with_q, .chars_items("#"))

  scheme   <- .seq(list(.lit("http"), .opt(.lit("s"))))
  host     <- .class_of(c(.letter_items(), .digit_items(), .chars_items(".-")), 1L, "Inf")
  port     <- .opt(.seq(list(.lit(":"), .dig_n(1L, "Inf"))))
  path     <- .opt(.seq(list(.lit("/"), .class_of(base,      0L, "Inf"))))
  query    <- .opt(.seq(list(.lit("?"), .class_of(with_q,    0L, "Inf"))))
  fragment <- .opt(.seq(list(.lit("#"), .class_of(with_frag, 0L, "Inf"))))
  .seq(list(scheme, .lit("://"), host, port, path, query, fragment))
}

#' RFC 9562 UUID text shape; version = 4 constrains version/variant nibbles.
#' @export
sl_uuid <- function(version = 0L) {
  if (identical(as.integer(version), 4L)) {
    variant <- .class_of(.chars_items("89ABab"), 1L, 1L)
    return(.seq(list(
      .hex_n(8L, 8L), .lit("-"),
      .hex_n(4L, 4L), .lit("-"),
      .lit("4"), .hex_n(3L, 3L), .lit("-"),
      variant, .hex_n(3L, 3L), .lit("-"),
      .hex_n(12L, 12L)
    )))
  }
  .seq(list(
    .hex_n(8L, 8L), .lit("-"),
    .hex_n(4L, 4L), .lit("-"),
    .hex_n(4L, 4L), .lit("-"),
    .hex_n(4L, 4L), .lit("-"),
    .hex_n(12L, 12L)
  ))
}

.ipv4 <- function() .seq(list(
  .dig_n(1L, 3L), .lit("."),
  .dig_n(1L, 3L), .lit("."),
  .dig_n(1L, 3L), .lit("."),
  .dig_n(1L, 3L)
))

.ipv6 <- function() .seq(list(
  .hex_n(1L, 4L), .lit(":"),
  .hex_n(1L, 4L), .lit(":"),
  .hex_n(1L, 4L), .lit(":"),
  .hex_n(1L, 4L), .lit(":"),
  .hex_n(1L, 4L), .lit(":"),
  .hex_n(1L, 4L), .lit(":"),
  .hex_n(1L, 4L), .lit(":"),
  .hex_n(1L, 4L)
))

#' IP-like lexical shape. version = 4 selects four digit groups, version = 6
#' selects eight hex groups, and default selects either; validity is not claimed.
#' @export
sl_ip <- function(version = 0L) {
  v <- as.integer(version)
  if (identical(v, 4L)) return(.ipv4())
  if (identical(v, 6L)) return(.ipv6())
  .alt(list(.ipv4(), .ipv6()))
}

#' Timestamp-like lexical shape; RFC 3339 / ISO 8601 validity is not claimed.
#' @export
sl_date_time <- function() {
  sign   <- .class_of(.chars_items("+-"), 1L, 1L)
  frac   <- .seq(list(.lit("."), .dig_n(1L, "Inf")))
  offset <- .seq(list(sign, .dig_n(2L, 2L), .lit(":"), .dig_n(2L, 2L)))
  .seq(list(
    .dig_n(4L, 4L), .lit("-"), .dig_n(2L, 2L), .lit("-"), .dig_n(2L, 2L),
    .lit("T"),
    .dig_n(2L, 2L), .lit(":"), .dig_n(2L, 2L), .lit(":"), .dig_n(2L, 2L),
    .opt(frac),
    .opt(.alt(list(.lit("Z"), offset)))
  ))
}
