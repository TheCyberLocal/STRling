# STRling

## The Next Generation of Regular Expressions

STRling is a powerful next-generation syntax designed as a user interface for writing regular expressions (RegEx) with an object-oriented approach. STRling is a simpler syntax than RegEx while maintaining the same underlying power and flexibility, making string validation more intuitive and less error-prone. Best of all, STRling syntax substitutes valid RegEx patterns, making it fully compatible with all traditional RegEx libraries and methods.

### Why STRling?

STRling recognizes the cryptic nature of RegEx can be challenging and susceptibility to errors. We provide a well-structured syntax that promotes readability and maintainability, empowering developers to focus on application logic rather than wrestling over difficult development tools. Most of all, we aim for a reliable product, which is why we only depend on built-in Python libraries.


### STRling's Mission

Our mission is to make RegEx a distant and outdated syntax by abstracting the complexities of RegEx into a clean, readable, and powerful interface. We strive to simplify string operations and ensure that developers can focus on building their applications without the steep learning curve of traditional RegEx. The previous alternative to RegEx was to learn the string validation syntax specific to each user input library, but STRling aims to unify the disparate syntaxes found across various libraries and frameworks into one simple library using only built-in Python packages.

### Key Features

- **High-Level Template Validation**: Quickly and easily validate common patterns using our template library.
- **Low-Level Pattern Construction**: Build complex regex patterns using a readable and maintainable, object-oriented syntax.
- **Escaping RegEx Jargon**: No longer write RegEx using complex jargon.
- **Dependencies**: Depends solely on built-in python libraries, fostering dependability and compatibility.

### Installation

Install STRling via pip:

```sh
pip install STRling
```

### Documentation - Developmental Guide

Here's a quick example to demonstrate how easy it is to get started with STRling:

```python
import re
from STRling import lit, group, merge


##########################################################
## Here are some real implementations of STRling syntax ##
##########################################################

# Most invoked functions have the range ability
# after their positional arguments as lib.letter()

any_letter = lib.letter() # [A-Za-z]
exactly_four_letters = lib.letter(4) # [A-Za-z]{4}
two_to_six_letters = lib.letter(2, 6) # [A-Za-z]{2, 6}
two_or_more_letters = lib.letter(2, '') # [A-Za-z]{2,}

# Using ahead (e.g., match 'foo' only if followed by 'bar')
foo_if_bar = lib.lit('foo') + lib.ahead('bar') # foo(?=bar)

# Using lookbehind (e.g., match 'bar' only if preceded by 'foo')
bar_if_foo = lib.behind('foo') + lib.lit('bar') # (?<=foo)bar

# Using or_ (e.g., match either 'cat' or 'dog')
cat_or_dog = lib.or_(lib.lit('cat'), lib.lit('dog')) # (?:cat|dog)

# Creating a named group (e.g., capturing a word)
letter_num = merge(lib.digit(), lib.letter()) # (?:\d[A-Za-z])
special1 = lib.group('word', lib.letter() + lib.may(letter_num())) # (?P<word>[A-Za-z](?:\d[A-Za-z])?)


##############################################################
## Here are all the lib methods with their equivalent RegEx ##
##############################################################

# Matches the literal provided string (no symbols or variables)
lib.lit('-*') # \-\*

# Matches any character between and including the two provided
lib.between('A', 'D') # [A-D]

# Matches any character in the provided string
lib.in_('abc') # [abc]

# Matches any character not in the provided string
lib.not_in('abc') # [^abc]

# Matches any digit
lib.digit() # \d

# Matches any letter
lib.letter() # [A-Za-z]

# Matches any uppercase letter
lib.upper() # [A-Z]

# Matches any lowercase letter
lib.lower() # [a-z]

# Matches any character besides newline
lib.any() # .

# Matches a newline character
lib.newline() # \n

# Matches a tab character
lib.tab() # \t

# Matches a carriage return
lib.carriage() # \r

# Matches a boundary character
lib.bound() # \b

# Matches the start of the string
# Doesn't accept range params
lib.start() # ^

# Matches the end of the string
# Doesn't accept range params
lib.end() # $

# Matches only where the provided pattern is found ahead
# Doesn't accept range params
lib.ahead() # (?=pattern)

# Matches only where the provided pattern is found behind
# Doesn't accept range params
lib.behind() # (?<=pattern)

# Matches only where the provided pattern is not found ahead
# Doesn't accept range params
lib.not_ahead() # (?!pattern)

# Matches only where the provided pattern is not found behind
# Doesn't accept range params
lib.not_behind() # (?<!pattern)

# Matches any of the provided patterns
lib.or_() # pattern1 | pattern2

# Matches 1 otherwise 0 of the provided pattern
lib.may() # pattern?

# Groups the provided patterns with a name
group() # (?P<name>pattern1 pattern2)

# Groups the provided patterns without a name
merge() # (?:pattern1 pattern2)
```

### License

STRling is licensed under the MIT License. See the [LICENSE](https://github.com/TheCyberLocal/STRling/blob/main/LICENSE) file for more information.

---

Simplify your string validation and matching tasks with STRling, the all-in-one solution for developers who need powerful yet user-friendly tools for working with strings. Download and start using STRling today!

---

To learn more about STRling, checkout [STRling on PyPI](https://pypi.org/project/STRling/) and [STRling on GitHub](https://github.com/TheCyberLocal/STRling)

To learn more about traditional RegEx syntax, checkout my GitHub repo at [regEx.md](https://github.com/TheCyberLocal/styled-coding-notes/blob/main/regEx.md)
