local simply = {}

-- Helper to ensure we have an AST node
local function to_node(item)
  if type(item) == "string" then
    return { type = "Literal", value = item }
  end
  return item
end

function simply.merge(...)
  local args = {...}
  local parts = {}
  for _, v in ipairs(args) do
    table.insert(parts, to_node(v))
  end
  return { type = "Sequence", parts = parts }
end

function simply.any_of(...)
  local args = {...}
  local alternatives = {}
  for _, v in ipairs(args) do
    table.insert(alternatives, to_node(v))
  end
  return { type = "Alternation", alternatives = alternatives }
end

function simply.may(item)
  return {
    type = "Quantifier",
    min = 0,
    max = 1,
    greedy = true,
    body = to_node(item)
  }
end

function simply.capture(item)
  return {
    type = "Group",
    capturing = true,
    body = to_node(item),
    name = nil,
    atomic = false
  }
end

function simply.digit(count)
  local digit_node = {
    type = "CharacterClass",
    negated = false,
    members = {
      { type = "Escape", kind = "digit" }
    }
  }
  
  if count == nil then
    return digit_node
  end
  
  return {
    type = "Quantifier",
    min = count,
    max = count,
    greedy = true,
    body = digit_node
  }
end

return simply
