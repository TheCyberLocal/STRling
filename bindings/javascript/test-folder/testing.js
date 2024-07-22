import { simply as s } from "../STRling/index.js";

s.anyOf(); // Matches any pattern, including patterns consisting of subpatterns.
// A composite pattern is one consisting of subpatterns (created by constructors and lookarounds).
const pattern1 = s.merge(s.digit(3), s.letter(3)); // Matches 3 digits followed by 3 letters.
const pattern2 = s.merge(s.letter(3), s.digit(3)); // Matches 3 letters followed by 3 digits.
s.anyOf(pattern1, pattern2); // Matches either pattern1 or pattern2

s.may(); // Optionally matches the provided patterns.
// If a `may` pattern isn't there, it still will match the rest of the patterns.
s.merge(s.letter(), s.may(s.digit()));
// Matches any letter, and includes any digit following the letter.
// In the text, "AB2" the pattern above matches 'A' and 'B2'.

s.merge(); // Combines multiple patterns into one larger pattern.
// You can see this used for the method above.

s.capture(); // Creates a numbered group that can be indexed for extracting part of a match later.
// Capture is used the same as merge.
s.capture(s.letter(), s.digit());

// Captures CANNOT be invoked with a range: s.capture(s.digit(), s.letter())(1, 2) <== INVALID
// Captures CAN be invoked with a number of copies: s.capture(s.digit(), s.letter())(3) <== VALID

const threeDigitGroup = s.capture(s.digit(3));
const fourGroupsOfThree = threeDigitGroup.rep(4);

const exampleText = "Here is a number: 111222333444";
const match = exampleText.match(new RegExp(fourGroupsOfThree.toString())); // Notice toString(pattern)

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
