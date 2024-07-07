import { STRlingError, Pattern, lit } from "./pattern.js";


/**
Matches any provided pattern, including patterns consisting of subpatterns.
@param {...(Pattern|string)} patterns - One or more patterns to be matched.
@returns {Pattern} An instance of the Pattern class.
@example
// Matches 3 digits followed by 3 letters.
const pattern1 = s.merge(s.digit(3), s.letter(3));

// Matches 3 letters followed by 3 digits.
const pattern2 = s.merge(s.letter(3), s.digit(3));

// Matches either pattern1 or pattern2.
const eitherPattern = s.anyOf(pattern1, pattern2);
*/
export function anyOf(...patterns) {
  const cleanPatterns = patterns.map((pattern) => {
    if (typeof pattern === "string") {
      pattern = lit(pattern)
    }

    if (!(pattern instanceof Pattern)) {
      const message = `
      Method: simply.anyOf(...patterns)

      The parameters must be instances of Pattern or string.

      Use a string such as "123abc$" to match literal characters, or use a predefined set like simply.letter().
      `;
      throw new STRlingError(message);
    }

    return pattern;
  });

  const namedGroupCounts = {};
  cleanPatterns.forEach((pattern) => {
    pattern.namedGroups.forEach((groupName) => {
      if (namedGroupCounts[groupName]) {
        namedGroupCounts[groupName] += 1;
      } else {
        namedGroupCounts[groupName] = 1;
      }
    });
  });

  const duplicates = Object.entries(namedGroupCounts).filter(
    ([_, count]) => count > 1
  );
  if (duplicates.length) {
    const duplicateInfo = duplicates
      .map(([name, count]) => `${name}: ${count}`)
      .join(", ");
    const message = `
    Method: simply.anyOf(...patterns)

    Named groups must be unique.
    Duplicate named groups found: ${duplicateInfo}.

    If you need later reference change the named group argument to simply.capture().
    If you don't need later reference change the named group argument to simply.merge().
    `;
    throw new STRlingError(message);
  }

  const subNames = Object.keys(namedGroupCounts);

  const joined = cleanPatterns.map((p) => p.toString()).join("|");
  const newPattern = `(?:${joined})`;

  return new Pattern({
    pattern: newPattern,
    composite: true,
    namedGroups: subNames,
  });
}

/**
Optionally matches the provided patterns. If this pattern is absent, surrounding patterns can still match.
@param {...(Pattern|string)} patterns - One or more patterns to be optionally matched.
@returns {Pattern} An instance of the Pattern class.
@example
// Matches any letter, along with any trailing digit.
const pattern = s.merge(s.letter(), s.may(s.digit()));

// In the text "AB2" the pattern above matches 'A' and 'B2'.
*/
export function may(...patterns) {
  const cleanPatterns = patterns.map((pattern) => {
    if (typeof pattern === "string") {
      pattern = lit(pattern)
    }

    if (!(pattern instanceof Pattern)) {
      const message = `
      Method: simply.may(...patterns)

      The parameters must be instances of Pattern or string.

      Use a string such as "123abc$" to match literal characters, or use a predefined set like simply.letter().
      `;
      throw new STRlingError(message);
    }

    return pattern;
  });

  const namedGroupCounts = {};
  cleanPatterns.forEach((pattern) => {
    pattern.namedGroups.forEach((groupName) => {
      if (namedGroupCounts[groupName]) {
        namedGroupCounts[groupName] += 1;
      } else {
        namedGroupCounts[groupName] = 1;
      }
    });
  });

  const duplicates = Object.entries(namedGroupCounts).filter(
    ([_, count]) => count > 1
  );
  if (duplicates.length) {
    const duplicateInfo = duplicates
      .map(([name, count]) => `${name}: ${count}`)
      .join(", ");
    const message = `
    Method: simply.may(...patterns)

    Named groups must be unique.
    Duplicate named groups found: ${duplicateInfo}.

    If you need later reference change the named group argument to simply.capture().
    If you don't need later reference change the named group argument to simply.merge().
    `;
    throw new STRlingError(message);
  }

  const subNames = Object.keys(namedGroupCounts);

  const joined = merge(...cleanPatterns).toString();
  const newPattern = `${joined}?`;

  return new Pattern({
    pattern: newPattern,
    composite: true,
    namedGroups: subNames,
  });
}

/**
Combines the provided patterns into one larger pattern.
@param {...(Pattern|string)} patterns - One or more patterns to be concatenated.
@returns {Pattern} An instance of the Pattern class.
@example
// Matches any digit followed by a comma and period.
const mergedPattern = s.merge(s.digit(), ',.');
*/
export function merge(...patterns) {
  const cleanPatterns = patterns.map((pattern) => {
    if (typeof pattern === "string") {
      pattern = lit(pattern)
    }

    if (!(pattern instanceof Pattern)) {
      const message = `
      Method: simply.merge(...patterns)

      The parameters must be instances of Pattern or string.

      Use a string such as "123abc$" to match literal characters, or use a predefined set like simply.letter().
      `;
      throw new STRlingError(message);
    }

    return pattern;
  });

  const namedGroupCounts = {};
  cleanPatterns.forEach((pattern) => {
    pattern.namedGroups.forEach((groupName) => {
      if (namedGroupCounts[groupName]) {
        namedGroupCounts[groupName] += 1;
      } else {
        namedGroupCounts[groupName] = 1;
      }
    });
  });

  const duplicates = Object.entries(namedGroupCounts).filter(
    ([_, count]) => count > 1
  );
  if (duplicates.length) {
    const duplicateInfo = duplicates
      .map(([name, count]) => `${name}: ${count}`)
      .join(", ");
    const message = `
    Method: simply.merge(...patterns)

    Named groups must be unique.
    Duplicate named groups found: ${duplicateInfo}.

    If you need later reference change the named group argument to simply.capture().
    If you don't need later reference change the named group argument to simply.merge().
    `;
    throw new STRlingError(message);
  }

  const subNames = Object.keys(namedGroupCounts);

  const joined = cleanPatterns.map((p) => p.toString()).join("");
  const newPattern = `(?:${joined})`;

  return new Pattern({
    pattern: newPattern,
    composite: true,
    namedGroups: subNames,
  });
}

/**
Creates a numbered group that can be indexed for extracting this part of the match.
@param {...(Pattern|string)} patterns - One or more patterns to be captured.
@returns {Pattern} An instance of the Pattern class.
@example
// Captures CANNOT be invoked with a range.
s.capture(s.digit(), s.letter())(1, 2) // <== INVALID

// Captures CAN be invoked with a number of copies.
s.capture(s.digit(), s.letter())(3) // <== VALID
@example
// Matches any digit followed by a comma and period.
const capturedPattern = s.capture(s.digit(), ',.');
@example
const threeDigitGroup = s.capture(s.digit(3));
const fourGroupsOfThree = threeDigitGroup.rep(4);

const exampleText = "Here is a number: 111222333444";

const regex = new RegExp(fourGroupsOfThree);
const match = exampleText.match(regex);

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
*/
export function capture(...patterns) {
  const cleanPatterns = patterns.map((pattern) => {
    if (typeof pattern === "string") {
      pattern = lit(pattern)
    }

    if (!(pattern instanceof Pattern)) {
      const message = `
      Method: simply.capture(...patterns)

      The parameters must be instances of Pattern or string.

      Use a string such as "123abc$" to match literal characters, or use a predefined set like simply.letter().
      `;
      throw new STRlingError(message);
    }

    return pattern;
  });

  // Count named groups and raise error if not unique
  const namedGroupCounts = {};
  cleanPatterns.forEach((pattern) => {
    pattern.namedGroups.forEach((groupName) => {
      if (namedGroupCounts[groupName]) {
        namedGroupCounts[groupName] += 1;
      } else {
        namedGroupCounts[groupName] = 1;
      }
    });
  });

  const duplicates = Object.entries(namedGroupCounts).filter(
    ([_, count]) => count > 1
  );
  if (duplicates.length) {
    const duplicateInfo = duplicates
      .map(([name, count]) => `${name}: ${count}`)
      .join(", ");
    const message = `
    Method: simply.capture(...patterns)

    Named groups must be unique.
    Duplicate named groups found: ${duplicateInfo}.

    If you need later reference change the named group argument to simply.capture().
    If you don't need later reference change the named group argument to simply.merge().
    `;
    throw new STRlingError(message);
  }

  const subNames = Object.keys(namedGroupCounts);

  const joined = cleanPatterns.map((p) => p.toString()).join("");
  const newPattern = `(${joined})`;

  return new Pattern({
    pattern: newPattern,
    composite: true,
    numberedGroup: true,
    namedGroups: subNames,
  });
}

/**
Creates a unique named group that can be referenced for extracting this part of the match.
@param {string} name - The name of the capturing group.
@param {...(Pattern|string)} patterns - One or more patterns to be captured.
@returns {Pattern} An instance of the Pattern class.
@example
// Groups CANNOT be invoked with a range.
s.group('name', s.digit())(1, 2) # <== INVALID
@example
// Matches any digit followed by a comma and period.
const capturedPattern = s.capture(s.digit(), ',.');
@example
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

// Output:
// Full Match: 123-456-7890
// First: 123
// Second: 456
// Third: 7890
*/
export function group(name, ...patterns) {
  if (typeof name !== "string") {
    const message = `
    Method: simply.group(name, ...patterns)

    The group is missing a specified name.
    The name parameter must be a string like 'groupName'.
    `;
    throw new STRlingError(message);
  }

  const cleanPatterns = patterns.map((pattern) => {
    if (typeof pattern === "string") {
      pattern = lit(pattern)
    }

    if (!(pattern instanceof Pattern)) {
      const message = `
      Method: simply.group(name, ...patterns)

      The parameters must be instances of Pattern or string.

      Use a string such as "123abc$" to match literal characters, or use a predefined set like simply.letter().
      `;
      throw new STRlingError(message);
    }

    return pattern;
  });

  // Count named groups and raise error if not unique
  const namedGroupCounts = {};
  cleanPatterns.forEach((pattern) => {
    pattern.namedGroups.forEach((groupName) => {
      if (namedGroupCounts[groupName]) {
        namedGroupCounts[groupName] += 1;
      } else {
        namedGroupCounts[groupName] = 1;
      }
    });
  });

  const duplicates = Object.entries(namedGroupCounts).filter(
    ([_, count]) => count > 1
  );
  if (duplicates.length) {
    const duplicateInfo = duplicates
      .map(([name, count]) => `${name}: ${count}`)
      .join(", ");
    const message = `
    Method: simply.group(name, ...patterns)

    Named groups must be unique.
    Duplicate named groups found: ${duplicateInfo}.

    If you need later reference change the named group argument to simply.capture().
    If you don't need later reference change the named group argument to simply.merge().
    `;
    throw new STRlingError(message);
  }

  const subNames = Object.keys(namedGroupCounts);

  const joined = cleanPatterns.map((p) => p.toString()).join("");
  const newPattern = `(?<${name}>${joined})`;

  return new Pattern({
    pattern: newPattern,
    composite: true,
    namedGroups: [name, ...subNames],
  });
}
