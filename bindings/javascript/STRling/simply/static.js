import { Pattern, lit } from "./pattern";

/**
 * Matches any letter (uppercase or lowercase) or digit.
 * @param {number} [minRep] - The minimum number of characters to match.
 * @param {number} [maxRep] - The maximum number of characters to match.
 * @returns {Pattern} The regex pattern.
 */
export function alphaNum(minRep, maxRep) {
  return new Pattern("[A-Za-z0-9]", (customSet = true)).rep(minRep, maxRep);
}

/**
 * Matches any character that is not a letter or digit.
 * @param {number} [minRep] - The minimum number of characters to match.
 * @param {number} [maxRep] - The maximum number of characters to match.
 * @returns {Pattern} The regex pattern.
 */
export function notAlphaNum(minRep, maxRep) {
  return new Pattern("[^A-Za-z0-9]", (customSet = true), (negated = true)).rep(
    minRep,
    maxRep,
  );
}

/**
 * Matches any special character.
 * @param {number} [minRep] - The minimum number of characters to match.
 * @param {number} [maxRep] - The maximum number of characters to match.
 * @returns {Pattern} The regex pattern.
 */
export function specialChar(minRep, maxRep) {
  const special = lit(`!"#$%&'()*+,-./:;<=>?@[\\]^_\`{|}~`);
  return new Pattern(`[${special}]`, (customSet = true)).rep(minRep, maxRep);
}

/**
 * Matches any character that is not a special character.
 * @param {number} [minRep] - The minimum number of characters to match.
 * @param {number} [maxRep] - The maximum number of characters to match.
 * @returns {Pattern} The regex pattern.
 */
export function notSpecialChar(minRep, maxRep) {
  const special = lit(`!"#$%&'()*+,-./:;<=>?@[\\]^_\`{|}~`);
  return new Pattern(`[^${special}]`, (customSet = true), (negated = true)).rep(
    minRep,
    maxRep,
  );
}

/**
 * Matches any letter (uppercase or lowercase).
 * @param {number} [minRep] - The minimum number of characters to match.
 * @param {number} [maxRep] - The maximum number of characters to match.
 * @returns {Pattern} The regex pattern.
 */
export function letter(minRep, maxRep) {
  return new Pattern("[A-Za-z]", (customSet = true)).rep(minRep, maxRep);
}

/**
 * Matches any character that is not a letter.
 * @param {number} [minRep] - The minimum number of characters to match.
 * @param {number} [maxRep] - The maximum number of characters to match.
 * @returns {Pattern} The regex pattern.
 */
export function notLetter(minRep, maxRep) {
  return new Pattern("[^A-Za-z]", (customSet = true), (negated = true)).rep(
    minRep,
    maxRep,
  );
}

/**
 * Matches any uppercase letter.
 * @param {number} [minRep] - The minimum number of characters to match.
 * @param {number} [maxRep] - The maximum number of characters to match.
 * @returns {Pattern} The regex pattern.
 */
export function upper(minRep, maxRep) {
  return new Pattern("[A-Z]", (customSet = true)).rep(minRep, maxRep);
}

/**
 * Matches any character that is not an uppercase letter.
 * @param {number} [minRep] - The minimum number of characters to match.
 * @param {number} [maxRep] - The maximum number of characters to match.
 * @returns {Pattern} The regex pattern.
 */
export function notUpper(minRep, maxRep) {
  return new Pattern("[^A-Z]", (customSet = true), (negated = true)).rep(
    minRep,
    maxRep,
  );
}

/**
 * Matches any lowercase letter.
 * @param {number} [minRep] - The minimum number of characters to match.
 * @param {number} [maxRep] - The maximum number of characters to match.
 * @returns {Pattern} The regex pattern.
 */
export function lower(minRep, maxRep) {
  return new Pattern("[a-z]", (customSet = true)).rep(minRep, maxRep);
}

/**
 * Matches any character that is not a lowercase letter.
 * @param {number} [minRep] - The minimum number of characters to match.
 * @param {number} [maxRep] - The maximum number of characters to match.
 * @returns {Pattern} The regex pattern.
 */
export function notLower(minRep, maxRep) {
  return new Pattern("[^a-z]", (customSet = true), (negated = true)).rep(
    minRep,
    maxRep,
  );
}

/**
 * Matches any hex-digit character.
 * A hex-digit character is any letter A through F (uppercase or lowercase) or any digit (0-9).
 * @param {number} [minRep] - The minimum number of characters to match.
 * @param {number} [maxRep] - The maximum number of characters to match.
 * @returns {Pattern} The regex pattern.
 */
export function hexDigit(minRep, maxRep) {
  return new Pattern("[A-Fa-f\\d]", (customSet = true)).rep(minRep, maxRep);
}

/**
 * Matches anything but a hex-digit character.
 * A hex-digit character is any letter A through F (uppercase or lowercase) or any digit (0-9).
 * @param {number} [minRep] - The minimum number of characters to match.
 * @param {number} [maxRep] - The maximum number of characters to match.
 * @returns {Pattern} The regex pattern.
 */
export function notHexDigit(minRep, maxRep) {
  return new Pattern("[^A-Fa-f\\d]", (customSet = true), (negated = true)).rep(
    minRep,
    maxRep,
  );
}

/**
 * Matches any digit.
 * @param {number} [minRep] - The minimum number of characters to match.
 * @param {number} [maxRep] - The maximum number of characters to match.
 * @returns {Pattern} The regex pattern.
 */
export function digit(minRep, maxRep) {
  return new Pattern("\\d").rep(minRep, maxRep);
}

/**
 * Matches any character that is not a digit.
 * @param {number} [minRep] - The minimum number of characters to match.
 * @param {number} [maxRep] - The maximum number of characters to match.
 * @returns {Pattern} The regex pattern.
 */
export function notDigit(minRep, maxRep) {
  return new Pattern("\\D").rep(minRep, maxRep);
}

/**
 * Matches any whitespace character. (Whitespaces include space, tab, newline, carriage return, etc.)
 * @param {number} [minRep] - The minimum number of characters to match.
 * @param {number} [maxRep] - The maximum number of characters to match.
 * @returns {Pattern} The regex pattern.
 */
export function whitespace(minRep, maxRep) {
  return new Pattern("\\s").rep(minRep, maxRep);
}

/**
 * Matches any character that is not a whitespace character. (Whitespaces include space, tab, newline, carriage return, etc.)
 * @param {number} [minRep] - The minimum number of characters to match.
 * @param {number} [maxRep] - The maximum number of characters to match.
 * @returns {Pattern} The regex pattern.
 */
export function notWhitespace(minRep, maxRep) {
  return new Pattern("\\S").rep(minRep, maxRep);
}

/**
 * Matches a newline character.
 * @param {number} [minRep] - The minimum number of characters to match.
 * @param {number} [maxRep] - The maximum number of characters to match.
 * @returns {Pattern} The regex pattern.
 */
export function newline(minRep, maxRep) {
  return new Pattern("\\n").rep(minRep, maxRep);
}

/**
 * Matches any character that is not a newline.
 * @param {number} [minRep] - The minimum number of characters to match.
 * @param {number} [maxRep] - The maximum number of characters to match.
 * @returns {Pattern} The regex pattern.
 */
export function notNewline(minRep, maxRep) {
  return new Pattern(".").rep(minRep, maxRep);
}

/**
 * Matches a tab character.
 * @param {number} [minRep] - The minimum number of characters to match.
 * @param {number} [maxRep] - The maximum number of characters to match.
 * @returns {Pattern} The regex pattern.
 */
export function tab(minRep, maxRep) {
  return new Pattern("\\t").rep(minRep, maxRep);
}

/**
 * Matches a carriage return character.
 * @param {number} [minRep] - The minimum number of characters to match.
 * @param {number} [maxRep] - The maximum number of characters to match.
 * @returns {Pattern} The regex pattern.
 */
export function carriage(minRep, maxRep) {
  return new Pattern("\\r").rep(minRep, maxRep);
}

/**
 * Matches a boundary character.
 * @param {number} [minRep] - The minimum number of characters to match.
 * @param {number} [maxRep] - The maximum number of characters to match.
 * @returns {Pattern} The regex pattern.
 */
export function bound(minRep, maxRep) {
  return new Pattern("\\b").rep(minRep, maxRep);
}

/**
 * Matches any character that is not a boundary.
 * @param {number} [minRep] - The minimum number of characters to match.
 * @param {number} [maxRep] - The maximum number of characters to match.
 * @returns {Pattern} The regex pattern.
 */
export function notBound(minRep, maxRep) {
  return new Pattern("\\B").rep(minRep, maxRep);
}

/**
 * Matches the start of a line.
 * @returns {Pattern} The regex pattern.
 */
export function start() {
  return new Pattern("^");
}

/**
 * Matches the end of a line.
 * @returns {Pattern} The regex pattern.
 */
export function end() {
  return new Pattern("$");
}
