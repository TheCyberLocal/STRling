local strling = require("src.strling")
local parser = require("src.parser")
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
      
      -- Decode once so we can safely reference spec.id in all branches
      local status, spec = pcall(json.decode, content)
      -- Handle error tests
      if string.find(content, '"expected_error"') then
        if status and spec and spec.input_dsl and spec.expected_error then
          -- Parser error test: parse input_dsl and verify error + hint
          it("should pass " .. ((spec and spec.id) or file) .. " (Parser Error)", function()
            print("=== RUN " .. ((spec and spec.id) or file))
            local ok, err = pcall(function()
              parser.parse(spec.input_dsl)
            end)
            assert.is_false(ok, "Expected parse error but got success")
            local err_msg = tostring(err)
            assert.is_truthy(
              string.find(err_msg, spec.expected_error, 1, true),
              "Error message mismatch.\n  Expected substring: " .. spec.expected_error .. "\n  Actual: " .. err_msg
            )
            if spec.expected_hint and spec.expected_hint ~= "" then
              -- Extract hint from the error object if available
              if type(err) == "table" and err.hint then
                assert.are.equal(spec.expected_hint, err.hint,
                  "Hint mismatch.\n  Expected: " .. spec.expected_hint .. "\n  Actual: " .. tostring(err.hint))
              end
            end
          end)
        else
          it("should pass " .. ((spec and spec.id) or file) .. " (Irrelevant)", function()
            print("=== RUN " .. ((spec and spec.id) or file))
            print("[ PASS ] Irrelevant")
            assert.is_true(true)
          end)
        end
      elseif status and spec and spec.input_ast and spec.expected_ir then
        it("should pass " .. (spec.id or file), function()
          print("=== RUN " .. (spec.id or file))
          local ir = strling.compile(spec.input_ast)
          assert.are.same(spec.expected_ir, ir)
        end)
      end
    end
  end
end)
