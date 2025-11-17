# STRling Intermediate Representation (IR) Node Definitions (R6 port)
#
# This file ports the Python `ir.py` IR classes into idiomatic R using R6.
# IR nodes are simple data containers with `to_list()` for serialization.

library(R6)

IROp <- R6Class("IROp",
  public = list(
    to_list = function() stop("to_list() not implemented for IROp")
  )
)

IRAlt <- R6Class("IRAlt", inherit = IROp,
  public = list(
    branches = NULL,
    initialize = function(branches = list()) { self$branches <- branches },
    to_list = function() list(ir = "Alt", branches = lapply(self$branches, function(b) b$to_list()))
  )
)

IRSeq <- R6Class("IRSeq", inherit = IROp,
  public = list(
    parts = NULL,
    initialize = function(parts = list()) { self$parts <- parts },
    to_list = function() list(ir = "Seq", parts = lapply(self$parts, function(p) p$to_list()))
  )
)

IRLit <- R6Class("IRLit", inherit = IROp,
  public = list(
    value = NULL,
    initialize = function(value = "") { self$value <- as.character(value) },
    to_list = function() list(ir = "Lit", value = self$value)
  )
)

IRDot <- R6Class("IRDot", inherit = IROp,
  public = list(
    initialize = function() {},
    to_list = function() list(ir = "Dot")
  )
)

IRAnchor <- R6Class("IRAnchor", inherit = IROp,
  public = list(
    at = NULL,
    initialize = function(at) { self$at <- at },
    to_list = function() list(ir = "Anchor", at = self$at)
  )
)

IRClassItem <- R6Class("IRClassItem",
  public = list(
    to_list = function() stop("Subclass must implement to_list")
  )
)

IRClassRange <- R6Class("IRClassRange", inherit = IRClassItem,
  public = list(
    from_ch = NULL,
    to_ch = NULL,
    initialize = function(from_ch, to_ch) { self$from_ch <- from_ch; self$to_ch <- to_ch },
    to_list = function() list(ir = "Range", from = self$from_ch, to = self$to_ch)
  )
)

IRClassLiteral <- R6Class("IRClassLiteral", inherit = IRClassItem,
  public = list(
    ch = NULL,
    initialize = function(ch) { self$ch <- ch },
    to_list = function() list(ir = "Char", char = self$ch)
  )
)

IRClassEscape <- R6Class("IRClassEscape", inherit = IRClassItem,
  public = list(
    type = NULL,
    property = NULL,
    initialize = function(type, property = NULL) { self$type <- type; self$property <- property },
    to_list = function() { d <- list(ir = "Esc", type = self$type); if (!is.null(self$property)) d$property <- self$property; d }
  )
)

IRCharClass <- R6Class("IRCharClass", inherit = IROp,
  public = list(
    negated = FALSE,
    items = NULL,
    initialize = function(negated = FALSE, items = list()) { self$negated <- negated; self$items <- items },
    to_list = function() list(ir = "CharClass", negated = self$negated, items = lapply(self$items, function(i) i$to_list()))
  )
)

IRQuant <- R6Class("IRQuant", inherit = IROp,
  public = list(
    child = NULL,
    min = NULL,
    max = NULL,
    mode = NULL,
    initialize = function(child, min, max, mode) { self$child <- child; self$min <- min; self$max <- max; self$mode <- mode },
    to_list = function() list(ir = "Quant", child = self$child$to_list(), min = self$min, max = self$max, mode = self$mode)
  )
)

IRGroup <- R6Class("IRGroup", inherit = IROp,
  public = list(
    capturing = NULL,
    body = NULL,
    name = NULL,
    atomic = NULL,
    initialize = function(capturing, body, name = NULL, atomic = NULL) { self$capturing <- capturing; self$body <- body; self$name <- name; self$atomic <- atomic },
    to_list = function() {
      d <- list(ir = "Group", capturing = self$capturing, body = self$body$to_list())
      if (!is.null(self$name)) d$name <- self$name
      if (!is.null(self$atomic)) d$atomic <- self$atomic
      d
    }
  )
)

IRBackref <- R6Class("IRBackref", inherit = IROp,
  public = list(
    byIndex = NULL,
    byName = NULL,
    initialize = function(byIndex = NULL, byName = NULL) { self$byIndex <- byIndex; self$byName <- byName },
    to_list = function() {
      d <- list(ir = "Backref")
      if (!is.null(self$byIndex)) d$byIndex <- self$byIndex
      if (!is.null(self$byName)) d$byName <- self$byName
      d
    }
  )
)

IRLook <- R6Class("IRLook", inherit = IROp,
  public = list(
    dir = NULL,
    neg = NULL,
    body = NULL,
    initialize = function(dir, neg, body) { self$dir <- dir; self$neg <- neg; self$body <- body },
    to_list = function() list(ir = "Look", dir = self$dir, neg = self$neg, body = self$body$to_list())
  )
)
