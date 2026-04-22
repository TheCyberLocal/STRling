local essential = require("src.essential")
local strling = require("src.strling")
local pcre2 = require("src.pcre2")
local json = require("cjson")

local function find_spec()
  local dir = "."
  for _ = 1, 10 do
    local path = dir .. "/spec/stdlib/essential_5.json"
    local f = io.open(path, "r")
    if f then f:close() return path end
    dir = dir .. "/.."
  end
  error("essential_5.json not found")
end

local f = io.open(find_spec(), "r")
local spec = json.decode(f:read("*a"))
f:close()

local rex = require("rex_pcre2")

local function compile(ast)
  return rex.new("^(?:" .. pcre2.emit(strling.compile(ast)) .. ")$")
end

local function fixtures(p, k) return spec.patterns[p].fixtures[k] end

local function all_match(re, samples)
  for _, s in ipairs(samples) do
    assert.is_truthy(re:match(s), "expected match: " .. s)
  end
end

local function none_match(re, samples)
  for _, s in ipairs(samples) do
    assert.is_falsy(re:match(s), "unexpected match: " .. s)
  end
end

describe("Essential 5", function()
  it("email valid",   function() all_match(compile(essential.email()), fixtures('email', 'valid')) end)
  it("email invalid", function() none_match(compile(essential.email()), fixtures('email', 'invalid')) end)
  it("url valid",     function() all_match(compile(essential.url()), fixtures('url', 'valid')) end)
  it("url invalid",   function() none_match(compile(essential.url()), fixtures('url', 'invalid')) end)
  it("uuid default valid",   function() all_match(compile(essential.uuid()), fixtures('uuid', 'valid_default')) end)
  it("uuid default invalid", function() none_match(compile(essential.uuid()), fixtures('uuid', 'invalid_default')) end)
  it("uuid v4 valid",        function() all_match(compile(essential.uuid(4)), fixtures('uuid', 'valid_v4')) end)
  it("uuid v4 invalid",      function() none_match(compile(essential.uuid(4)), fixtures('uuid', 'invalid_v4')) end)
  it("ip v4 valid",   function() all_match(compile(essential.ip(4)), fixtures('ip', 'valid_v4')) end)
  it("ip v4 invalid", function() none_match(compile(essential.ip(4)), fixtures('ip', 'invalid_v4')) end)
  it("ip v6 valid",   function() all_match(compile(essential.ip(6)), fixtures('ip', 'valid_v6')) end)
  it("ip v6 invalid", function() none_match(compile(essential.ip(6)), fixtures('ip', 'invalid_v6')) end)
  it("ip any v4",     function() all_match(compile(essential.ip()), fixtures('ip', 'valid_v4')) end)
  it("ip any v6",     function() all_match(compile(essential.ip()), fixtures('ip', 'valid_v6')) end)
  it("dateTime valid",   function() all_match(compile(essential.date_time()), fixtures('dateTime', 'valid')) end)
  it("dateTime invalid", function() none_match(compile(essential.date_time()), fixtures('dateTime', 'invalid')) end)
end)
