import { simply as s } from "STRling";

// Let's make a phone number pattern for the formats below:
// - (123) 456-7890
// - 123-456-7890
// - 123 456 7890
// - 1234567890

// Separator: either space or hyphen
const separator = s.inChars(' -');

// Optional area code part: 123 even if in parenthesis like (123)
const areaCode = s.merge(  // notice we use merge since we don't want to name the group with parenthesis
    s.may('('),  // Optional opening parenthesis
    s.group('area_code', s.digit(3)), // Exactly 3 digits and named for later reference
    s.may(')')  // Optional closing parenthesis
);

// Central part: 456
const centralPart = s.group('central_part', s.digit(3));  // Exactly 3 digits and named for later reference

// Last part: 7890
const lastPart = s.group("last_part", s.digit(4));  // Exactly 4 digits and named for later reference

// Combine all parts into the final phone number pattern
// Notice we don't name the whole pattern since we can already reference it
const phoneNumberPattern = s.merge(
    areaCode,  // Area code part
    s.may(separator),  // Optional separator after area code
    centralPart,  // Central 3 digits
    s.may(separator),  // Optional separator after central part
    lastPart  // Last part with hyphen and 4 digits
);

// Example usage
// Note: To make a pattern a RegEx string compatible with other engines use `toString(pattern)`.
const exampleText = "(123) 456-7890 and 123-456-7890";
const pattern = new RegExp(phoneNumberPattern.toString());  // Notice toString(pattern)
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
