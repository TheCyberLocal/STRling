local strling = require("src.strling")
local json = require("cjson")

describe("Conformance Tests", function()
  local spec_dir = "../../tests/spec"
  -- Use ls to find files. This works on Linux/WSL/macOS.
  local handle = io.popen('ls "' .. spec_dir .. '"/*.json')
  local files = handle:read("*a")
  handle:close()

  for file in string.gmatch(files, "[^\r\n]+") do
    local f = io.open(file, "r")
    if f then
      local content = f:read("*a")
      f:close()
      
      -- Skip error tests
      if not string.find(content, '"expected_error"') then
        local status, spec = pcall(json.decode, content)
        if status and spec.input_ast and spec.expected_ir then
           it("should pass " .. (spec.id or file), function()
              local ir = strling.compile(spec.input_ast)
              assert.are.same(spec.expected_ir, ir)
           end)
        end
      end
    end
  end
end)
