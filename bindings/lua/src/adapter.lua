-- Thin Lua projection of the canonical STRling interop protocol.
local json = require("cjson.safe")
local native = require("strling_native")

local strling = {
  VERSION = "3.0.0",
  INTEROP_PROTOCOL_VERSION = "1.0.0",
  NATIVE_ABI_VERSION = 1,
  MAX_INTEROP_REQUEST_BYTES = 10485760,
  MAX_INTEROP_RESPONSE_BYTES = 33554432,
}

if json.encode_invalid_numbers then json.encode_invalid_numbers(false) end
if json.decode_invalid_numbers then json.decode_invalid_numbers(false) end

local function skip_whitespace(text, index)
  while index <= #text and string.find(" \t\r\n", string.sub(text, index, index), 1, true) do
    index = index + 1
  end
  return index
end

local function scan_string(text, index)
  if string.sub(text, index, index) ~= '"' then error("expected JSON string") end
  local start = index
  index = index + 1
  while index <= #text do
    local byte = string.byte(text, index)
    local char = string.sub(text, index, index)
    index = index + 1
    if char == '"' then return index, string.sub(text, start, index - 1) end
    if byte < 32 then error("unescaped control character in JSON string") end
    if char == "\\" then
      local escape = string.sub(text, index, index)
      index = index + 1
      if escape == "u" then
        local hex = string.sub(text, index, index + 3)
        if #hex ~= 4 or string.find(hex, "[^0-9a-fA-F]") then error("invalid Unicode escape") end
        index = index + 4
      elseif not string.find('"\\/bfnrt', escape, 1, true) then
        error("invalid JSON escape")
      end
    end
  end
  error("unterminated JSON string")
end

local scan_value

local function scan_object(text, index)
  index = skip_whitespace(text, index + 1)
  if string.sub(text, index, index) == "}" then return index + 1 end
  local keys = {}
  while true do
    local literal
    index, literal = scan_string(text, skip_whitespace(text, index))
    local key, decode_error = json.decode(literal)
    if decode_error then error(decode_error) end
    if keys[key] then error("duplicate property " .. literal) end
    keys[key] = true
    index = skip_whitespace(text, index)
    if string.sub(text, index, index) ~= ":" then error("expected JSON colon") end
    index = scan_value(text, index + 1)
    index = skip_whitespace(text, index)
    local delimiter = string.sub(text, index, index)
    if delimiter == "}" then return index + 1 end
    if delimiter ~= "," then error("expected JSON object delimiter") end
    index = index + 1
  end
end

local function scan_array(text, index)
  index = skip_whitespace(text, index + 1)
  if string.sub(text, index, index) == "]" then return index + 1 end
  while true do
    index = scan_value(text, index)
    index = skip_whitespace(text, index)
    local delimiter = string.sub(text, index, index)
    if delimiter == "]" then return index + 1 end
    if delimiter ~= "," then error("expected JSON array delimiter") end
    index = index + 1
  end
end

scan_value = function(text, index)
  index = skip_whitespace(text, index)
  local char = string.sub(text, index, index)
  if char == "{" then return scan_object(text, index) end
  if char == "[" then return scan_array(text, index) end
  if char == '"' then return scan_string(text, index) end
  local finish = index
  while finish <= #text and not string.find(" \t\r\n,]}", string.sub(text, finish, finish), 1, true) do
    finish = finish + 1
  end
  if finish == index then error("invalid JSON token") end
  return finish
end

local function decode_response(raw)
  local ok, finish = pcall(scan_value, raw, 1)
  if not ok then error("native STRling response is not strict JSON: " .. finish) end
  if skip_whitespace(raw, finish) ~= #raw + 1 then error("native STRling response has trailing JSON content") end
  local value, decode_error = json.decode(raw)
  if decode_error then error("native STRling response is not strict JSON: " .. decode_error) end
  if type(value) ~= "table" or value.interop_protocol_version ~= strling.INTEROP_PROTOCOL_VERSION then
    error("interop response has an unsupported version")
  end
  if value.status ~= "completed" and value.status ~= "error" then error("interop response has an unsupported status") end
  if value.status == "completed" and value.result == nil then error("completed interop response has no result") end
  if value.status == "error" and
      (type(value.error) ~= "table" or type(value.error.code) ~= "string" or type(value.error.path) ~= "string") then
    error("failed interop response has no stable code and path")
  end
  return value
end

local client_methods = {}
client_methods.__index = client_methods

function client_methods:execute(request)
  local encoded, encode_error = json.encode(request)
  if not encoded then error("interop request is not strict JSON: " .. encode_error) end
  if #encoded > strling.MAX_INTEROP_REQUEST_BYTES then error("interop request exceeds 10485760 bytes") end
  return decode_response(self._native:execute(encoded))
end

local function envelope(operation, payload)
  return { interop_protocol_version = strling.INTEROP_PROTOCOL_VERSION, operation = operation, payload = payload }
end

local function completed_result(self, request)
  local response = self:execute(request)
  if response.status == "error" then error(response.error.code .. " at " .. response.error.path) end
  return response.result
end

function client_methods:describe() return completed_result(self, envelope("describe", {})) end
function client_methods:compile(compile_request, target_profile)
  local payload = { compile_request = compile_request }
  if target_profile ~= nil then payload.target_profile = target_profile end
  return completed_result(self, envelope("compile", payload))
end
function client_methods:inspect_target_profile(target_profile)
  return completed_result(self, envelope("target_profile.inspect", { target_profile = target_profile }))
end
function client_methods:simply_compile(builder_request, target_profile)
  local payload = { builder_request = builder_request }
  if target_profile ~= nil then payload.target_profile = target_profile end
  return completed_result(self, envelope("simply.compile", payload))
end
function client_methods:close() return self._native:close() end
function client_methods:is_closed() return self._native:is_closed() end
function client_methods:library_path() return self._native:library_path() end

function strling.load_native(library_path)
  return setmetatable({ _native = native.open(library_path) }, client_methods)
end

function strling.source_compile_request(source, options)
  options = options or {}
  local specification = tostring(options.specification_version or "1.0-draft.1")
  local frontend = tostring(options.frontend_id or "semantic_strling")
  local request = {
    contract_version = "1.0.0", specification_version = specification,
    input = { kind = "source", document = {
      contract_version = "1.0.0", source_id = tostring(options.source_id or "src:lua.adapter"),
      specification_version = specification,
      frontend = { id = frontend, dialect_version = tostring(options.frontend_version or specification) },
      content = { kind = "inline", encoding = "utf-8", media_type = tostring(options.media_type or "text/strling"), text = source },
      provenance = { kind = "authored" },
    } },
    requested_outputs = options.requested_outputs or { "semantic", "analysis" },
    compiler_options = options.compiler_options or {
      partial_semantics = "forbid", diagnostic_policy = { minimum_severity = "hint" },
    },
  }
  if options.target_profile_reference ~= nil then request.target_profile = options.target_profile_reference end
  return request
end

function strling.stdlib_helper(step_id, helper_id, parameters)
  return { step_id = tostring(step_id), operation = "stdlib_helper", arguments = { helper_id = helper_id, parameters = parameters or {} } }
end

function strling.simply_builder_request(steps, root_step_id, identity_namespace)
  return {
    protocol_version = "1.1.0", contract_version = "1.0.0", specification_version = "1.0-draft.1",
    identity_namespace = identity_namespace or "lua.adapter",
    semantic_options = {
      case_matching = "sensitive", text_model = "unicode_scalar_values",
      builtin_character_domain = "unicode", wildcard_line_terminators = "exclude",
    },
    steps = steps, root_step_id = tostring(root_step_id),
    compile = { requested_outputs = { "semantic", "analysis" }, compiler_options = {
      partial_semantics = "forbid", diagnostic_policy = { minimum_severity = "hint" },
    } },
  }
end

local stdlib = require("strling.stdlib_generated")
for name, value in pairs(stdlib) do strling[name] = value end

return strling
