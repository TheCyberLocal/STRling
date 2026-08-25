-- Generated from the canonical standard-library registry. Do not edit.
-- These lexical helpers record Simply recipes; they do not validate semantics.
local surface = {
  SURFACE_SOURCE_SHA256 = "94f28b16873abd0b57b324b76e236cbe17706f5310758e066a88a776e4930a3d",
  REGISTRY_VERSION = "1.0.0",
  HELPER_IDS = { "stdlib.date_time", "stdlib.email", "stdlib.ip", "stdlib.url", "stdlib.uuid" },
}
local json_null = require("cjson.safe").null

local function helper(step_id, helper_id, parameters)
  return { step_id = tostring(step_id), operation = "stdlib_helper", arguments = { helper_id = helper_id, parameters = parameters or {} } }
end

function surface.date_time(step_id) return helper(step_id, "stdlib.date_time") end
function surface.email(step_id) return helper(step_id, "stdlib.email") end
function surface.ip(step_id, version) return helper(step_id, "stdlib.ip", { version = version == nil and json_null or version }) end
function surface.url(step_id) return helper(step_id, "stdlib.url") end
function surface.uuid(step_id, version) return helper(step_id, "stdlib.uuid", { version = version == nil and json_null or version }) end

return surface
