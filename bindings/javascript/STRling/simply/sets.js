
import { STRlingError, Pattern, lit } from './pattern';

// User Char Sets

/**
 * Matches all characters within and including the start and end of a letter or number range.
 * @param {string|number} start - The starting character or digit of the range.
 * @param {string|number} end - The ending character or digit of the range.
 * @param {number} [minRep] - The minimum number of characters to match.
 * @param {number} [maxRep] - The maximum number of characters to match.
 * @returns {Pattern} The regex pattern.
 * @throws {STRlingError} If the arguments are invalid.
 */
function between(start, end, minRep, maxRep) {
    if ((typeof start !== 'string' || typeof end !== 'string') && (typeof start !== 'number' || typeof end !== 'number')) {
        const message = `
        Method: simply.between(start, end)

        The start and end arguments must both be integers (0-9) or letters of the same case (A-Z or a-z).
        `;
        throw new STRlingError(message);
    }

    let newPattern;

    if (typeof start === 'number') {
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

    if (typeof start === 'string') {
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

        if ((start.toLowerCase() === start && end.toLowerCase() !== end) || (start.toUpperCase() === start && end.toUpperCase() !== end)) {
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

    return new Pattern(newPattern, true).call(minRep, maxRep);
}

/**
 * Matches any character not within or including the start and end of a letter or digit range.
 * @param {string|number} start - The starting character or digit of the range.
 * @param {string|number} end - The ending character or digit of the range.
 * @param {number} [minRep] - The minimum number of characters to match.
 * @param {number} [maxRep] - The maximum number of characters to match.
 * @returns {Pattern} The regex pattern.
 * @throws {STRlingError} If the arguments are invalid.
 */
function notBetween(start, end, minRep, maxRep) {
    if ((typeof start !== 'string' || typeof end !== 'string') && (typeof start !== 'number' || typeof end !== 'number')) {
        const message = `
        Method: simply.not_between(start, end)

        The start and end arguments must both be integers (0-9) or letters of the same case (A-Z or a-z).
        `;
        throw new STRlingError(message);
    }

    let newPattern;

    if (typeof start === 'number') {
        if (start > end) {
            const message = `
            Method: simply.not_between(start, end)

            The start integer must not be greater than the end integer.
            `;
            throw new STRlingError(message);
        }

        if (start < 0 || start > 9 || end < 0 || end > 9) {
            const message = `
            Method: simply.not_between(start, end)

            The start and end integers must be single digits (0-9).
            `;
            throw new STRlingError(message);
        }

        newPattern = `[^${start}-${end}]`;
    }

    if (typeof start === 'string') {
        if (!/^[a-zA-Z]$/.test(start) || !/^[a-zA-Z]$/.test(end)) {
            const message = `
            Method: simply.not_between(start, end)

            The start and end must be alphabetical characters.
            `;
            throw new STRlingError(message);
        }

        if (start.length !== 1 || end.length !== 1) {
            const message = `
            Method: simply.not_between(start, end)

            The start and end characters must be single letters.
            `;
            throw new STRlingError(message);
        }

        if ((start.toLowerCase() === start && end.toLowerCase() !== end) || (start.toUpperCase() === start && end.toUpperCase() !== end)) {
            const message = `
            Method: simply.not_between(start, end)

            The start and end characters must be of the same case.
            `;
            throw new STRlingError(message);
        }

        if (start > end) {
            const message = `
            Method: simply.not_between(start, end)

            The start character must not be lexicographically greater than the end character.
            `;
            throw new STRlingError(message);
        }

        newPattern = `[^${start}-${end}]`;
    }

    return new Pattern(newPattern, true, true).call(minRep, maxRep);
}

module.exports = {
    between,
    notBetween
};
