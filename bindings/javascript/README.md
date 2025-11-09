# STRling.js

## 🗺️ Overview

This is the **JavaScript binding** for [STRling](https://github.com/TheCyberLocal/STRling), a next-generation production-grade syntax designed as a user interface for writing powerful regular expressions (RegEx).

STRling makes string validation and matching **readable, safe, and consistent** across environments. Instead of cryptic regex syntax, you build patterns using a clean, object-oriented DSL. Under the hood, STRling compiles to native RegEx engines — but adds instructional error handling and consistent semantics.

## 🗝️ Key Features

-   **Beginner Friendly**: No regex jargon required.
-   **Reliable**: Built only on standard libraries.
-   **Instructional Errors**: Explains what went wrong and how to fix it.
-   **Consistent**: Works across frameworks and libraries without custom validators.
-   **Multilingual**: Available across popular programming languages ([Python](../python/README.md), and more coming soon).

## 💾 Installation

```sh
npm install @thecyberlocal/strling
```

## ✨ STRling in action!

### Basic Example: US Phone Number

```js
import { simply as s } from "@thecyberlocal/strling";

// Define parts of a US phone number pattern
const separator = s.inChars(" -");
const areaCode = s.merge(
    s.may("("),
    s.group("area_code", s.digit(3)),
    s.may(")")
);
const centralPart = s.group("central_part", s.digit(3));
const lastPart = s.group("last_part", s.digit(4));

const phoneNumberPattern = s.merge(
    areaCode,
    s.may(separator),
    centralPart,
    s.may(separator),
    lastPart
);

// Compile to RegEx
const exampleText = "(123) 456-7890 and 123-456-7890";
const pattern = new RegExp(phoneNumberPattern.toString(), "g");

for (const match of exampleText.matchAll(pattern)) {
    console.log("Full:", match[0]);
    console.log("Area:", match.groups.area_code);
    console.log("Central:", match.groups.central_part);
    console.log("Last:", match.groups.last_part);
}
```

### Advanced Features

For comprehensive syntax reference and advanced features, see the [STRling Semantics Specification](../../spec/grammar/semantics.md).

**Example: Character Classes and Quantifiers**

```js
import { simply as s } from "@thecyberlocal/strling";

// Match 3-5 lowercase letters
const pattern = s.inRange("a", "z", { min: 3, max: 5 });
console.log(pattern.toString());  // Compiles to regex

// Match one or more digits
const digits = s.digit({ min: 1 });

// Match optional whitespace
const whitespace = s.may(s.whitespace());
```

**Example: Groups and Backreferences**

```js
import { simply as s } from "@thecyberlocal/strling";

// Capture and reference groups
const tagPattern = s.merge(
    "<",
    s.group("tag", s.inRange("a", "z", { min: 1 })),
    ">",
    s.any(),  // Content
    "</",
    s.backref("tag"),  // Reference captured tag name
    ">"
);
```

## 📚 Documentation

- **[STRling Documentation Hub](../../docs/README.md)**: Architecture, philosophy, and development workflow
- **[Formal Specification](../../spec/README.md)**: Grammar and semantics reference
- **[Python Binding](../python/README.md)**: STRling for Python

## 🧪 Testing

For information on the test suite and development workflow, see the [Test Suite Guide](../../tests/README.md).

## 💖 Support

If you find STRling useful, consider [buying me a coffee](https://buymeacoffee.com/thecyberlocal).
