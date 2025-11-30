require_relative 'lib/strling'

# Using the Simply Fluent API
s = Strling::Simply

pattern = s.merge(
  s.start,
  s.capture(s.digit.times(3)),
  s.may(s.any_of('-', '.', ' ')),
  s.capture(s.digit.times(3)),
  s.may(s.any_of('-', '.', ' ')),
  s.capture(s.digit.times(4)),
  s.end
)

puts pattern.to_s
