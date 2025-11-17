# STRling AST Node Definitions (R6 port)
#
# This file ports the Python `nodes.py` AST classes into idiomatic R using
# R6 classes. These classes are plain data containers with `to_list()` methods
# for serialization. Parser/compilation logic is intentionally out-of-scope.

library(R6)

# ---- Flags container ----
# Container for regex flags/modifiers.
Flags <- R6Class("Flags",
  public = list(
    ignoreCase = FALSE,
    multiline = FALSE,
    dotAll = FALSE,
    unicode = FALSE,
    extended = FALSE,

    initialize = function(ignoreCase = FALSE, multiline = FALSE, dotAll = FALSE, unicode = FALSE, extended = FALSE) {
      self$ignoreCase <- ignoreCase
      self$multiline <- multiline
      self$dotAll <- dotAll
      self$unicode <- unicode
      self$extended <- extended
    },

    to_list = function() {
      list(
        ignoreCase = self$ignoreCase,
        multiline = self$multiline,
        dotAll = self$dotAll,
        unicode = self$unicode,
        extended = self$extended
      )
    }
  )
)

# Helper to construct Flags from letters (e.g., "imuxs")
Flags_from_letters <- function(letters) {
  f <- Flags$new()
  if (is.null(letters) || letters == "") return(f)
  chars <- unlist(strsplit(gsub("[ ,]", "", letters), ""))
  for (ch in chars) {
    if (ch == "i") f$ignoreCase <- TRUE
    else if (ch == "m") f$multiline <- TRUE
    else if (ch == "s") f$dotAll <- TRUE
    else if (ch == "u") f$unicode <- TRUE
    else if (ch == "x") f$extended <- TRUE
    else {
      # unknown flags are ignored here
    }
  }
  f
}

# ---- Base node ----
Node <- R6Class("Node",
  public = list(
    to_list = function() stop("to_list() not implemented for base Node")
  )
)

# ---- Concrete nodes matching Base Schema ----
Alt <- R6Class("Alt", inherit = Node,
  public = list(
    branches = NULL,
    initialize = function(branches = list()) {
      self$branches <- branches
    },
    to_list = function() {
      list(kind = "Alt", branches = lapply(self$branches, function(b) b$to_list()))
    }
  )
)

Seq <- R6Class("Seq", inherit = Node,
  public = list(
    parts = NULL,
    initialize = function(parts = list()) {
      self$parts <- parts
    },
    to_list = function() {
      list(kind = "Seq", parts = lapply(self$parts, function(p) p$to_list()))
    }
  )
)

Lit <- R6Class("Lit", inherit = Node,
  public = list(
    value = NULL,
    initialize = function(value = "") {
      self$value <- as.character(value)
    },
    to_list = function() {
      list(kind = "Lit", value = self$value)
    }
  )
)

Dot <- R6Class("Dot", inherit = Node,
  public = list(
    initialize = function() {},
    to_list = function() list(kind = "Dot")
  )
)

Anchor <- R6Class("Anchor", inherit = Node,
  public = list(
    at = NULL,
    initialize = function(at) { self$at <- at },
    to_list = function() list(kind = "Anchor", at = self$at)
  )
)

# --- CharClass --
ClassItem <- R6Class("ClassItem",
  public = list(
    to_list = function() stop("Subclass must implement to_list")
  )
)

ClassRange <- R6Class("ClassRange", inherit = ClassItem,
  public = list(
    from_ch = NULL,
    to_ch = NULL,
    initialize = function(from_ch, to_ch) {
      self$from_ch <- from_ch
      self$to_ch <- to_ch
    },
    to_list = function() list(kind = "Range", from = self$from_ch, to = self$to_ch)
  )
)

ClassLiteral <- R6Class("ClassLiteral", inherit = ClassItem,
  public = list(
    ch = NULL,
    initialize = function(ch) { self$ch <- ch },
    to_list = function() list(kind = "Char", char = self$ch)
  )
)

ClassEscape <- R6Class("ClassEscape", inherit = ClassItem,
  public = list(
    type = NULL,
    property = NULL,
    initialize = function(type, property = NULL) {
      self$type <- type
      self$property <- property
    },
    to_list = function() {
      d <- list(kind = "Esc", type = self$type)
      if (!is.null(self$property) && self$type %in% c("p", "P")) d$property <- self$property
      d
    }
  )
)

CharClass <- R6Class("CharClass", inherit = Node,
  public = list(
    negated = FALSE,
    items = NULL,
    initialize = function(negated = FALSE, items = list()) {
      self$negated <- negated
      self$items <- items
    },
    to_list = function() list(kind = "CharClass", negated = self$negated, items = lapply(self$items, function(it) it$to_list()))
  )
)

Quant <- R6Class("Quant", inherit = Node,
  public = list(
    child = NULL,
    min = NULL,
    max = NULL,
    mode = NULL,
    initialize = function(child, min, max, mode) {
      self$child <- child
      self$min <- min
      self$max <- max
      self$mode <- mode
    },
    to_list = function() list(kind = "Quant", child = self$child$to_list(), min = self$min, max = self$max, mode = self$mode)
  )
)

Group <- R6Class("Group", inherit = Node,
  public = list(
    capturing = NULL,
    body = NULL,
    name = NULL,
    atomic = NULL,
    initialize = function(capturing, body, name = NULL, atomic = NULL) {
      self$capturing <- capturing
      self$body <- body
      self$name <- name
      self$atomic <- atomic
    },
    to_list = function() {
      data <- list(kind = "Group", capturing = self$capturing, body = self$body$to_list())
      if (!is.null(self$name)) data$name <- self$name
      if (!is.null(self$atomic)) data$atomic <- self$atomic
      data
    }
  )
)

Backref <- R6Class("Backref", inherit = Node,
  public = list(
    byIndex = NULL,
    byName = NULL,
    initialize = function(byIndex = NULL, byName = NULL) {
      self$byIndex <- byIndex
      self$byName <- byName
    },
    to_list = function() {
      data <- list(kind = "Backref")
      if (!is.null(self$byIndex)) data$byIndex <- self$byIndex
      if (!is.null(self$byName)) data$byName <- self$byName
      data
    }
  )
)

Look <- R6Class("Look", inherit = Node,
  public = list(
    dir = NULL,
    neg = NULL,
    body = NULL,
    initialize = function(dir, neg, body) {
      self$dir <- dir
      self$neg <- neg
      self$body <- body
    },
    to_list = function() list(kind = "Look", dir = self$dir, neg = self$neg, body = self$body$to_list())
  )
)
