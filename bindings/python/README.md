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

### Documentation - Developmental Guide

Here's a quick example to demonstrate how easy it is to get started with STRling:

```python
import re
from STRling import lit, group, merge, templates as tmp


##########################################################
## Here are some real implementations of STRling syntax ##
##########################################################

phones_in_usa = tmp.phone_number_US
"""
The matched formats include:
- No Delimiters: 1234567890
- All Groups Separated:
    - 123 456 7890
    - 123-456-7890
    - 123.456.7890
- Grouped Area Code:
    - (123) 456 7890
    - (123) 456-7890
    - (123) 456.7890
"""
# As you can see, we have very complex templates already created,
# so for the most cases you can forget about even crafting patterns.


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
special1 = lib.group('word', lib.letter() + lib.may(letter_num()))
# special1 is equivalent to the RegEx (?P<word>[A-Za-z](?:\d[A-Za-z])?)


first = group('first', lib.digit(3)) # (?P<first>\d{3})
second = group('second', lib.digit(3)) # (?P<second>\d{3})
third = group('third', lib.digit(4)) # (?P<third>\d{4})
h = lib.lit('-') # \-

phone_pattern = lib.group('phone', first + h + second + h + third)
# phone_pattern is equivalent to the RegEx pattern below
# (?P<phone>(?P<first>\d{3})\-(?P<second>\d{3})\-(?P<third>\d{4}))

# Sample string containing phone numbers
text = "Here are some phone numbers: 987-654-3210, 123-456-7890."

# Using the re package to search for the phone number pattern
matches = re.finditer(phone_pattern, text)

# Displaying the matches
for match in matches:
    print('Match Index Range:', match.span())
    print('"first" group:', match.group('first'))
    print('"second" group:', match.group('second'))
    print('"third" group:', match.group('third'))
    print('"phone" group:', match.group('phone'))

# Match Index Range: (29, 41)
# "first" group: 987
# "second" group: 654
# "third" group: 3210
# "phone" group: 987-654-3210

# Match Index Range: (43, 55)
# "first" group: 123
# "second" group: 456
# "third" group: 7890
# "phone" group: 123-456-7890



##############################################################
## Here are all the lib methods with their equivalent RegEx ##
##############################################################

# Matches the literal provided string (no symbols or variables)
lib.lit('\s t*') # \\s\st\*

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

Simplify your string validation and matching tasks with STRling, the all-in-one solution for developers who need powerful yet user-friendly tools for working with strings. Download and start using STRling today!

---

To learn more about STRling, checkout [STRling on PyPI](https://pypi.org/project/STRling/) and [STRling on GitHub](https://github.com/TheCyberLocal/STRling).

To learn more about me, checkout [My LinkedIn](https://www.linkedin.com/in/tzm01/).

To learn more about traditional RegEx syntax, checkout [My RegEx Docs](https://github.com/TheCyberLocal/styled-coding-notes/blob/main/regEx.md).
