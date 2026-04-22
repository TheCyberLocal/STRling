--[[
    STRling Diagnostics — Safety Guards

    Provides the cross-binding diagnostic types raised and surfaced by
    the emitter when a pattern would compile to something dangerous
    (variable length lookbehind, host-stack-exhausting depth, or
    catastrophic backtracking risk). Mirrors the SSOT in
    `bindings/typescript/`.
]]

local M = {}

-- Fatal emitter-stage failure raised by an IR safety guard. Carries a
-- stable `code` (`VLB_NOT_SUPPORTED`, `MAX_DEPTH`) and the offending
-- `engine` so cross-binding parity tests can match on shared substrings
-- without coupling to a specific message wording.
local STRlingCompilationError = {}
STRlingCompilationError.__index = STRlingCompilationError

function STRlingCompilationError.new(message, code, engine)
    local self = setmetatable({}, STRlingCompilationError)
    self.message = message
    self.code = code
    self.engine = engine or "pcre2"
    return self
end

function STRlingCompilationError:__tostring()
    return "STRlingCompilationError: " .. tostring(self.message)
end

-- Non-fatal diagnostic. `__tostring` matches the SSOT format
-- `STRlingWarning [CODE]: message` so the global pathological fixture's
-- `expected_warning` substring compares 1:1 across bindings.
local STRlingWarning = {}
STRlingWarning.__index = STRlingWarning

function STRlingWarning.new(code, message)
    local self = setmetatable({}, STRlingWarning)
    self.code = code
    self.message = message
    return self
end

function STRlingWarning:__tostring()
    return "STRlingWarning [" .. tostring(self.code) .. "]: " .. tostring(self.message)
end

-- Result of an emit pass: produced PCRE2 pattern + non-fatal warnings.
local CompileResult = {}
CompileResult.__index = CompileResult

function CompileResult.new(pattern, warnings)
    local self = setmetatable({}, CompileResult)
    self.pattern = pattern
    self.warnings = warnings or {}
    return self
end

M.STRlingCompilationError = STRlingCompilationError
M.STRlingWarning = STRlingWarning
M.CompileResult = CompileResult

return M
