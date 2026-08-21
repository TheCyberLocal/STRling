local strling = require("strling")
local json = require("cjson.safe")

describe("canonical native adapter", function()
  it("builds canonical requests and lexical helper steps", function()
    local request = strling.source_compile_request('literal "hello"')
    assert.are.equal("1.0.0", request.contract_version)
    assert.are.equal("semantic_strling", request.input.document.frontend.id)
    assert.are.equal("stdlib.email", strling.email("root").arguments.helper_id)
  end)

  it("consumes the canonical Essential fixture for every stdlib helper", function()
    local handle = assert(io.open("../../spec/stdlib/essential_5.json", "rb"))
    local encoded = handle:read("*a")
    handle:close()
    local fixture = assert(json.decode(encoded))
    local steps = {
      dateTime = strling.date_time("date-time"),
      email = strling.email("email"),
      ip = strling.ip("ip"),
      url = strling.url("url"),
      uuid = strling.uuid("uuid"),
    }
    for name, step in pairs(steps) do
      assert.is_table(fixture.patterns[name])
      local helper_id = name == "dateTime" and "date_time" or name
      assert.are.equal("stdlib." .. helper_id, step.arguments.helper_id)
    end
  end)

  it("rejects relative paths", function()
    assert.has_error(function() strling.load_native("libstrling_interop.so") end)
    assert.has_error(function() strling.load_native("/tmp/strling\0invalid") end)
  end)

  it("executes the certification probe when supplied", function()
    local path = os.getenv("STRLING_DYNAMIC_PROBE")
    if not path then return end
    local client = strling.load_native(path)
    local expected = { unicode = "雪" }
    local results = {
      describe = client:describe(),
      compile = client:compile(strling.source_compile_request('literal "雪"')),
      ["target_profile.inspect"] = client:inspect_target_profile({ contract_version = "1.0.0" }),
      ["simply.compile"] = client:simply_compile(strling.simply_builder_request({ strling.email("root") }, "root")),
    }
    for _, result in pairs(results) do assert.are.same(expected, result) end
    local evidence_dir = os.getenv("STRLING_DYNAMIC_EVIDENCE_DIR")
    if evidence_dir then
      local evidence_file = assert(io.open(evidence_dir .. "/lua.json", "wb"))
      local encoded_results, encode_error = json.encode(results)
      assert.is_nil(encode_error)
      assert.is_string(encoded_results)
      assert(evidence_file:write(encoded_results))
      assert(evidence_file:close())
    end
    client:close()
    assert.is_true(client:is_closed())
    client:close()
    assert.has_error(function() client:describe() end)
  end)

  it("rejects adversarial transport probes", function()
    for _, name in ipairs({
      "STRLING_DYNAMIC_ABI_PROBE", "STRLING_DYNAMIC_OVERSIZE_PROBE",
      "STRLING_DYNAMIC_DUPLICATE_PROBE", "STRLING_DYNAMIC_INVALID_UTF8_PROBE",
      "STRLING_DYNAMIC_RELEASE_FAILURE_PROBE",
    }) do
      local path = os.getenv(name)
      if path then assert.has_error(function() strling.load_native(path):describe() end) end
    end
  end)
end)
