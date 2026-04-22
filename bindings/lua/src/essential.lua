-- STRling Essential — canonical, RFC-grounded patterns for the most
-- commonly validated string formats.
--
-- Each helper composes existing primitives so the compiled output flows
-- through the standard pipeline and no raw regex leaks into the public API.

local essential = {}

local function letter_items()
  return {
    { type = "Range", from = "A", to = "Z" },
    { type = "Range", from = "a", to = "z" },
  }
end

local function digit_items()
  return { { type = "Escape", kind = "digit" } }
end

local function hex_items()
  return {
    { type = "Range", from = "A", to = "F" },
    { type = "Range", from = "a", to = "f" },
    { type = "Range", from = "0", to = "9" },
  }
end

local function chars_items(s)
  local out = {}
  for i = 1, #s do
    table.insert(out, { type = "Literal", value = s:sub(i, i) })
  end
  return out
end

local function class_of(items, min, max)
  local cc = { type = "CharacterClass", negated = false, members = items }
  if max ~= nil and min == 1 and max == 1 then
    return cc
  end
  return {
    type = "Quantifier", min = min, max = max, greedy = true,
    target = cc,
  }
end

local function dig_n(min, max)  return class_of(digit_items(),  min, max) end
local function hex_n(min, max)  return class_of(hex_items(),    min, max) end
local function lett_n(min, max) return class_of(letter_items(), min, max) end

local function lit(s) return { type = "Literal", value = s } end

local function opt(node)
  local grouped = { type = "Group", capturing = false, body = node, name = nil, atomic = false }
  return {
    type = "Quantifier", min = 0, max = 1, greedy = true,
    target = grouped,
  }
end

local function alt_of(branches)
  return { type = "Alternation", alternatives = branches }
end

local function seq_of(parts)
  return { type = "Sequence", parts = parts }
end

local function concat(...)
  local out = {}
  for _, t in ipairs({...}) do
    for _, v in ipairs(t) do table.insert(out, v) end
  end
  return out
end

-- Matches an email address (RFC 5322 addr-spec, basic structure).
function essential.email()
  local local_  = class_of(concat(letter_items(), digit_items(), chars_items('._%+-')), 1, nil)
  local domain  = class_of(concat(letter_items(), digit_items(), chars_items('.-')),    1, nil)
  local tld     = lett_n(2, nil)
  return seq_of({local_, lit('@'), domain, lit('.'), tld})
end

-- Matches an HTTP or HTTPS URL (RFC 3986 generic syntax).
function essential.url()
  local base      = concat(letter_items(), digit_items(), chars_items("/_-.~%&=:@!$'()*+,;"))
  local with_q    = concat(base, chars_items('?'))
  local with_frag = concat(with_q, chars_items('#'))

  local scheme   = seq_of({lit('http'), opt(lit('s'))})
  local host     = class_of(concat(letter_items(), digit_items(), chars_items('.-')), 1, nil)
  local port     = opt(seq_of({lit(':'), dig_n(1, nil)}))
  local path     = opt(seq_of({lit('/'), class_of(base,      0, nil)}))
  local query    = opt(seq_of({lit('?'), class_of(with_q,    0, nil)}))
  local fragment = opt(seq_of({lit('#'), class_of(with_frag, 0, nil)}))
  return seq_of({scheme, lit('://'), host, port, path, query, fragment})
end

-- Matches a UUID (RFC 4122). Pass version=4 for v4-specific validation.
function essential.uuid(version)
  version = version or 0
  if version == 4 then
    local variant = class_of(chars_items('89ABab'), 1, 1)
    return seq_of({
      hex_n(8, 8), lit('-'),
      hex_n(4, 4), lit('-'),
      lit('4'), hex_n(3, 3), lit('-'),
      variant, hex_n(3, 3), lit('-'),
      hex_n(12, 12),
    })
  end
  return seq_of({
    hex_n(8, 8), lit('-'),
    hex_n(4, 4), lit('-'),
    hex_n(4, 4), lit('-'),
    hex_n(4, 4), lit('-'),
    hex_n(12, 12),
  })
end

-- Matches an IPv4 (RFC 791) or full-form IPv6 (RFC 4291) address.
function essential.ip(version)
  version = version or 0
  local function ipv4()
    return seq_of({
      dig_n(1, 3), lit('.'),
      dig_n(1, 3), lit('.'),
      dig_n(1, 3), lit('.'),
      dig_n(1, 3),
    })
  end
  local function ipv6()
    return seq_of({
      hex_n(1, 4), lit(':'),
      hex_n(1, 4), lit(':'),
      hex_n(1, 4), lit(':'),
      hex_n(1, 4), lit(':'),
      hex_n(1, 4), lit(':'),
      hex_n(1, 4), lit(':'),
      hex_n(1, 4), lit(':'),
      hex_n(1, 4),
    })
  end
  if version == 4 then return ipv4() end
  if version == 6 then return ipv6() end
  return alt_of({ipv4(), ipv6()})
end

-- Matches an ISO 8601 / RFC 3339 datetime.
function essential.date_time()
  local sign   = class_of(chars_items('+-'), 1, 1)
  local frac   = seq_of({lit('.'), dig_n(1, nil)})
  local offset = seq_of({sign, dig_n(2, 2), lit(':'), dig_n(2, 2)})
  return seq_of({
    dig_n(4, 4), lit('-'), dig_n(2, 2), lit('-'), dig_n(2, 2),
    lit('T'),
    dig_n(2, 2), lit(':'), dig_n(2, 2), lit(':'), dig_n(2, 2),
    opt(frac),
    opt(alt_of({lit('Z'), offset})),
  })
end

return essential
