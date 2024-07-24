# STRling

## 🗺️ [Project Overview](https://github.com/TheCyberLocal/STRling)

STRling is a next-generation production-grade syntax designed as a user interface for writing powerful regular expressions (RegEx) with an object-oriented approach and instructional error handling. STRling recognizes the cryptic nature of raw regular expression is challenging and susceptible to errors, which is why STRling keeps it as far from you as possible while maintaining the same power and flexibility. String validation should be simple and enjoyable, not a hassle. Best of all, STRling syntax is built upon the RegEx engine, making it fully compatible with all libraries that accept RegEx along with the traditional built-in RegEx methods.

## 🗝️ Key Features

1. **Beginner Friendly:** You need ZERO knowledge of RegEx jargon to create powerful and clear-to-read patterns.
2. **Reliable Logic:** STRling exclusively utilizes built-in libraries, making it a reliable package.
3. **Instructional Error Handling:** Errors inevitably occur by drafting invalid patterns, so STRling explains to the developer exactly what was done wrong and how to correct it.
4. **Consistent and Readable:** Make your projects clear and consistent by using STRling rather than the individual library string validators that each have their own syntax (Sqlite3, Sequelize, Postgres, WTForms... etc.).
5. **Multilingual Availability:** STRling is not just a package, but a concept brought to you through multiple widely used languages.

These key features collectively emphasize and fortify the claim that STRling truly is a next-generation production-grade syntax for pattern handling.

## 🎯 Project Mission

Our mission is to make RegEx a distant and outdated syntax by abstracting the complexities of RegEx into a clean, readable, and powerful interface. We strive to simplify string operations and ensure that developers can focus on building their applications without the steep learning curve of traditional RegEx. The previous alternative to RegEx was to learn the string validation syntax specific to each user input library, but STRling aims to unify the disparate syntaxes found across various libraries and frameworks into one simple library using only built-in packages.

## 💾 Installation

Install STRling via pip:

```sh
pip install STRling
```

## ✨ STRling in action!

### 📑 [STRling Documentation](./docs/strling_docs.md)

```python
from STRling import simply as s
import re


# Let's make a phone number pattern for the formats below:
# - (123) 456-7890
# - 123-456-7890
# - 123 456 7890
# - 1234567890

# Separator: either space or hyphen
separator = s.in_chars(' -')

# Optional area code part: 123 even if in parenthesis like (123)
area_code = s.merge( # notice we use merge since we don't want to name the group with parenthesis
    s.may('('),  # Optional opening parenthesis
    s.group('area_code', s.digit(3)), # Exactly 3 digits and named for later reference
    s.may(')')  # Optional closing parenthesis
)

# Central part: 456
central_part = s.group('central_part', s.digit(3))  # Exactly 3 digits and named for later reference

# Last part: 7890
last_part = s.group("last_part", s.digit(4))  # Exactly 4 digits and named for later reference

# Combine all parts into the final phone number pattern
# Notice we don't name the whole pattern since we can already reference it
phone_number_pattern = s.merge(
    area_code,  # Area code part
    s.may(separator),  # Optional separator after area code
    central_part,  # Central 3 digits
    s.may(separator),  # Optional separator after area code
    last_part  # Last part with hyphen and 4 digits
)

# Example usage
# Note: To make a pattern a RegEx string compatible with other engines use `str(pattern)`.
example_text = "(123) 456-7890 and 123-456-7890"
pattern = re.compile(str(phone_number_pattern))  # Notice str(pattern)
matches = pattern.finditer(example_text)

for match in matches:
    print("Full Match:", match.group())
    print("Area Code:", match.group("area_code"))
    print("Central Part:", match.group("central_part"))
    print("Last Part:", match.group("last_part"))
    print()

# Output:
# Full Match: (123) 456-7890
# Area Code: 123
# Central Part: 456
# Last Part: 7890

# Full Match: 123-456-7890
# Area Code: 123
# Central Part: 456
# Last Part: 7890
```

Simplify your string validation and matching tasks with STRling, the all-in-one solution for developers who need a powerful yet user-friendly tool for working with strings. No longer write RegEx using complex jargon or the various syntaxes string validation specific to independent libraries. Download and start using STRling today!

## 🌎 Locations

### STRling for Python

[![](https://img.shields.io/pypi/v/STRling?color=blue&logo=pypi)](https://pypi.org/project/STRling/)
[![](https://img.shields.io/badge/GitHub-black?logo=github&logoColor=white)](https://github.com/TheCyberLocal/STRling-Py)

### STRling for JavaScript

[![](https://img.shields.io/npm/v/@thecyberlocal/strling?color=blue&logo=npm)](https://www.npmjs.com/package/@thecyberlocal/strling)
[![](https://img.shields.io/badge/GitHub-black?logo=github&logoColor=white)](https://github.com/TheCyberLocal/STRling-JS)

## 🌐 Socials

[![LinkedIn](https://img.shields.io/badge/LinkedIn-%230077B5.svg?logo=linkedin&logoColor=white)](https://linkedin.com/in/tzm01)
[![GitHub](https://img.shields.io/badge/GitHub-black?logo=github&logoColor=white)](https://github.com/TheCyberLocal)
[![PyPI](https://img.shields.io/badge/PyPI-3776AB?logo=pypi&logoColor=white)](https://pypi.org/user/TheCyberLocal/)
[![npm](https://img.shields.io/badge/npm-%23FFFFFF.svg?logo=npm&logoColor=D00000)](https://www.npmjs.com/~thecyberlocal)

## 💖 Support

If you find my content helpful or interesting, consider buying me a coffee. Every cup is greatly appreciated and fuels my work!

[![Buy Me a Coffee](https://img.shields.io/badge/-buy_me_a%C2%A0coffee-gray?logo=buy-me-a-coffee)](https://buymeacoffee.com/thecyberlocal)
[![PayPal](https://img.shields.io/badge/PayPal-00457C?logo=paypal&logoColor=white)](https://www.paypal.com/paypalme/TheCyberLocal)
[![Venmo](https://img.shields.io/badge/Venmo-008CFF?logo=venmo&logoColor=white)](https://www.venmo.com/TheCyberLocal)
