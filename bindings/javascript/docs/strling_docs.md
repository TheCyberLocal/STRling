# 📑 STRling Documentation

### [⇦ Back to Project Overview](../README.md)

## 😅 Don't worry if you can't remember it all!

We have well structured and explanatory docustrings for each function
that allow you to understand exactly how it works by just hovering your mouse.

```js
import { simply as s } from "STRling";
import re;


// // // Range Feature // // //

// Most methods allow the `minRep` and `maxRep` to be passed in directly or after params.
// For example, simply.letter(1, 3) will match 1 to 3 letters.

// But some methods take an unknown number of parameters and can't distinguish the range.
// For example, s.merge(simply.letter(), simply.digit(), 1, 2). <==== INVALID

// However, all methods allow setting the range using the rep method unless otherwise specified.
// For example, simply.letter().rep(1, 2) is the same as simply.letter(1, 2).

// This external invocation may seem useless, but it can solve our earlier issue.
// For example, s.merge(simply.letter(), simply.digit()).rep(1, 2). <==== VALID

// Notice for all functions (where repetition is valid) we can use the rep method,
// but it is primarily useful for functions with an unknown number of parameters.


// // // Custom Literals // // //

// Creates a matching pattern from a regular string
s.lit('$%');  // Matches the literal characters '$' or '%'.


// // // Character Sets // // //

// Note: Each character set below has a negated counterpart.
// For example, simply.letter() => simply.notLetter()

s.alphaNum();    // Matches any letter (uppercase or lowercase) or digit.
s.specialChar(); // Matches any special character. => !"#$%&'()*+,-./:;<=>?@[\]^_`{|}~

s.letter();      // Matches any letter (uppercase or lowercase).
s.upper();       // Matches any uppercase letter.
s.lower();       // Matches any lowercase letter.

s.digit();       // Matches any digit.
s.hexDigit();    // Matches any letter A through F (uppercase or lowercase) or a digit (0-9).

s.whitespace();  // Matches any whitespace character (space, tab, newline, carriage return, etc.).
s.newline();     // Matches a newline character.
s.bound();       // Matches a boundary character.

// Note: Each character set below doesn't has a negated counterpart.
// For example, simply.tab(), but there is no simply.notTab().

s.tab()          // Matches a tab character.
s.carriage()     // Matches a carriage return character.


// // // Anchors // // //

s.start();  // Matches the start of a line.
// There is no `simply.notStart()` function.
// Instead, use `simply.notBehind(simply.start())`.

s.end();  // Matches the end of a line.
// There is no `simply.notEnd()` function.
// Instead, use `simply.notAhead(simply.end())`.


// // // Custom Sets // // //

// Note: Each custom set below has a negated counterpart.
// For example, simply.between() => simply.notBetween()

// Matches all characters within and including the start and end of a letter or number range.
s.between(0, 9);     // Matches any digit from 0 to 9.
s.between('a', 'z'); // Matches any lowercase letter from 'a' to 'z'.
s.between('A', 'Z'); // Matches any uppercase letter from 'A' to 'Z'.

// Matches any provided patterns, but they can't include subpatterns.
s.inChars(s.letter(), s.digit(), ',.');  // Matches any letter, digit, comma, and period.
// A composite pattern is one consisting of subpatterns (created by constructors and lookarounds).


// // // Constructors // // //

s.anyOf();  // Matches any pattern, including patterns consisting of subpatterns.
// A composite pattern is one consisting of subpatterns (created by constructors and lookarounds).
const pattern1 = s.merge(s.digit(3), s.letter(3));  // Matches 3 digits followed by 3 letters.
const pattern2 = s.merge(s.letter(3), s.digit(3));  // Matches 3 letters followed by 3 digits.
s.anyOf(pattern1, pattern2);  // Matches either pattern1 or pattern2

s.may();  // Optionally matches the provided patterns.
// If a `may` pattern isn't there, it still will match the rest of the patterns.
s.merge(s.letter(), s.may(s.digit()));
// Matches any letter, and includes any digit following the letter.
// In the text, "AB2" the pattern above matches 'A' and 'B2'.

s.merge();  // Combines multiple patterns into one larger pattern.
// You can see this used for the method above.

s.capture();  // Creates a numbered group that can be indexed for extracting part of a match later.
// Capture is used the same as merge.
s.capture(s.letter(), s.digit());

// Captures CANNOT have a range: s.capture(s.digit(), s.letter()).rep(1, 2) <== INVALID
// Captures CAN match an exact number of copies: s.capture(s.digit(), s.letter()).rep(3) <== VALID

const threeDigitGroup = s.capture(s.digit(3));
const fourGroupsOfThree = threeDigitGroup.rep(4);

const exampleText = "Here is a number: 111222333444";
const match = exampleText.match(new RegExp(fourGroupsOfThree.toString()));  // Notice toString(pattern)

console.log("Full Match:", match[0]);
console.log("First:", match[1]);
console.log("Second:", match[2]);
console.log("Third:", match[3]);
console.log("Fourth:", match[4]);

// Output:
// Full Match: 111222333444
// First: 111
// Second: 222
// Third: 333
// Fourth: 444

s.group();  // Creates a named group that can be referenced for extracting part of a match.
// group is used the same as merge and capture but it takes a string name as the first argument.
s.group('my_group', s.letter(), s.digit());

// Unlike merge and capture, groups CANNOT be invoked with a range.
// This is because group names must be unique in a pattern.
// s.group('unique_name', s.digit()).rep(1, 2) <== INVALID

// Groups can easily be referenced from the match by name
// assuming the numbers have been grouped and named properly.
const exampleText2 = "Here is a phone number: 123-456-7890.";
const match2 = exampleText2.match(new RegExp(phoneNumberPattern.toString()));  // Notice toString(pattern)

console.log("Full Match:", match2[0]);
console.log("Area Code:", match2.groups.area_code);
console.log("Central Part:", match2.groups.central_part);
console.log("Last Part:", match2.groups.last_part);

// Output:
// Full Match: 123-456-7890
// Area Code: 123
// Central Part: 456
// Last Part: 7890


// // // Lookarounds // // //

// Note: Each lookaround below has a negated counterpart.
// For example, simply.ahead() => simply.notAhead()

// These verify a pattern is or isn't ahead or behind
// without capturing it as part of the pattern matched.

s.ahead();  // Only matches the rest of a pattern if the provided pattern is ahead.
// For example, in the text "123ABC", the pattern below matches 3 but not 1 or 2.
s.merge(s.digit(), s.ahead(s.letter()));  // Only matches a digit followed by a letter.

s.behind();  // Only matches the rest of a pattern if the provided pattern is behind.
// For example, in the text "123ABC", the pattern below matches A but not B or C.
s.merge(s.behind(s.digit()), s.letter());  // Only matches a letter preceded by a digit.
```

Simplify your string validation and matching tasks with STRling, the all-in-one solution for developers who need a powerful yet user-friendly tool for working with strings. No longer write RegEx using complex jargon or the various syntaxes string validation specific to independent libraries. Download and start using STRling today!
