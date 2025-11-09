# STRling.py

## 🗺️ Overview

This is the **Python binding** for [STRling](https://github.com/TheCyberLocal/STRling), a next-generation production-grade syntax designed as a user interface for writing powerful regular expressions (RegEx).

STRling makes string validation and matching **readable, safe, and consistent** across environments. Instead of cryptic regex syntax, you build patterns using a clean, object-oriented DSL. Under the hood, STRling compiles to native RegEx engines — but adds instructional error handling and consistent semantics.

## 🗝️ Key Features

-   **Beginner Friendly**: No regex jargon required.
-   **Reliable**: Built only on standard libraries.
-   **Instructional Errors**: Explains what went wrong and how to fix it.
-   **Consistent**: Works across frameworks and libraries without custom validators.
-   **Multilingual**: Available across popular programming languages ([JavaScript](../javascript/README.md), and more coming soon).

## 💾 Installation

Install STRling via pip:

```sh
pip install STRling
```

## ✨ STRling in action!

### Basic Example: US Phone Number

```python
from STRling import simply as s
import re

# Define parts of a US phone number pattern
separator = s.in_chars(" -")
area_code = s.merge(
    s.may("("),
    s.group("area_code", s.digit(3)),
    s.may(")")
)
central_part = s.group("central_part", s.digit(3))
last_part = s.group("last_part", s.digit(4))

phone_number_pattern = s.merge(
    area_code,
    s.may(separator),
    central_part,
    s.may(separator),
    last_part
)

# Compile to RegEx
example_text = "(123) 456-7890 and 123-456-7890"
pattern = re.compile(str(phone_number_pattern))
matches = pattern.finditer(example_text)

for match in matches:
    print("Full Match:", match.group())
    print("Area Code:", match.group("area_code"))
    print("Central Part:", match.group("central_part"))
    print("Last Part:", match.group("last_part"))
```

### Advanced Features

For comprehensive syntax reference and advanced features, see the [STRling Semantics Specification](../../spec/grammar/semantics.md).

**Example: Character Classes and Quantifiers**

```python
from STRling import simply as s

# Match 3-5 lowercase letters
pattern = s.in_range("a", "z", min=3, max=5)
print(str(pattern))  # Compiles to regex

# Match one or more digits
digits = s.digit(min=1)

# Match optional whitespace
whitespace = s.may(s.whitespace())
```

**Example: Groups and Backreferences**

```python
from STRling import simply as s

# Capture and reference groups
tag_pattern = s.merge(
    "<",
    s.group("tag", s.in_range("a", "z", min=1)),
    ">",
    s.any(),  # Content
    "</",
    s.backref("tag"),  # Reference captured tag name
    ">"
)
```

## 📚 Documentation

- **[STRling Documentation Hub](../../docs/README.md)**: Architecture, philosophy, and development workflow
- **[Formal Specification](../../spec/README.md)**: Grammar and semantics reference
- **[JavaScript Binding](../javascript/README.md)**: STRling for JavaScript/Node.js

## 🧪 Testing

For information on the test suite and development workflow, see the [Test Suite Guide](../../tests/README.md).

## 💖 Support

If you find STRling useful, consider [buying me a coffee](https://buymeacoffee.com/thecyberlocal).
