local strling = {}
local json = require("cjson")

local simply
local status, mod = pcall(require, "strling.simply")
if status then
  simply = mod
else
  -- Fallback for local development where files are in src/
  simply = require("src.simply")
end
strling.simply = simply

local function val_or_nil(v)
  if v == json.null then return nil end
  return v
end

local function compile_node(node)
  if not node then return nil end
  
  if node.type == "Literal" then
    return { ir = "Lit", value = node.value }
    
  elseif node.type == "Sequence" then
    local parts = {}
    if node.parts then
      for _, p in ipairs(node.parts) do
        local compiled = compile_node(p)
        if compiled then
            local prev = parts[#parts]
            if prev and prev.ir == "Lit" and compiled.ir == "Lit" then
               prev.value = prev.value .. compiled.value
            else
               table.insert(parts, compiled)
            end
        end
      end
    end
    if #parts == 1 then
      return parts[1]
    end
    return { ir = "Seq", parts = parts }
    
  elseif node.type == "CharacterClass" then
    local items = {}
    if node.members then
      for _, m in ipairs(node.members) do
        if m.type == "Literal" then
          table.insert(items, { ir = "Char", char = m.value })
        elseif m.type == "Range" then
           table.insert(items, { 
               ir = "Range", 
               from = m.from, 
               to = m.to 
           })
        elseif m.type == "Escape" then
           table.insert(items, compile_node(m))
        elseif m.type == "UnicodeProperty" then
           table.insert(items, compile_node(m))
        else
          table.insert(items, compile_node(m))
        end
      end
    end
    return { ir = "CharClass", negated = node.negated, items = items }
    
  elseif node.type == "Quantifier" then
    local mode = "Greedy"
    if node.possessive then
      mode = "Possessive"
    elseif not node.greedy then
      mode = "Lazy"
    end
    
    local max = val_or_nil(node.max)
    if max == nil then max = "Inf" end
    
    return {
      ir = "Quant",
      min = node.min,
      max = max,
      mode = mode,
      child = compile_node(node.target)
    }
    
  elseif node.type == "Group" then
    local atomic = node.atomic
    if atomic == false then atomic = nil end
    return {
      ir = "Group",
      capturing = node.capturing,
      atomic = atomic,
      name = val_or_nil(node.name),
      body = compile_node(node.body)
    }
    
  elseif node.type == "Alternation" then
    local branches = {}
    if node.alternatives then
      for _, a in ipairs(node.alternatives) do
        table.insert(branches, compile_node(a))
      end
    end
    return { ir = "Alt", branches = branches }
    
  elseif node.type == "Anchor" then
    local at = node.at
    if at == "NonWordBoundary" then at = "NotWordBoundary" end
    return { ir = "Anchor", at = at }
    
  elseif node.type == "Dot" then
    return { ir = "Dot" }
    
  elseif node.type == "Escape" then
     if node.kind == "unicode_property" then
        local t = "p"
        if node.negated then t = "P" end
        return { ir = "Esc", type = t, property = node.property }
     end
     
     local map = {
       digit = "d", ["not-digit"] = "D",
       space = "s", ["not-space"] = "S",
       word = "w", ["not-word"] = "W"
     }
     if map[node.kind] then
       return { ir = "Esc", type = map[node.kind] }
     end

     return { ir = "Esc", type = "Unknown", property = node.kind }

  elseif node.type == "UnicodeProperty" then
    local t = "p"
    if node.negated then t = "P" end
    return { ir = "Esc", type = t, property = node.value }

  elseif node.type == "Backreference" then
    local res = { ir = "Backref" }
    local name = val_or_nil(node.name)
    if name then
      res.byName = name
    else
      res.byIndex = node.index
    end
    return res

  elseif node.type == "Lookahead" then
    return { ir = "Look", dir = "Ahead", neg = false, body = compile_node(node.body) }
  elseif node.type == "NegativeLookahead" then
    return { ir = "Look", dir = "Ahead", neg = true, body = compile_node(node.body) }
  elseif node.type == "Lookbehind" then
    return { ir = "Look", dir = "Behind", neg = false, body = compile_node(node.body) }
  elseif node.type == "NegativeLookbehind" then
    return { ir = "Look", dir = "Behind", neg = true, body = compile_node(node.body) }
  end
  
  return { ir = "Unknown", type = node.type }
end

function strling.compile(json_ast)
  return compile_node(json_ast)
end

return strling
