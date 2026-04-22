# frozen_string_literal: true

require_relative 'simply'

module Strling
  # Standard library: canonical, RFC-grounded patterns for the most commonly
  # validated string formats.
  #
  # Each helper composes existing Simply primitives so the compiled output
  # flows through the standard pipeline and no raw regex leaks into the
  # public API.
  module Essential
    module_function

    def self.letter_items
      [
        Strling::Nodes::Range.new(from: 'A', to: 'Z'),
        Strling::Nodes::Range.new(from: 'a', to: 'z')
      ]
    end

    def self.digit_items
      [Strling::Nodes::Escape.new(kind: 'digit')]
    end

    def self.hex_items
      [
        Strling::Nodes::Range.new(from: 'A', to: 'F'),
        Strling::Nodes::Range.new(from: 'a', to: 'f'),
        Strling::Nodes::Range.new(from: '0', to: '9')
      ]
    end

    def self.chars_items(s)
      s.chars.map { |c| Strling::Nodes::Literal.new(value: c) }
    end

    def self.class_of(items, min, max)
      class_node = Strling::Nodes::CharacterClass.new(negated: false, members: items)
      if min == 1 && max == 1
        Strling::Simply.new(class_node)
      else
        max_val = max.nil? ? 'Inf' : max
        Strling::Simply.new(Strling::Core::Quant.new(class_node, min, max_val, 'Greedy'))
      end
    end

    def self.dig_n(min, max)  = class_of(digit_items,  min, max)
    def self.hex_n(min, max)  = class_of(hex_items,    min, max)
    def self.lett_n(min, max) = class_of(letter_items, min, max)

    def self.lit(s)
      Strling::Simply.new(Strling::Core::Lit.new(s))
    end

    def self.opt(pattern)
      body = pattern.is_a?(Strling::Simply) ? pattern.node : pattern
      grouped = Strling::Core::Group.new(false, body)
      Strling::Simply.new(Strling::Core::Quant.new(grouped, 0, 1, 'Greedy'))
    end

    def self.alt(branches)
      nodes = branches.map(&:node)
      Strling::Simply.new(Strling::Core::Alt.new(nodes))
    end

    def self.seq(parts)
      Strling::Simply.merge(*parts)
    end

    # Matches an email address (RFC 5322 addr-spec, basic structure).
    def self.email
      local  = class_of(letter_items + digit_items + chars_items('._%+-'), 1, nil)
      domain = class_of(letter_items + digit_items + chars_items('.-'),    1, nil)
      tld    = lett_n(2, nil)
      seq([local, lit('@'), domain, lit('.'), tld])
    end

    # Matches an HTTP or HTTPS URL (RFC 3986 generic syntax).
    def self.url
      base       = letter_items + digit_items + chars_items("/_-.~%&=:@!$'()*+,;")
      with_q     = base + chars_items('?')
      with_frag  = with_q + chars_items('#')

      scheme   = seq([lit('http'), opt(lit('s'))])
      host     = class_of(letter_items + digit_items + chars_items('.-'), 1, nil)
      port     = opt(seq([lit(':'), dig_n(1, nil)]))
      path     = opt(seq([lit('/'), class_of(base, 0, nil)]))
      query    = opt(seq([lit('?'), class_of(with_q, 0, nil)]))
      fragment = opt(seq([lit('#'), class_of(with_frag, 0, nil)]))
      seq([scheme, lit('://'), host, port, path, query, fragment])
    end

    # Matches a UUID (RFC 4122). Pass version: 4 for v4-specific validation.
    def self.uuid(version = 0)
      dash = -> { lit('-') }
      if version == 4
        variant = class_of(chars_items('89ABab'), 1, 1)
        return seq([
          hex_n(8, 8),  dash.call,
          hex_n(4, 4),  dash.call,
          lit('4'), hex_n(3, 3), dash.call,
          variant, hex_n(3, 3), dash.call,
          hex_n(12, 12)
        ])
      end
      seq([
        hex_n(8, 8),  dash.call,
        hex_n(4, 4),  dash.call,
        hex_n(4, 4),  dash.call,
        hex_n(4, 4),  dash.call,
        hex_n(12, 12)
      ])
    end

    # Matches an IPv4 (RFC 791) or full-form IPv6 (RFC 4291) address.
    def self.ip(version = 0)
      ipv4 = lambda do
        seq([
          dig_n(1, 3), lit('.'),
          dig_n(1, 3), lit('.'),
          dig_n(1, 3), lit('.'),
          dig_n(1, 3)
        ])
      end
      ipv6 = lambda do
        seq([
          hex_n(1, 4), lit(':'),
          hex_n(1, 4), lit(':'),
          hex_n(1, 4), lit(':'),
          hex_n(1, 4), lit(':'),
          hex_n(1, 4), lit(':'),
          hex_n(1, 4), lit(':'),
          hex_n(1, 4), lit(':'),
          hex_n(1, 4)
        ])
      end
      case version
      when 4 then ipv4.call
      when 6 then ipv6.call
      else        alt([ipv4.call, ipv6.call])
      end
    end

    # Matches an ISO 8601 / RFC 3339 datetime.
    def self.date_time
      sign   = class_of(chars_items('+-'), 1, 1)
      frac   = seq([lit('.'), dig_n(1, nil)])
      offset = seq([sign, dig_n(2, 2), lit(':'), dig_n(2, 2)])
      seq([
        dig_n(4, 4), lit('-'), dig_n(2, 2), lit('-'), dig_n(2, 2),
        lit('T'),
        dig_n(2, 2), lit(':'), dig_n(2, 2), lit(':'), dig_n(2, 2),
        opt(frac),
        opt(alt([lit('Z'), offset]))
      ])
    end
  end
end
