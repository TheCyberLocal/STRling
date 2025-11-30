package.path = package.path .. ";./?.lua"
local strling = require("src.strling")

if not strling.simply then
  print("FAIL: strling.simply is missing")
  os.exit(1)
end

local s = strling.simply
local p = s.capture(s.digit(3))

if p.type ~= "Group" then
  print("FAIL: Expected Group, got " .. tostring(p.type))
  os.exit(1)
end

if p.body.type ~= "Quantifier" then
  print("FAIL: Expected Quantifier body, got " .. tostring(p.body.type))
  os.exit(1)
end

if p.body.min ~= 3 then
  print("FAIL: Expected min 3, got " .. tostring(p.body.min))
  os.exit(1)
end

print("SUCCESS: Simply API verification passed")
