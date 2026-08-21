-- Generated from the canonical standard-library registry. Do not edit.
-- These lexical helpers record Simply recipes; they do not validate semantics.
local surface = {
  SURFACE_SOURCE_SHA256 = "36779a57c8016a0ff4a1ba00e9c6cb198246bf8e170edb1e0d627c0ed91f19a0",
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
