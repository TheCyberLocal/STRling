
import { Pattern, lit } from './pattern';

/**
 * Matches any letter (uppercase or lowercase) or digit.
 * @param {number} [minRep] - The minimum number of characters to match.
 * @param {number} [maxRep] - The maximum number of characters to match.
 * @returns {Pattern} The regex pattern.
 */
function alphaNum(minRep, maxRep) {
    return new Pattern('[A-Za-z0-9]', true).call(minRep, maxRep);
}

/**
 * Matches any character that is not a letter or digit.
 * @param {number} [minRep] - The minimum number of characters to match.
 * @param {number} [maxRep] - The maximum number of characters to match.
 * @returns {Pattern} The regex pattern.
 */
function notAlphaNum(minRep, maxRep) {
    return new Pattern('[^A-Za-z0-9]', true, true).call(minRep, maxRep);
}

/**
 * Matches any special character.
 * @param {number} [minRep] - The minimum number of characters to match.
 * @param {number} [maxRep] - The maximum number of characters to match.
 * @returns {Pattern} The regex pattern.
 */
function specialChar(minRep, maxRep) {
    const special = lit(`!"#$%&'()*+,-./:;<=>?@[\\]^_\`{|}~`);
    return new Pattern(`[${special}]`, true).call(minRep, maxRep);
}

/**
 * Matches any character that is not a special character.
 * @param {number} [minRep] - The minimum number of characters to match.
 * @param {number} [maxRep] - The maximum number of characters to match.
 * @returns {Pattern} The regex pattern.
 */
function notSpecialChar(minRep, maxRep) {
    const special = lit(`!"#$%&'()*+,-./:;<=>?@[\\]^_\`{|}~`);
    return new Pattern(`[^${special}]`, true, true).call(minRep, maxRep);
}

/**
 * Matches any letter (uppercase or lowercase).
 * @param {number} [minRep] - The minimum number of characters to match.
 * @param {number} [maxRep] - The maximum number of characters to match.
 * @returns {Pattern} The regex pattern.
 */
function letter(minRep, maxRep) {
    return new Pattern('[A-Za-z]', true).call(minRep, maxRep);
}

/**
 * Matches any character that is not a letter.
 * @param {number} [minRep] - The minimum number of characters to match.
 * @param {number} [maxRep] - The maximum number of characters to match.
 * @returns {Pattern} The regex pattern.
 */
function notLetter(minRep, maxRep) {
    return new Pattern('[^A-Za-z]', true, true).call(minRep, maxRep);
}

/**
 * Matches any uppercase letter.
 * @param {number} [minRep] - The minimum number of characters to match.
 * @param {number} [maxRep] - The maximum number of characters to match.
 * @returns {Pattern} The regex pattern.
 */
function upper(minRep, maxRep) {
    return new Pattern('[A-Z]', true).call(minRep, maxRep);
}

/**
 * Matches any character that is not an uppercase letter.
 * @param {number} [minRep] - The minimum number of characters to match.
 * @param {number} [maxRep] - The maximum number of characters to match.
 * @returns {Pattern} The regex pattern.
 */
function notUpper(minRep, maxRep) {
    return new Pattern('[^A-Z]', true, true).call(minRep, maxRep);
}

module.exports = {
    alphaNum,
    notAlphaNum,
    specialChar,
    notSpecialChar,
    letter,
    notLetter,
    upper,
    notUpper
};
