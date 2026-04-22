--[[
    Emitter Edges Conformance — Lua bridge.

    Drives the global pathological-AST fixture
    `tests/conformance/inputs/emitter_edges/pathological.json` through
    the Lua Pcre2Emitter and asserts each safety guard fires:
      1. Variable-Length Lookbehind Rejection — STRlingCompilationError
      2. AST Depth Limit Exceeded             — STRlingCompilationError
      3. ReDoS Risk Warning (`(a+)+`)         — non-fatal STRlingWarning

    The local `astToIr` mirrors the TypeScript bridge so the test
    targets the emitter without coupling to the parser/compiler stages.
    Keep it minimal — supporting only node types currently appearing in
    `pathological.json` — so adapter omissions cannot mask emitter bugs
    by silently dropping nodes.
]]

local pcre2 = require("src.pcre2")
local json = require("cjson")

local function find_fixture()
    local function exists(p)
        local f = io.open(p, "r")
        if f then f:close(); return true end
        return false
    end
    -- Tests run with cwd = bindings/lua/spec under busted; climb to root.
    local candidates = {
        "../../../tests/conformance/inputs/emitter_edges/pathological.json",
        "../../tests/conformance/inputs/emitter_edges/pathological.json",
        "tests/conformance/inputs/emitter_edges/pathological.json",
    }
    for _, p in ipairs(candidates) do
        if exists(p) then return p end
    end
    error("could not locate pathological.json from cwd")
end

local function ast_to_ir(node)
    local t = node.type
    if t == "Literal" then
        return { ir = "Lit", value = tostring(node.value or "") }
    elseif t == "Group" then
        return { ir = "Group", capturing = false, body = ast_to_ir(node.content) }
    elseif t == "Quantifier" then
        local raw_max = node.max
        -- nil/null in the user-facing AST means unbounded → IR sentinel "Inf".
        local max
        if raw_max == nil or raw_max == json.null then
            max = "Inf"
        else
            max = raw_max
        end
        return {
            ir = "Quant",
            child = ast_to_ir(node.content),
            min = node.min or 0,
            max = max,
            mode = "Greedy",
        }
    elseif t == "Lookbehind" then
        return { ir = "Look", dir = "Behind", neg = false, body = ast_to_ir(node.content) }
    elseif t == "NegativeLookbehind" then
        return { ir = "Look", dir = "Behind", neg = true, body = ast_to_ir(node.content) }
    elseif t == "Lookahead" then
        return { ir = "Look", dir = "Ahead", neg = false, body = ast_to_ir(node.content) }
    elseif t == "NegativeLookahead" then
        return { ir = "Look", dir = "Ahead", neg = true, body = ast_to_ir(node.content) }
    end
    error("ast_to_ir: unsupported pathological AST node type \"" .. tostring(t) ..
        "\". Extend the adapter when new pathological vectors are added.")
end

local function expected_substring(prefixed)
    if prefixed:sub(1, #"STRlingCompilationError:") == "STRlingCompilationError:" then
        return prefixed:sub(#"STRlingCompilationError:" + 1):gsub("^%s+", "")
    end
    if prefixed:sub(1, #"STRlingWarning") == "STRlingWarning" then
        local idx = prefixed:find("]")
        if idx then
            return prefixed:sub(idx + 1):gsub("^[: ]+", "")
        end
    end
    return prefixed
end

describe("Emitter Edges Conformance (pathological.json)", function()
    local f = io.open(find_fixture(), "r")
    local raw = f:read("*a")
    f:close()
    local doc = json.decode(raw)

    it("fixture is non-empty", function()
        assert.is_truthy(doc.tests and #doc.tests > 0)
    end)

    for _, tc in ipairs(doc.tests) do
        local name = tc.name or "<unnamed>"
        it(name, function()
            local ir = ast_to_ir(tc.ast)
            local max_depth = tc.depth_override_for_test or 0

            if tc.expected_error then
                local needle = expected_substring(tonumber(tc.expected_error) and tostring(tc.expected_error) or tc.expected_error)
                local ok, err = pcall(function()
                    pcre2.emitWithDiagnostics(ir, nil, max_depth)
                end)
                assert.is_false(ok, "[" .. name .. "] expected STRlingCompilationError")
                local msg = (type(err) == "table" and err.message) or tostring(err)
                assert.is_truthy(string.find(msg, needle, 1, true),
                    "[" .. name .. "] expected substring \"" .. needle .. "\" in \"" .. msg .. "\"")
            elseif tc.expected_warning then
                local needle = expected_substring(tc.expected_warning)
                local result = pcre2.emitWithDiagnostics(ir, nil, max_depth)
                -- Warnings must NOT abort emission — pattern is still produced.
                assert.is_truthy(result.pattern and #result.pattern > 0,
                    "[" .. name .. "] expected non-empty pattern when only a warning fires")
                local hit = false
                for _, w in ipairs(result.warnings) do
                    if w.code == "REDOS_RISK" and string.find(w.message, needle, 1, true) then
                        hit = true; break
                    end
                end
                assert.is_true(hit, "[" .. name .. "] missing REDOS_RISK warning containing \"" .. needle .. "\"")
            else
                error("[" .. name .. "] declares neither expected_error nor expected_warning")
            end
        end)
    end
end)

describe("Emitter Edges — negative controls", function()
    it("non-pathological emits no warnings", function()
        local result = pcre2.emitWithDiagnostics({ ir = "Lit", value = "abc" })
        assert.are.equal("abc", result.pattern)
        assert.are.equal(0, #result.warnings)
    end)

    it("depth cap does not fire under limit", function()
        local ir = {
            ir = "Group", capturing = false,
            body = { ir = "Group", capturing = false, body = { ir = "Lit", value = "ok" } },
        }
        local result = pcre2.emitWithDiagnostics(ir, nil, 5)
        assert.are.equal(0, #result.warnings)
        assert.is_truthy(string.find(result.pattern, "ok", 1, true))
    end)
end)
