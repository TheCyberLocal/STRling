import { STRlingError, Pattern, lit } from "./pattern.js";

// User Char Sets

/**
Matches all characters within and including the start and end of a letter or number range.
@param {string|number} start - The starting character or digit of the range.
@param {string|number} end - The ending character or digit of the range.
@param {number} [minRep] - The minimum number of characters to match.
@param {number} [maxRep] - The maximum number of characters to match.
@returns {Pattern} The regex pattern.
@throws {STRlingError} If the arguments are invalid.
 */
export function between(start, end, minRep, maxRep) {
  if (
    (typeof start !== "string" || typeof end !== "string") &&
    (typeof start !== "number" || typeof end !== "number")
  ) {
    const message = `
    Method: simply.between(start, end)

    The start and end arguments must both be integers (0-9) or letters of the same case (A-Z or a-z).
    `;
    throw new STRlingError(message);
  }

  let newPattern;

  if (typeof start === "number") {
    if (start > end) {
      const message = `
      Method: simply.between(start, end)

      The start integer must not be greater than the end integer.
      `;
      throw new STRlingError(message);
    }

    if (start < 0 || start > 9 || end < 0 || end > 9) {
      const message = `
      Method: simply.between(start, end)

      The start and end integers must be single digits (0-9).
      `;
      throw new STRlingError(message);
    }

    newPattern = `[${start}-${end}]`;
  }

  if (typeof start === "string") {
    if (!/^[a-zA-Z]$/.test(start) || !/^[a-zA-Z]$/.test(end)) {
      const message = `
      Method: simply.between(start, end)

      The start and end must be alphabetical characters.
      `;
      throw new STRlingError(message);
    }

    if (start.length !== 1 || end.length !== 1) {
      const message = `
      Method: simply.between(start, end)

      The start and end characters must be single letters.
      `;
      throw new STRlingError(message);
    }

    if (
      (start.toLowerCase() === start && end.toLowerCase() !== end) ||
      (start.toUpperCase() === start && end.toUpperCase() !== end)
    ) {
      const message = `
      Method: simply.between(start, end)

      The start and end characters must be of the same case.
      `;
      throw new STRlingError(message);
    }

    if (start > end) {
      const message = `
      Method: simply.between(start, end)

      The start character must not be lexicographically greater than the end character.
      `;
      throw new STRlingError(message);
    }

    newPattern = `[${start}-${end}]`;
  }

  return new Pattern({ pattern: newPattern, composite: true }).rep(
    minRep,
    maxRep,
  );
}

/**
Matches any character not within or including the start and end of a letter or digit range.
@param {string|number} start - The starting character or digit of the range.
@param {string|number} end - The ending character or digit of the range.
@param {number} [minRep] - The minimum number of characters to match.
@param {number} [maxRep] - The maximum number of characters to match.
@returns {Pattern} The regex pattern.
@throws {STRlingError} If the arguments are invalid.
 */
export function notBetween(start, end, minRep, maxRep) {
  if (
    (typeof start !== "string" || typeof end !== "string") &&
    (typeof start !== "number" || typeof end !== "number")
  ) {
    const message = `
    Method: simply.notBetween(start, end)

    The start and end arguments must both be integers (0-9) or letters of the same case (A-Z or a-z).
    `;
    throw new STRlingError(message);
  }

  let newPattern;

  if (typeof start === "number") {
    if (start > end) {
      const message = `
      Method: simply.notBetween(start, end)

      The start integer must not be greater than the end integer.
      `;
      throw new STRlingError(message);
    }

    if (start < 0 || start > 9 || end < 0 || end > 9) {
      const message = `
      Method: simply.notBetween(start, end)

      The start and end integers must be single digits (0-9).
      `;
      throw new STRlingError(message);
    }

    newPattern = `[^${start}-${end}]`;
  }

  if (typeof start === "string") {
    if (!/^[a-zA-Z]$/.test(start) || !/^[a-zA-Z]$/.test(end)) {
      const message = `
      Method: simply.notBetween(start, end)

      The start and end must be alphabetical characters.
      `;
      throw new STRlingError(message);
    }

    if (start.length !== 1 || end.length !== 1) {
      const message = `
      Method: simply.notBetween(start, end)

      The start and end characters must be single letters.
      `;
      throw new STRlingError(message);
    }

    if (
      (start.toLowerCase() === start && end.toLowerCase() !== end) ||
      (start.toUpperCase() === start && end.toUpperCase() !== end)
    ) {
      const message = `
      Method: simply.notBetween(start, end)

      The start and end characters must be of the same case.
      `;
      throw new STRlingError(message);
    }

    if (start > end) {
      const message = `
      Method: simply.notBetween(start, end)

      The start character must not be lexicographically greater than the end character.
      `;
      throw new STRlingError(message);
    }

    newPattern = `[^${start}-${end}]`;
  }

  return new Pattern({
    pattern: newPattern,
    composite: true,
    negated: true,
  }).rep(minRep, maxRep);
}

/**
Matches any provided patterns, but they can't include subpatterns.
@param {...(Pattern|string)} patterns - One or more non-composite patterns to match.
@returns {Pattern} A Pattern object that matches any of the given patterns.
@throws {STRlingError} If any pattern is invalid.
 */
export function inChars(...patterns) {
  const cleanPatterns = patterns.map((pattern) => {
    if (typeof pattern === "string") {
      pattern = lit(pattern)
    }

    if (!(pattern instanceof Pattern)) {
      const message = `
      Method: simply.inChars(...patterns)

      The parameters must be instances of Pattern or string.

      Use a string such as "123abc$" to match literal characters, or use a predefined set like simply.letter().
      `;
      throw new STRlingError(message);
    }

    return pattern;
  });

  if (cleanPatterns.some((p) => p.composite)) {
    const message = `
    Method: simply.inChars(...patterns)

    All patterns must be non-composite.
    `;
    throw new STRlingError(message);
  }

  let joined = "";
  for (const pattern of cleanPatterns) {
    const patternStr = pattern.toString();
    if (
      patternStr.length > 1 &&
      patternStr[patternStr.length - 1] === "}" &&
      patternStr[patternStr.length - 2] !== "\\"
    ) {
      const message = `
      Method: simply.inChars(...patterns)

      Patterns must not have specified ranges.
      `;
      throw new STRlingError(message);
    }

    if (pattern.customSet) {
      if (pattern.negated) {
        const message = `
        Method: simply.inChars(...patterns)

        To match the characters specified in a negated set, move the parameters directly into simply.inChars(...patterns).

        Example: simply.inChars(simply.notInChars(...patterns)) => simply.inChars(...patterns)
        `;
        throw new STRlingError(message);
      } else {
        joined += patternStr.slice(1, -1); // [pattern] => pattern
      }
    } else {
      joined += patternStr;
    }
  }

  const newPattern = `[${joined}]`;
  return new Pattern({ pattern: newPattern, composite: true });
}

/**
Matches anything but the provided patterns, but they can't include subpatterns.
@param {...(Pattern|string)} patterns - One or more non-composite patterns to avoid.
@returns {Pattern} A Pattern object that matches any of the given patterns.
@throws {STRlingError} If any pattern is invalid.
 */
export function notInChars(...patterns) {
  const cleanPatterns = patterns.map((pattern) => {
    if (typeof pattern === "string") {
      pattern = lit(pattern)
    }

    if (!(pattern instanceof Pattern)) {
      const message = `
      Method: simply.notInChars(...patterns)

      The parameters must be instances of Pattern or string.

      Use a string such as "123abc$" to match literal characters, or use a predefined set like simply.letter().
      `;
      throw new STRlingError(message);
    }

    return pattern;
  });

  if (cleanPatterns.some((p) => p.composite)) {
    const message = `
    Method: simply.notInChars(...patterns)

    All patterns must be non-composite.
    `;
    throw new STRlingError(message);
  }

  let joined = "";
  for (const pattern of cleanPatterns) {
    const patternStr = pattern.toString();
    if (
      patternStr.length > 1 &&
      patternStr[patternStr.length - 1] === "}" &&
      patternStr[patternStr.length - 2] !== "\\"
    ) {
      const message = `
      Method: simply.notInChars(...patterns)

      Patterns must not have specified ranges.
      `;
      throw new STRlingError(message);
    }

    if (pattern.customSet) {
      if (pattern.negated) {
        joined += patternStr.slice(2, -1); // [^pattern] => pattern
      } else {
        joined += patternStr.slice(1, -1); // [pattern] => pattern
      }
    } else {
      joined += patternStr;
    }
  }

  const newPattern = `[^${joined}]`;
  return new Pattern({ pattern: newPattern, composite: true, negated: true });
}
