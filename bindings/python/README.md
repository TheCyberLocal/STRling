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
from STRling import group, merge, lib, templates as tmp
# group creates a named capture group
# merge creates an non-capture group
# lib stores the basic character templates
# templates stores regex templates like tmp.phone_number

# Define a named capture groups
first_group = group('first', lib.num(3))
# first_group => (?P<first>\d{3})
second_group = group('second', lib.num(3))
# second_group => (?P<second>\d{3})
third_group = group('third', lib.num(4))
# third_group => (?P<third>\d{4})

phone_num = merge('phone_num', first_group, lib.lit('-'), second_group, lib.lit('-'), third_group)
# phone_num => (?:(?P<first>\d{3})\-(?P<second>\d{3})\-(?P<third>\d{4}))


# Create a phone number group of 10 straight digits or phone_num from above
custom = lib.num(10)
# custom = >\d{10}

phone_number = group('phone_number', lib.or_(custom, phone_num))
# phone_number => (?P<phone_number>\d{10}|(?:(?P<first>\d{3})\-(?P<second>\d{3})\-(?P<third>\d{4})))

# Compile the pattern and match against a string
compiled_pattern = re.compile(phone_number)
input_string = "123-456-7890"
match = compiled_pattern.match(input_string)


# Groups and Merges can be specified with ranges when invoked
special_pattern = merge(lib.num(1, 3), lib.lit('&', 1, ''))
chain = group('chain', special_pattern(1, ''))
# chain => (?P<chain>(?:\d{1,3}\&{1,}){1,})
```

### License

STRling is licensed under the MIT License. See the [LICENSE](https://github.com/TheCyberLocal/STRling/blob/main/LICENSE) file for more information.

---

Simplify your string validation and matching tasks with STRling, the all-in-one solution for developers who need powerful yet user-friendly tools for working with strings. Download and start using STRling today!

---

Feel free to adjust the links and other details as per your project specifics.
