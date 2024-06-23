# STRling

## The Next Generation of Regular Expressions

STRling is a powerful next-generation syntax designed as a user interface for writing regular expressions (RegEx) with an object-oriented approach. STRling recognizes the cryptic nature of RegEx can be challenging and susceptibility to errors, which is why STRling looks and feels nothing like RegEx, but it maintains the same power and flexibility, making string validation enjoyable rather than a hassle. Best of all, STRling syntax substitutes valid RegEx patterns, making it fully compatible with all traditional RegEx libraries and methods.

### Why STRling?

1. You need ZERO knowledge of RegEx jargon to create powerful and readable patterns.
2. STRling exclusively utilizes built-in python libraries, making it a reliable package.
3. Make your projects clear and consistent by using STRling rather than the individual library string validators that each have their own syntax (Sqlite3, Sequelize, Postgres, WTForms... etc.).
4. STRling has predefined templates for commonly used patterns, so forget about even writing our simple syntax for most cases. (phone number, email, url... etc.)

### STRling's Mission

Our mission is to make RegEx a distant and outdated syntax by abstracting the complexities of RegEx into a clean, readable, and powerful interface. We strive to simplify string operations and ensure that developers can focus on building their applications without the steep learning curve of traditional RegEx. The previous alternative to RegEx was to learn the string validation syntax specific to each user input library, but STRling aims to unify the disparate syntaxes found across various libraries and frameworks into one simple library using only built-in Python packages.

### Key Features

- **High-Level Template Validation**: Quickly and easily validate common patterns using our template library.
- **Low-Level Pattern Construction**: Build complex RegEx patterns using a readable and maintainable, object-oriented syntax.
- **Escaping RegEx Jargon**: No longer write RegEx using complex jargon.
- **Dependencies**: Depends solely on built-in python libraries, fostering dependability and compatibility.

### Installation

Install STRling via pip:

```sh
pip install STRling
```

---

# STRling Package Documentation
```python
from STRling import simply as s
import re

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
# This is similar to simply.in_(), except it can take in composite patterns.
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
```

Simplify your string validation and matching tasks with STRling, the all-in-one solution for developers who need powerful yet user-friendly tools for working with strings. Download and start using STRling today!

---

To learn more about STRling, checkout [STRling on PyPI](https://pypi.org/project/STRling/) and [STRling on GitHub](https://github.com/TheCyberLocal/STRling).

To learn more about me, checkout [My LinkedIn](https://www.linkedin.com/in/tzm01/).

To learn more about traditional RegEx syntax, checkout [My RegEx Docs](https://github.com/TheCyberLocal/styled-coding-notes/blob/main/regEx.md).
