from STRling import simply as s
import re


####################
# Range Feature
####################

# Most methods allow the `min_rep` and `max_rep` to be passed in directly or after params.
# For example, s.group('my_group_name', simply.letter(1, 2), simply.digit(1, 2)).
# All methods allow to set by reinvoking with the range if one hasn't already been set.
# For example, simply.letter()(1, 2) is the same as simply.letter(1, 2).
# This is especially handy for functions that take an unknown number of parameters.
# For example, s.group('my_group_name', simply.letter(1, 2), simply.digit(1, 2)).
# This cannot be passed the range directly because it will think you want the numbers in the group.
# Instead, pass them in after: s.group('my_group_name', simply.letter(1, 2), simply.digit(1, 2))(1, 2).
# Notice now the range is clearly not part of the group, but does assign the range correctly.


####################
# Custom Literals
####################

# Creates a matching pattern from a regular string
s.lit('$%')  # Matches the literal characters '$' or '%'.

####################
# Character Sets
####################

# Note: Each character set below has a negated counterpart.
# For example, simply.letter() => simply.not_letter()

s.letter()      # Matches any letter (uppercase or lowercase).
s.upper()       # Matches any uppercase letter.
s.lower()       # Matches any lowercase letter.
s.digit()       # Matches any digit.
s.whitespace()  # Matches any whitespace character (space, tab, newline, carriage return, etc.).
s.newline()     # Matches a newline character.
s.tab()         # Matches a tab character.
s.carriage()    # Matches a carriage return character.
s.bound()       # Matches a boundary character.

####################
# Custom Sets
####################

# Note: Each custom set below has a negated counterpart.
# For example, simply.between() => simply.not_between()

# Matches all characters within and including the start and end of a letter or number range.
s.between(0, 9)      # Matches any digit from 0 to 9.
s.between('a', 'z')  # Matches any lowercase letter from 'a' to 'z'.
s.between('A', 'Z')  # Matches any uppercase letter from 'A' to 'Z'.

# Matches any characters in the provided set.
s.in_(s.letter(), s.digit(), s.lit(',.'))  # Matches letters, digits, commas, and periods.
# You may notice a resemblance between simply.in_() and simply.any_of().
# Key distinctions:
#   - simply.in_() typically processes faster than simply.any_of().
#   - simply.any_of() can process composite patterns while simply.in_() cannot.
# A composite pattern is one consisting of smaller combined patterns.

####################
# Anchors
####################

s.start()  # Matches the start of a line.
# There is no `simply.not_start()` function.
# Instead, use `simply.not_behind(simply.start())`.

s.end()  # Matches the end of a line.
# There is no `simply.not_end()` function.
# Instead, use `simply.not_ahead(simply.end())`.

####################
# Constructors
####################

s.any_of()  # Matches any one of the provided patterns.
# You may notice a resemblance between simply.in_() and simply.any_of().
# Key distinctions:
#   - simply.in_() typically processes faster than simply.any_of().
#   - simply.any_of() can process composite patterns while simply.in_() cannot.
# A composite pattern is one consisting of smaller combined patterns.
s.any_of(pattern1, pattern2) # Matches only if one of the patterns listed is present.


s.may()  # Optionally matches the provided patterns.
# If a `may` pattern isn't there, it still will match the rest of the patterns.
# In the text, "ABC2" the patter below matches ['A', 'B', 'C2']
s.merge(s.letter(), s.may(s.digit()))


s.merge()  # Combines multiple patterns into one larger pattern.
# You can see this used for the method above.


s.capture()  # Creates a numbered group that can be indexed for extracting part of a match later.
# Capture is used the same as merge.
s.capture(s.letter(), s.digit())


s.group()  # Creates a named group that can be referenced for extracting part of a match.
# group is used the same as merge and capture but it takes a string name as the first argument.
s.group('my_group', s.letter(), s.digit())
# Unlike merge and capture, merge cannot be repeated.
# This is because group names must be unique in a pattern.

####################
# Lookarounds
####################

# Note: Each lookaround below has a negated counterpart.
# For example, simply.ahead() => simply.not_ahead()

# These verify a pattern is or isn't ahead or behind
# without capturing it as part of the pattern matched.

s.ahead()  # Only matches the rest of a pattern if the provided pattern is ahead.
# For example, in the text "123ABC", the pattern below matches 3 but not 1 or 2.
s.merge(s.digit(), s.ahead(s.letter()))  # Only matches a digit followed by a letter.

s.behind()  # Only matches the rest of a pattern if the provided pattern is behind.
# For example, in the text "123ABC", the pattern below matches A but not B or C.
s.merge(s.behind(s.digit()), s.letter())  # Only matches a letter preceded by a digit.
