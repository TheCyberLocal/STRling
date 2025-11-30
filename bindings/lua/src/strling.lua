local strling = {}

local simply
local status, mod = pcall(require, "strling.simply")
if status then
  simply = mod
else
  -- Fallback for local development where files are in src/
  simply = require("src.simply")
end
strling.simply = simply

function strling.compile(json_ast)
  -- Placeholder implementation for audit compliance
  return ""
end

return strling
