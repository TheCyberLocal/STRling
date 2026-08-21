#' Construct a canonical source compile request
#' @export
strling_source_compile_request <- function(source, options = list()) {
  specification <- as.character(options$specification_version %||% "1.0-draft.1")
  frontend <- as.character(options$frontend_id %||% "semantic_strling")
  request <- list(
    contract_version = "1.0.0", specification_version = specification,
    input = list(kind = "source", document = list(
      contract_version = "1.0.0", source_id = as.character(options$source_id %||% "src:r.adapter"),
      specification_version = specification,
      frontend = list(id = frontend, dialect_version = as.character(options$frontend_version %||% specification)),
      content = list(kind = "inline", encoding = "utf-8", media_type = as.character(options$media_type %||% "text/strling"), text = as.character(source)),
      provenance = list(kind = "authored")
    )),
    requested_outputs = options$requested_outputs %||% c("semantic", "analysis"),
    compiler_options = options$compiler_options %||% list(
      partial_semantics = "forbid", diagnostic_policy = list(minimum_severity = "hint")
    )
  )
  if (!is.null(options$target_profile_reference)) request$target_profile <- options$target_profile_reference
  request
}

#' @export
strling_stdlib_helper <- function(step_id, helper_id, parameters = list()) {
  if (length(parameters) == 0L && is.null(names(parameters))) parameters <- .strling_empty_object
  list(step_id = as.character(step_id), operation = "stdlib_helper", arguments = list(helper_id = helper_id, parameters = parameters))
}

#' @export
strling_simply_builder_request <- function(steps, root_step_id, identity_namespace = "r.adapter") {
  list(
    protocol_version = "1.1.0", contract_version = "1.0.0", specification_version = "1.0-draft.1",
    identity_namespace = identity_namespace,
    semantic_options = list(
      case_matching = "sensitive", text_model = "unicode_scalar_values",
      builtin_character_domain = "unicode", wildcard_line_terminators = "exclude"
    ),
    steps = steps, root_step_id = as.character(root_step_id),
    compile = list(
      requested_outputs = c("semantic", "analysis"),
      compiler_options = list(partial_semantics = "forbid", diagnostic_policy = list(minimum_severity = "hint"))
    )
  )
}

`%||%` <- function(value, fallback) if (is.null(value)) fallback else value
