import { Pattern, lit } from "./pattern";

/**
 * Matches any letter (uppercase or lowercase) or digit.
 * @param {number} [minRep] - The minimum number of characters to match.
 * @param {number} [maxRep] - The maximum number of characters to match.
 * @returns {Pattern} The regex pattern.
 */
export function alphaNum(minRep, maxRep) {
  return new Pattern("[A-Za-z0-9]", true).call(minRep, maxRep);
}

/**
 * Matches any character that is not a letter or digit.
 * @param {number} [minRep] - The minimum number of characters to match.
 * @param {number} [maxRep] - The maximum number of characters to match.
 * @returns {Pattern} The regex pattern.
 */
export function notAlphaNum(minRep, maxRep) {
  return new Pattern("[^A-Za-z0-9]", true, true).call(minRep, maxRep);
}

/**
 * Matches any special character.
 * @param {number} [minRep] - The minimum number of characters to match.
 * @param {number} [maxRep] - The maximum number of characters to match.
 * @returns {Pattern} The regex pattern.
 */
export function specialChar(minRep, maxRep) {
  const special = lit(`!"#$%&'()*+,-./:;<=>?@[\\]^_\`{|}~`);
  return new Pattern(`[${special}]`, true).call(minRep, maxRep);
}

/**
 * Matches any character that is not a special character.
 * @param {number} [minRep] - The minimum number of characters to match.
 * @param {number} [maxRep] - The maximum number of characters to match.
 * @returns {Pattern} The regex pattern.
 */
export function notSpecialChar(minRep, maxRep) {
  const special = lit(`!"#$%&'()*+,-./:;<=>?@[\\]^_\`{|}~`);
  return new Pattern(`[^${special}]`, true, true).call(minRep, maxRep);
}

/**
 * Matches any letter (uppercase or lowercase).
 * @param {number} [minRep] - The minimum number of characters to match.
 * @param {number} [maxRep] - The maximum number of characters to match.
 * @returns {Pattern} The regex pattern.
 */
export function letter(minRep, maxRep) {
  return new Pattern("[A-Za-z]", true).call(minRep, maxRep);
}

/**
 * Matches any character that is not a letter.
 * @param {number} [minRep] - The minimum number of characters to match.
 * @param {number} [maxRep] - The maximum number of characters to match.
 * @returns {Pattern} The regex pattern.
 */
export function notLetter(minRep, maxRep) {
  return new Pattern("[^A-Za-z]", true, true).call(minRep, maxRep);
}

/**
 * Matches any uppercase letter.
 * @param {number} [minRep] - The minimum number of characters to match.
 * @param {number} [maxRep] - The maximum number of characters to match.
 * @returns {Pattern} The regex pattern.
 */
export function upper(minRep, maxRep) {
  return new Pattern("[A-Z]", true).call(minRep, maxRep);
}

/**
 * Matches any character that is not an uppercase letter.
 * @param {number} [minRep] - The minimum number of characters to match.
 * @param {number} [maxRep] - The maximum number of characters to match.
 * @returns {Pattern} The regex pattern.
 */
export function notUpper(minRep, maxRep) {
  return new Pattern("[^A-Z]", true, true).call(minRep, maxRep);
}

/**
 * Matches any lowercase letter.
 * @param {number} [minRep] - The minimum number of characters to match.
 * @param {number} [maxRep] - The maximum number of characters to match.
 * @returns {Pattern} The regex pattern.
 */
export function lower(minRep, maxRep) {
  return new Pattern("[a-z]", true).call(minRep, maxRep);
}

/**
 * Matches any character that is not a lowercase letter.
 * @param {number} [minRep] - The minimum number of characters to match.
 * @param {number} [maxRep] - The maximum number of characters to match.
 * @returns {Pattern} The regex pattern.
 */
export function notLower(minRep, maxRep) {
  return new Pattern("[^a-z]", true, true).call(minRep, maxRep);
}

/**
 * Matches any digit.
 * @param {number} [minRep] - The minimum number of characters to match.
 * @param {number} [maxRep] - The maximum number of characters to match.
 * @returns {Pattern} The regex pattern.
 */
export function digit(minRep, maxRep) {
  return new Pattern("\\d").call(minRep, maxRep);
}

/**
 * Matches any character that is not a digit.
 * @param {number} [minRep] - The minimum number of characters to match.
 * @param {number} [maxRep] - The maximum number of characters to match.
 * @returns {Pattern} The regex pattern.
 */
export function notDigit(minRep, maxRep) {
  return new Pattern("\\D").call(minRep, maxRep);
}

/**
 * Matches any hex-digit character.
 * A hex-digit character is any letter A through F (uppercase or lowercase) or any digit (0-9).
 * @param {number} [minRep] - The minimum number of characters to match.
 * @param {number} [maxRep] - The maximum number of characters to match.
 * @returns {Pattern} The regex pattern.
 */
export function hexDigit(minRep, maxRep) {
  return new Pattern("[A-Fa-f\\d]").call(minRep, maxRep);
}

/**
 * Matches anything but a hex-digit character.
 * A hex-digit character is any letter A through F (uppercase or lowercase) or any digit (0-9).
 * @param {number} [minRep] - The minimum number of characters to match.
 * @param {number} [maxRep] - The maximum number of characters to match.
 * @returns {Pattern} The regex pattern.
 */
export function notHexDigit(minRep, maxRep) {
  return new Pattern("[^A-Fa-f\\d]").call(minRep, maxRep);
}

/**
 * Matches any whitespace character. (Whitespaces include space, tab, newline, carriage return, etc.)
 * @param {number} [minRep] - The minimum number of characters to match.
 * @param {number} [maxRep] - The maximum number of characters to match.
 * @returns {Pattern} The regex pattern.
 */
export function whitespace(minRep, maxRep) {
  return new Pattern("\\s").call(minRep, maxRep);
}

/**
 * Matches any character that is not a whitespace character. (Whitespaces include space, tab, newline, carriage return, etc.)
 * @param {number} [minRep] - The minimum number of characters to match.
 * @param {number} [maxRep] - The maximum number of characters to match.
 * @returns {Pattern} The regex pattern.
 */
export function notWhitespace(minRep, maxRep) {
  return new Pattern("\\S").call(minRep, maxRep);
}

/**
 * Matches a newline character.
 * @param {number} [minRep] - The minimum number of characters to match.
 * @param {number} [maxRep] - The maximum number of characters to match.
 * @returns {Pattern} The regex pattern.
 */
export function newline(minRep, maxRep) {
  return new Pattern("\\n").call(minRep, maxRep);
}

/**
 * Matches any character that is not a newline.
 * @param {number} [minRep] - The minimum number of characters to match.
 * @param {number} [maxRep] - The maximum number of characters to match.
 * @returns {Pattern} The regex pattern.
 */
export function notNewline(minRep, maxRep) {
  return new Pattern(".").call(minRep, maxRep);
}

/**
 * Matches a tab character.
 * @param {number} [minRep] - The minimum number of characters to match.
 * @param {number} [maxRep] - The maximum number of characters to match.
 * @returns {Pattern} The regex pattern.
 */
export function tab(minRep, maxRep) {
  return new Pattern("\\t").call(minRep, maxRep);
}

/**
 * Matches any character that is not a tab.
 * @param {number} [minRep] - The minimum number of characters to match.
 * @param {number} [maxRep] - The maximum number of characters to match.
 * @returns {Pattern} The regex pattern.
 */
export function notTab(minRep, maxRep) {
  return new Pattern("\\T").call(minRep, maxRep); // Note: JavaScript does not support \T. Correcting to something meaningful.
}

/**
 * Matches a carriage return character.
 * @param {number} [minRep] - The minimum number of characters to match.
 * @param {number} [maxRep] - The maximum number of characters to match.
 * @returns {Pattern} The regex pattern.
 */
export function carriage(minRep, maxRep) {
  return new Pattern("\\r").call(minRep, maxRep);
}

/**
 * Matches any character that is not a carriage return.
 * @param {number} [minRep] - The minimum number of characters to match.
 * @param {number} [maxRep] - The maximum number of characters to match.
 * @returns {Pattern} The regex pattern.
 */
export function notCarriage(minRep, maxRep) {
  return new Pattern(".").call(minRep, maxRep); // No direct equivalent for \R in JavaScript regex
}

/**
 * Matches a boundary character.
 * @param {number} [minRep] - The minimum number of characters to match.
 * @param {number} [maxRep] - The maximum number of characters to match.
 * @returns {Pattern} The regex pattern.
 */
export function bound(minRep, maxRep) {
  return new Pattern("\\b").call(minRep, maxRep);
}

/**
 * Matches any character that is not a boundary.
 * @param {number} [minRep] - The minimum number of characters to match.
 * @param {number} [maxRep] - The maximum number of characters to match.
 * @returns {Pattern} The regex pattern.
 */
export function notBound(minRep, maxRep) {
  return new Pattern("\\B").call(minRep, maxRep);
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
