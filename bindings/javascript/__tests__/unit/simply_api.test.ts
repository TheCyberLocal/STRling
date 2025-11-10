/**
 * Test Design — simply_api.test.ts
 *
 * ## Purpose
 * This test suite validates the public-facing Simply API, ensuring all exported
 * functions work correctly and produce expected regex patterns. This provides
 * comprehensive coverage of the user-facing DSL that developers interact with directly.
 *
 * ## Description
 * The Simply API is the primary interface for building regex patterns. This suite
 * tests all public functions across the modules to ensure they:
 * 1. Accept valid inputs and produce correct patterns
 * 2. Reject invalid inputs with instructional errors
 * 3. Compose correctly with other API functions
 * 4. Generate expected regex output
 *
 * ## Scope
 * - **In scope:**
 *   - All public functions in `simply/sets.js`
 *   - All public functions in `simply/constructors.js`
 *   - All public functions in `simply/lookarounds.js`
 *   - All public functions in `simply/static.js`
 *   - Integration between API functions
 *   - Error handling and validation
 *
 * - **Out of scope:**
 *   - Internal parser, compiler, and emitter logic (covered in other test files)
 *   - Low-level AST node manipulation
 *   - Performance testing
 */

import * as s from '../../src/STRling/simply/index.js';
import { Compiler } from '../../src/STRling/core/compiler';
import { emit as emitPcre2 } from '../../src/STRling/emitters/pcre2';

// Helper function to compile Simply API patterns to regex
function toRegex(pattern: any): RegExp {
    const compiler = new Compiler();
    const ir = compiler.compile(pattern.node);
    const regexStr = emitPcre2(ir);
    return new RegExp(regexStr);
}

// =============================================================================
// Category A: Sets Module Tests
// =============================================================================

describe('Sets Module', () => {
    // -------------------------------------------------------------------------
    // A.1: notBetween() tests
    // -------------------------------------------------------------------------

    describe('notBetween()', () => {
        test('simple case - digits', () => {
            const pattern = s.notBetween(0, 9);
            const regex = toRegex(pattern);
            // Should match non-digits
            expect(regex.test('A')).toBe(true);
            expect(regex.test(' ')).toBe(true);
            expect(regex.test('5')).toBe(false);
        });

        test('typical case - lowercase letters', () => {
            const pattern = s.notBetween('a', 'z');
            const regex = toRegex(pattern);
            // Should match anything except lowercase letters
            expect(regex.test('A')).toBe(true);
            expect(regex.test('5')).toBe(true);
            expect(regex.test('!')).toBe(true);
            expect(regex.test('m')).toBe(false);
        });

        test('interaction with repetition', () => {
            const pattern = s.notBetween('a', 'e', 2, 4);
            const regex = toRegex(pattern);
            // Should match 2-4 characters that are not a-e
            const match = 'XYZ'.match(regex);
            expect(match).not.toBeNull();
            expect(match![0]).toBe('XYZ');
        });

        test('edge case - same start and end', () => {
            const pattern = s.notBetween('a', 'a');
            const regex = toRegex(pattern);
            // Should match everything except 'a'
            expect(regex.test('b')).toBe(true);
            expect(regex.test('a')).toBe(false);
        });

        test('edge case - uppercase range', () => {
            const pattern = s.notBetween('A', 'Z');
            const regex = toRegex(pattern);
            // Should match anything except uppercase letters
            expect(regex.test('a')).toBe(true);
            expect(regex.test('M')).toBe(false);
        });

        test('error - invalid range (start > end)', () => {
            expect(() => s.notBetween(9, 0)).toThrow();
        });

        test('error - mixed types', () => {
            expect(() => s.notBetween('a' as any, 9 as any)).toThrow();
        });

        test('error - mixed case', () => {
            expect(() => s.notBetween('a', 'Z')).toThrow();
        });
    });

    // -------------------------------------------------------------------------
    // A.2: inChars() tests
    // -------------------------------------------------------------------------

    describe('inChars()', () => {
        test('simple case - string literals', () => {
            const pattern = s.inChars('abc');
            const regex = toRegex(pattern);
            // Should match any of a, b, or c
            expect(regex.test('a')).toBe(true);
            expect(regex.test('b')).toBe(true);
            expect(regex.test('c')).toBe(true);
            expect(regex.test('d')).toBe(false);
        });

        test('typical case - mixed patterns', () => {
            const pattern = s.inChars(s.digit(), s.letter(), '.,');
            const regex = toRegex(pattern);
            // Should match digits, letters, or . and ,
            expect(regex.test('5')).toBe(true);
            expect(regex.test('X')).toBe(true);
            expect(regex.test('.')).toBe(true);
            expect(regex.test(',')).toBe(true);
            expect(regex.test('@')).toBe(false);
        });

        test('edge case - single character', () => {
            const pattern = s.inChars('x');
            const regex = toRegex(pattern);
            expect(regex.test('x')).toBe(true);
            expect(regex.test('y')).toBe(false);
        });

        test('error - composite pattern', () => {
            expect(() => s.inChars(s.merge(s.digit(), s.letter()))).toThrow();
        });
    });

    // -------------------------------------------------------------------------
    // A.3: notInChars() tests
    // -------------------------------------------------------------------------

    describe('notInChars()', () => {
        test('simple case - string literals', () => {
            const pattern = s.notInChars('abc');
            const regex = toRegex(pattern);
            // Should match anything except a, b, or c
            expect(regex.test('d')).toBe(true);
            expect(regex.test('5')).toBe(true);
            expect(regex.test('a')).toBe(false);
            expect(regex.test('b')).toBe(false);
        });

        test('typical case - exclude digits and letters', () => {
            const pattern = s.notInChars(s.digit(), s.letter());
            const regex = toRegex(pattern);
            // Should match anything except digits and letters
            expect(regex.test('@')).toBe(true);
            expect(regex.test(' ')).toBe(true);
            expect(regex.test('5')).toBe(false);
            expect(regex.test('A')).toBe(false);
        });

        test('interaction with merge', () => {
            const pattern = s.merge(s.notInChars('aeiou'), s.digit());
            const regex = toRegex(pattern);
            // Should match a non-vowel followed by a digit
            const match = 'x5'.match(regex);
            expect(match).not.toBeNull();
            expect(match![0]).toBe('x5');
        });
    });
});

// =============================================================================
// Category B: Constructors Module Tests
// =============================================================================

describe('Constructors Module', () => {
    // -------------------------------------------------------------------------
    // B.1: anyOf() tests
    // -------------------------------------------------------------------------

    describe('anyOf()', () => {
        test('simple case - string alternatives', () => {
            const pattern = s.anyOf('cat', 'dog');
            const regex = toRegex(pattern);
            // Should match either 'cat' or 'dog'
            expect(regex.test('I have a cat')).toBe(true);
            expect(regex.test('I have a dog')).toBe(true);
            expect(regex.test('I have a bird')).toBe(false);
        });

        test('typical case - mixed patterns', () => {
            const pattern = s.anyOf(s.digit(3), s.letter(3));
            const regex = toRegex(pattern);
            // Should match either 3 digits or 3 letters
            expect(regex.test('999')).toBe(true);
            expect(regex.test('xyz')).toBe(true);
        });

        test('interaction in merge', () => {
            const prefix = s.anyOf('Mr', 'Ms', 'Dr');
            const pattern = s.merge(prefix, '.', s.whitespace(), s.letter(1, 0));
            const regex = toRegex(pattern);
            // Should match titles like "Mr. Smith", "Ms. Jones", etc.
            expect(regex.test('Mr. Smith')).toBe(true);
            expect(regex.test('Dr. Watson')).toBe(true);
        });

        test('error - duplicate named groups', () => {
            const group1 = s.group('name', s.digit());
            const group2 = s.group('name', s.letter());
            expect(() => s.anyOf(group1, group2)).toThrow(/unique/i);
        });
    });

    // -------------------------------------------------------------------------
    // B.2: merge() tests
    // -------------------------------------------------------------------------

    describe('merge()', () => {
        test('simple case - string literals', () => {
            const pattern = s.merge('hello', ' ', 'world');
            const regex = toRegex(pattern);
            // Should match exact sequence 'hello world'
            expect(regex.test('hello world')).toBe(true);
            expect(regex.test('hello')).toBe(false);
        });

        test('typical case - complex pattern', () => {
            const areaCode = s.digit(3);
            const separator = s.inChars('- ');
            const pattern = s.merge(areaCode, separator, s.digit(3), separator, s.digit(4));
            const regex = toRegex(pattern);
            // Should match phone number patterns
            expect(regex.test('555-123-4567')).toBe(true);
            expect(regex.test('555 123 4567')).toBe(true);
        });

        test('interaction with quantifiers', () => {
            const word = s.letter(1, 0);
            const pattern = s.merge(word, s.whitespace(1, 0), word);
            const regex = toRegex(pattern);
            // Should match words separated by whitespace
            expect(regex.test('hello world')).toBe(true);
        });

        test('error - duplicate named groups', () => {
            const group1 = s.group('value', s.digit());
            const group2 = s.group('value', s.digit());
            expect(() => s.merge(group1, group2)).toThrow(/unique/i);
        });
    });
});

// =============================================================================
// Category C: Lookarounds Module Tests
// =============================================================================

describe('Lookarounds Module', () => {
    // -------------------------------------------------------------------------
    // C.1: notAhead() tests
    // -------------------------------------------------------------------------

    describe('notAhead()', () => {
        test('simple case', () => {
            const pattern = s.merge(s.digit(), s.notAhead(s.letter()));
            const regex = toRegex(pattern);
            // Should match digit NOT followed by letter
            expect(regex.test('56')).toBe(true);
            expect(regex.test('5 ')).toBe(true);
            expect(regex.test('5A')).toBe(false);
        });

        test('typical case - identifier', () => {
            const identifier = s.merge(s.letter(), s.alphaNum(0, 0));
            const pattern = s.merge(identifier, s.notAhead(s.merge('_tmp', s.end())));
            const regex = toRegex(pattern);
            expect(regex.test('myvar')).toBe(true);
        });

        test('interaction with boundary', () => {
            const pattern = s.merge(s.letter(1, 0), s.notAhead(s.digit()));
            const regex = toRegex(pattern);
            expect(regex.test('hello')).toBe(true);
            const match = regex.exec('test123');
            expect(match).not.toBeNull();
        });
    });

    // -------------------------------------------------------------------------
    // C.2: notBehind() tests
    // -------------------------------------------------------------------------

    describe('notBehind()', () => {
        test('simple case', () => {
            const pattern = s.merge(s.notBehind(s.digit()), s.letter());
            const regex = toRegex(pattern);
            // Should match letter NOT preceded by digit
            const match = 'AB'.match(regex);
            expect(match).not.toBeNull();
            expect(match![0]).toBe('A');
        });

        test('typical case - word prefix', () => {
            const pattern = s.merge(s.notBehind(s.lit('im')), s.lit('possible'));
            const regex = toRegex(pattern);
            expect(regex.test('possible')).toBe(true);
        });

        test('interaction with start', () => {
            const pattern = s.merge(s.notBehind(s.start()), s.letter());
            const regex = toRegex(pattern);
            // Pattern compiles successfully
            expect(pattern.toString()).toBeDefined();
        });
    });
});

// =============================================================================
// Category D: Static Module Tests
// =============================================================================

describe('Static Module', () => {
    // -------------------------------------------------------------------------
    // D.1: alphaNum() tests
    // -------------------------------------------------------------------------

    describe('alphaNum()', () => {
        test('simple case', () => {
            const pattern = s.alphaNum();
            const regex = toRegex(pattern);
            expect(regex.test('A')).toBe(true);
            expect(regex.test('5')).toBe(true);
            expect(regex.test('z')).toBe(true);
            expect(regex.test('@')).toBe(false);
        });

        test('typical case - username', () => {
            const pattern = s.alphaNum(3, 16);
            const regex = toRegex(pattern);
            expect(regex.exec('user123')).not.toBeNull();
            expect(regex.exec('ABC')).not.toBeNull();
            expect(regex.exec('ab')).toBeNull(); // Too short
        });

        test('interaction with merge', () => {
            const pattern = s.merge(s.letter(), s.alphaNum(0, 0));
            const regex = toRegex(pattern);
            expect(regex.exec('user123')).not.toBeNull();
            expect(regex.exec('123user')).toBeNull();
        });
    });

    // -------------------------------------------------------------------------
    // D.2: notAlphaNum() tests
    // -------------------------------------------------------------------------

    describe('notAlphaNum()', () => {
        test('simple case', () => {
            const pattern = s.notAlphaNum();
            const regex = toRegex(pattern);
            expect(regex.test('@')).toBe(true);
            expect(regex.test(' ')).toBe(true);
            expect(regex.test('A')).toBe(false);
            expect(regex.test('5')).toBe(false);
        });

        test('typical case - delimiter', () => {
            const pattern = s.notAlphaNum(1, 0);
            const regex = toRegex(pattern);
            const match = 'word@@word'.match(regex);
            expect(match).not.toBeNull();
            expect(match![0]).toContain('@@');
        });
    });

    // -------------------------------------------------------------------------
    // D.3: upper() tests
    // -------------------------------------------------------------------------

    describe('upper()', () => {
        test('simple case', () => {
            const pattern = s.upper();
            const regex = toRegex(pattern);
            expect(regex.test('A')).toBe(true);
            expect(regex.test('Z')).toBe(true);
            expect(regex.test('a')).toBe(false);
            expect(regex.test('5')).toBe(false);
        });

        test('typical case - acronym', () => {
            const pattern = s.upper(2, 5);
            const regex = toRegex(pattern);
            expect(regex.test('NASA')).toBe(true);
            expect(regex.test('FBI')).toBe(true);
        });
    });

    // -------------------------------------------------------------------------
    // D.4: notUpper() tests
    // -------------------------------------------------------------------------

    describe('notUpper()', () => {
        test('simple case', () => {
            const pattern = s.notUpper();
            const regex = toRegex(pattern);
            expect(regex.test('a')).toBe(true);
            expect(regex.test('5')).toBe(true);
            expect(regex.test('A')).toBe(false);
        });
    });

    // -------------------------------------------------------------------------
    // D.5: notLower() tests
    // -------------------------------------------------------------------------

    describe('notLower()', () => {
        test('simple case', () => {
            const pattern = s.notLower();
            const regex = toRegex(pattern);
            expect(regex.test('A')).toBe(true);
            expect(regex.test('5')).toBe(true);
            expect(regex.test('a')).toBe(false);
        });
    });

    // -------------------------------------------------------------------------
    // D.6: notLetter() tests
    // -------------------------------------------------------------------------

    describe('notLetter()', () => {
        test('simple case', () => {
            const pattern = s.notLetter();
            const regex = toRegex(pattern);
            expect(regex.test('5')).toBe(true);
            expect(regex.test('@')).toBe(true);
            expect(regex.test('A')).toBe(false);
            expect(regex.test('z')).toBe(false);
        });
    });

    // -------------------------------------------------------------------------
    // D.7: notSpecialChar() tests
    // -------------------------------------------------------------------------

    describe('notSpecialChar()', () => {
        test('simple case', () => {
            const pattern = s.notSpecialChar();
            const regex = toRegex(pattern);
            expect(regex.test('A')).toBe(true);
            expect(regex.test('5')).toBe(true);
        });
    });

    // -------------------------------------------------------------------------
    // D.8: notHexDigit() tests
    // -------------------------------------------------------------------------

    describe('notHexDigit()', () => {
        test('simple case', () => {
            const pattern = s.notHexDigit();
            const regex = toRegex(pattern);
            expect(regex.test('G')).toBe(true);
            expect(regex.test('z')).toBe(true);
            expect(regex.test('A')).toBe(false);
            expect(regex.test('5')).toBe(false);
            expect(regex.test('f')).toBe(false);
        });
    });

    // -------------------------------------------------------------------------
    // D.9: notDigit() tests
    // -------------------------------------------------------------------------

    describe('notDigit()', () => {
        test('simple case', () => {
            const pattern = s.notDigit();
            const regex = toRegex(pattern);
            expect(regex.test('A')).toBe(true);
            expect(regex.test(' ')).toBe(true);
            expect(regex.test('5')).toBe(false);
        });
    });

    // -------------------------------------------------------------------------
    // D.10: notWhitespace() tests
    // -------------------------------------------------------------------------

    describe('notWhitespace()', () => {
        test('simple case', () => {
            const pattern = s.notWhitespace();
            const regex = toRegex(pattern);
            expect(regex.test('A')).toBe(true);
            expect(regex.test('5')).toBe(true);
            expect(regex.test(' ')).toBe(false);
            expect(regex.test('\t')).toBe(false);
        });
    });

    // -------------------------------------------------------------------------
    // D.11: notNewline() tests
    // -------------------------------------------------------------------------

    describe('notNewline()', () => {
        test('simple case', () => {
            const pattern = s.notNewline();
            const regex = toRegex(pattern);
            // Note: Implementation may use \r (carriage return)
            expect(regex.test('\r')).toBe(true);
        });
    });

    // -------------------------------------------------------------------------
    // D.12: notBound() tests
    // -------------------------------------------------------------------------

    describe('notBound()', () => {
        test('simple case', () => {
            const pattern = s.notBound();
            const regex = toRegex(pattern);
            // Word boundary tests are complex, just verify it compiles
            expect(regex.toString()).toBeDefined();
        });
    });
});
