--[[
    STRling PCRE2 Emitter - Lua Implementation

    Transforms STRling IR into PCRE2-compatible regex strings.
    Iron Law: Emitters are pure functions with signature emit(ir, flags) → string.
]]

local diagnostics = require("src.diagnostics")
local STRlingCompilationError = diagnostics.STRlingCompilationError
local STRlingWarning = diagnostics.STRlingWarning
local CompileResult = diagnostics.CompileResult

local Pcre2Emitter = {}
Pcre2Emitter.__index = Pcre2Emitter

-- Default upper bound on IR nesting depth before the emitter aborts.
-- Mirrors the SSOT in the TypeScript reference.
Pcre2Emitter.DEFAULT_MAX_DEPTH = 250

local REDOS_MESSAGE =
    "The pattern contains overlapping alternations or nested unbounded "
 .. "quantifiers (e.g., (a+)+). This can lead to catastrophic backtracking "
 .. "and exponential CPU spikes. Consider using possessive quantifiers "
 .. "(++ or *+) or atomic groups to guarantee execution safety."

-- Special characters that need escaping in PCRE2 literals
local LITERAL_SPECIAL = "[\\]^$.|?*+(){}"

-- Special characters inside character class
local CLASS_SPECIAL = "[\\]^-"

-- Check if character is in special set
local function contains(str, ch)
    return str:find(ch, 1, true) ~= nil
end

-- Escape a literal string for use outside character classes
local function escapeLiteral(s)
    local buf = {}
    for ch in s:gmatch(".") do
        if contains(LITERAL_SPECIAL, ch) then
            table.insert(buf, "\\")
        end
        table.insert(buf, ch)
    end
    return table.concat(buf)
end

-- Escape a character for use inside character classes
local function escapeClassChar(ch)
    if contains(CLASS_SPECIAL, ch) then
        return "\\" .. ch
    end
    return ch
end

function Pcre2Emitter.new(maxDepth)
    local self = setmetatable({}, Pcre2Emitter)
    self._depth = 0
    self._maxDepth = (maxDepth and maxDepth > 0) and maxDepth or Pcre2Emitter.DEFAULT_MAX_DEPTH
    self._inLookbehind = false
    self._warnings = {}
    return self
end

-- --- Safety predicates ---------------------------------------------------

local function isUnboundedQuant(node)
    return node.max == "Inf" or node.max == nil
end

local function isVariableLengthQuant(node)
    if isUnboundedQuant(node) then return true end
    return node.max ~= node.min
end

local isFixedLengthBody
local hasNestedUnboundedQuant

-- Mirror of `_isFixedLengthBody` in the TS SSOT.
function isFixedLengthBody(node)
    local t = node.ir
    if t == "Quant" then
        return (not isVariableLengthQuant(node)) and isFixedLengthBody(node.child)
    elseif t == "Seq" then
        for _, p in ipairs(node.parts) do
            if not isFixedLengthBody(p) then return false end
        end
        return true
    elseif t == "Alt" then
        for _, b in ipairs(node.branches) do
            if not isFixedLengthBody(b) then return false end
        end
        return true
    elseif t == "Group" then
        return isFixedLengthBody(node.body)
    elseif t == "Look" then
        return true
    end
    return true
end

-- Mirror of `_hasNestedUnboundedQuant`.
function hasNestedUnboundedQuant(node)
    local t = node.ir
    if t == "Quant" then
        return isUnboundedQuant(node)
    elseif t == "Group" then
        return hasNestedUnboundedQuant(node.body)
    elseif t == "Seq" then
        return #node.parts == 1 and hasNestedUnboundedQuant(node.parts[1])
    elseif t == "Alt" then
        for _, b in ipairs(node.branches) do
            if hasNestedUnboundedQuant(b) then return true end
        end
        return false
    end
    return false
end

function Pcre2Emitter:pushReDoSWarning()
    for _, w in ipairs(self._warnings) do
        if w.code == "REDOS_RISK" then return end
    end
    table.insert(self._warnings, STRlingWarning.new("REDOS_RISK", REDOS_MESSAGE))
end

function Pcre2Emitter:emit(ir, flags)
    local irType = ir.ir
    self._depth = self._depth + 1
    if self._depth > self._maxDepth then
        self._depth = self._depth - 1
        error(STRlingCompilationError.new(
            "Maximum AST depth exceeded (limit: " .. self._maxDepth .. "). "
         .. "This pattern is too deeply nested and risks host stack "
         .. "exhaustion during emission. Refactor the pattern to reduce "
         .. "nesting, or flatten capturing groups where possible.",
            "MAX_DEPTH"
        ))
    end
    local ok, result = pcall(function()
        if irType == "Lit" then
            return self:emitLit(ir)
        elseif irType == "Seq" then
            return self:emitSeq(ir)
        elseif irType == "Alt" then
            return self:emitAlt(ir)
        elseif irType == "Group" then
            return self:emitGroup(ir)
        elseif irType == "Quant" then
            return self:emitQuant(ir)
        elseif irType == "CharClass" then
            return self:emitCharClass(ir)
        elseif irType == "Anchor" then
            return self:emitAnchor(ir)
        elseif irType == "Dot" then
            return "."
        elseif irType == "Backref" then
            return self:emitBackref(ir)
        elseif irType == "Look" then
            return self:emitLook(ir)
        elseif irType == "Esc" then
            return self:emitEsc(ir)
        else
            error("Unknown IR type: " .. tostring(irType))
        end
    end)
    self._depth = self._depth - 1
    if not ok then error(result) end
    return result
end

function Pcre2Emitter:emitLit(ir)
    return escapeLiteral(ir.value)
end

function Pcre2Emitter:emitSeq(ir)
    local parts = {}
    for _, p in ipairs(ir.parts) do
        table.insert(parts, self:emit(p))
    end
    return table.concat(parts)
end

function Pcre2Emitter:emitAlt(ir)
    local branches = {}
    for _, b in ipairs(ir.branches) do
        table.insert(branches, self:emit(b))
    end
    return table.concat(branches, "|")
end

function Pcre2Emitter:emitGroup(ir)
    local body = self:emit(ir.body)
    local capturing = ir.capturing
    local name = ir.name
    local atomic = ir.atomic

    if atomic then
        return "(?>" .. body .. ")"
    end
    if name then
        return "(?<" .. name .. ">" .. body .. ")"
    end
    if capturing then
        return "(" .. body .. ")"
    end
    return "(?:" .. body .. ")"
end

function Pcre2Emitter:emitQuant(ir)
    local child = ir.child
    local min = ir.min
    local max = ir.max
    local mode = ir.mode or "Greedy"

    -- ReDoS guard: only flag when the *outer* quantifier is itself
    -- unbounded. A bounded outer like `(a+){0,3}` cannot produce
    -- exponential backtracking on its own.
    if isUnboundedQuant(ir) and hasNestedUnboundedQuant(child) then
        self:pushReDoSWarning()
    end

    local childStr = self:emit(child)

    -- Check if we need parentheses
    local needsParens = self:needsQuantifierParens(child, childStr)
    if needsParens then
        childStr = "(?:" .. childStr .. ")"
    end

    -- Build quantifier suffix
    local quantStr
    if max == "Inf" or max == nil then
        if min == 0 then
            quantStr = "*"
        elseif min == 1 then
            quantStr = "+"
        else
            quantStr = "{" .. min .. ",}"
        end
    elseif min == max then
        if min == 0 then
            return ""  -- Matches nothing
        elseif min == 1 then
            quantStr = ""
        else
            quantStr = "{" .. min .. "}"
        end
    elseif min == 0 and max == 1 then
        quantStr = "?"
    else
        quantStr = "{" .. min .. "," .. max .. "}"
    end

    -- Add mode suffix
    if mode == "Lazy" then
        quantStr = quantStr .. "?"
    elseif mode == "Possessive" then
        quantStr = quantStr .. "+"
    end

    return childStr .. quantStr
end

function Pcre2Emitter:needsQuantifierParens(child, childStr)
    local irType = child.ir
    if irType == "Seq" then return true end
    if irType == "Alt" then return true end
    if irType == "Lit" then
        return #childStr > 1 and not childStr:match("^\\")
    end
    if irType == "Quant" then return true end
    return false
end

function Pcre2Emitter:emitCharClass(ir)
    local negated = ir.negated
    local items = ir.items

    -- Single-item shorthand optimization
    if #items == 1 then
        local item = items[1]
        local itemIr = item.ir

        if itemIr == "Esc" then
            local type_ = item.type

            -- Handle d, w, s with negation flipping
            if type_:match("^[dws]$") then
                if negated then
                    return "\\" .. type_:upper()
                end
                return "\\" .. type_
            end

            -- Handle D, W, S
            if type_:match("^[DWS]$") then
                if negated then
                    return "\\" .. type_:lower()
                end
                return "\\" .. type_
            end

            -- Handle \p{...} and \P{...}
            if type_ == "p" or type_ == "P" then
                local prop = item.property
                if prop then
                    local shouldNegate = negated ~= (type_ == "P")
                    local use = shouldNegate and "P" or "p"
                    return "\\" .. use .. "{" .. prop .. "}"
                end
            end
        end
    end

    -- Build bracket class
    local parts = {}
    local hasHyphen = false

    for _, item in ipairs(items) do
        local itemIr = item.ir

        if itemIr == "Char" then
            local ch = item.char
            if ch == "-" then
                hasHyphen = true
            else
                table.insert(parts, escapeClassChar(ch))
            end
        elseif itemIr == "Range" then
            local from = item.from
            local to = item.to
            table.insert(parts, escapeClassChar(from) .. "-" .. escapeClassChar(to))
        elseif itemIr == "Esc" then
            local type_ = item.type
            local prop = item.property
            if prop then
                table.insert(parts, "\\" .. type_ .. "{" .. prop .. "}")
            else
                table.insert(parts, "\\" .. type_)
            end
        end
    end

    -- Hyphen at start to avoid ambiguity
    local inner
    if hasHyphen then
        inner = "-" .. table.concat(parts)
    else
        inner = table.concat(parts)
    end

    local neg = negated and "^" or ""
    return "[" .. neg .. inner .. "]"
end

function Pcre2Emitter:emitAnchor(ir)
    local at = ir.at
    if at == "Start" then return "^" end
    if at == "End" then return "$" end
    if at == "WordBoundary" then return "\\b" end
    if at == "NotWordBoundary" then return "\\B" end
    if at == "AbsoluteStart" then return "\\A" end
    if at == "AbsoluteEnd" then return "\\z" end
    if at == "EndBeforeFinalNewline" then return "\\Z" end
    error("Unknown anchor type: " .. tostring(at))
end

function Pcre2Emitter:emitBackref(ir)
    local byIndex = ir.byIndex
    local byName = ir.byName

    if byName then
        return "\\k<" .. byName .. ">"
    end
    if byIndex then
        return "\\" .. byIndex
    end
    error("Backref must have byIndex or byName")
end

function Pcre2Emitter:emitLook(ir)
    local dir = ir.dir
    local neg = ir.neg

    -- Variable-length lookbehind guard: PCRE2 mandates a fixed-width
    -- lookbehind body. Detect the violation here so the user sees a
    -- Signpost-pattern error rather than an opaque PCRE2 compile failure
    -- leaking from the runtime.
    if dir == "Behind" and not isFixedLengthBody(ir.body) then
        error(STRlingCompilationError.new(
            "PCRE2 does not support variable-length lookbehinds. The "
         .. "lookbehind body contains a quantifier that makes its length "
         .. "unpredictable. Rewrite the assertion using a fixed-length "
         .. "range (e.g. `{1,8}` instead of `+`), or restructure the "
         .. "pattern using a Lookahead, or extract the quantified portion "
         .. "outside the assertion.",
            "VLB_NOT_SUPPORTED"
        ))
    end

    local wasInLb = self._inLookbehind
    if dir == "Behind" then self._inLookbehind = true end
    local body = self:emit(ir.body)
    self._inLookbehind = wasInLb

    if dir == "Ahead" then
        if neg then
            return "(?!" .. body .. ")"
        else
            return "(?=" .. body .. ")"
        end
    else
        if neg then
            return "(?<!" .. body .. ")"
        else
            return "(?<=" .. body .. ")"
        end
    end
end

function Pcre2Emitter:emitEsc(ir)
    local type_ = ir.type
    local prop = ir.property

    if prop then
        return "\\" .. type_ .. "{" .. prop .. "}"
    end
    return "\\" .. type_
end

-- Module exports
local M = {}
M.Pcre2Emitter = Pcre2Emitter
M.STRlingCompilationError = STRlingCompilationError
M.STRlingWarning = STRlingWarning
M.CompileResult = CompileResult
M.DEFAULT_MAX_DEPTH = Pcre2Emitter.DEFAULT_MAX_DEPTH

function M.emit(ir, flags)
    return M.emitWithDiagnostics(ir, flags).pattern
end

function M.emitWithDiagnostics(ir, flags, maxDepth)
    local emitter = Pcre2Emitter.new(maxDepth)
    local pattern = emitter:emit(ir, flags)
    return CompileResult.new(pattern, emitter._warnings)
end

return M
