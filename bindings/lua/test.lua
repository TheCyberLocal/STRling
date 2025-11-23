package.path = package.path .. ";./?.lua"
local strling = require("src.strling")

print("Testing STRling Lua binding...")

if strling == nil then
  print("FAIL: strling module is nil")
  os.exit(1)
end

if strling.compile == nil then
  print("FAIL: strling.compile is nil")
  os.exit(1)
end

print("SUCCESS: Basic checks passed")
os.exit(0)
