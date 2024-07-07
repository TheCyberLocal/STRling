import { simply as s } from "../STRling/index.js";

// Referencing
const first = s.group("first", s.digit(3))

const second = s.group("second", s.digit(3))

const third = s.group("third", s.digit(4))

const phoneNumberPattern = s.merge(first, "-", second, "-", third)
const exampleText = "Here is a phone number: 123-456-7890.";

const regex = new RegExp(phoneNumberPattern);
const match = exampleText.match(regex);

console.log("Full Match:", match[0]);
console.log("First:", match.groups.first);
console.log("Second:", match.groups.second);
console.log("Third:", match.groups.third);

// Expected Output:
// Full Match: 123-456-7890
// First: 123
// Second: 456
// Third: 7890
