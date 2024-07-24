# STRling

## 🗺️ [Project Overview](https://github.com/TheCyberLocal/STRling)

## 💾 Installation

```sh
npm install @thecyberlocal/strling
```

## ✨ STRling in action!

### 📑 [STRling Documentation](./docs/strling_docs.md)

```js
import { simply as s } from "@thecyberlocal/strling";

// Let's make a phone number pattern for the formats below:
// - (123) 456-7890
// - 123-456-7890
// - 123 456 7890
// - 1234567890

// Separator: either space or hyphen
const separator = s.inChars(" -");

// Optional area code part: 123 even if in parenthesis like (123)
const areaCode = s.merge(
  // notice we use merge since we don't want to name the group with parenthesis
  s.may("("), // Optional opening parenthesis
  s.group("area_code", s.digit(3)), // Exactly 3 digits and named for later reference
  s.may(")"), // Optional closing parenthesis
);

// Central part: 456
const centralPart = s.group("central_part", s.digit(3)); // Exactly 3 digits and named for later reference

// Last part: 7890
const lastPart = s.group("last_part", s.digit(4)); // Exactly 4 digits and named for later reference

// Combine all parts into the final phone number pattern
// Notice we don't name the whole pattern since we can already reference it
const phoneNumberPattern = s.merge(
  areaCode, // Area code part
  s.may(separator), // Optional separator after area code
  centralPart, // Central 3 digits
  s.may(separator), // Optional separator after central part
  lastPart, // Last part with hyphen and 4 digits
);

// Example usage
// Note: To make a pattern a RegEx string compatible with other engines use `toString(pattern)`.
const exampleText = "(123) 456-7890 and 123-456-7890";
const pattern = new RegExp(phoneNumberPattern.toString(), "g"); // Notice toString(pattern)
const matches = exampleText.matchAll(pattern);

for (const match of matches) {
  console.log("Full Match:", match[0]);
  console.log("Area Code:", match.groups.area_code);
  console.log("Central Part:", match.groups.central_part);
  console.log("Last Part:", match.groups.last_part);
  console.log();
}

// Output:
// Full Match: (123) 456-7890
// Area Code: 123
// Central Part: 456
// Last Part: 7890

// Full Match: 123-456-7890
// Area Code: 123
// Central Part: 456
// Last Part: 7890
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
