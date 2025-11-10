import { STRlingError, Pattern, lit } from "./pattern.js";

/**
 * Matches any one of the provided patterns (alternation/OR operation).
 *
 * This function creates a pattern that succeeds if any of the provided patterns
 * match at the current position. It's equivalent to the | operator in regular
 * expressions.
 *
 * @param {...(Pattern|string)} patterns - One or more patterns to be matched.
 *                                          Strings are automatically converted to literal patterns.
 * @returns {Pattern} A new Pattern object representing the alternation of all provided patterns.
 *
 * @throws {STRlingError} If any parameter is not a Pattern or string, or if duplicate named groups
 *                        are found across the patterns.
 *
 * @example
 * // Simple Use: Match either 'cat' or 'dog'
 * const pattern = s.anyOf('cat', 'dog');
 * /cat|dog/.test('I have a cat');  // true
 * /cat|dog/.test('I have a dog');  // true
 *
 * @example
 * // Advanced Use: Match different number formats
 * const pattern1 = s.merge(s.digit(3), s.letter(3));  // 3 digits then 3 letters
 * const pattern2 = s.merge(s.letter(3), s.digit(3));  // 3 letters then 3 digits
 * const eitherPattern = s.anyOf(pattern1, pattern2);
 * new RegExp(eitherPattern).test('ABC123');  // true
 * new RegExp(eitherPattern).test('123ABC');  // true
 *
 * @see {@link merge} For concatenating patterns sequentially
 * @see {@link may} For optional patterns
 */
export function anyOf(...patterns) {
    const cleanPatterns = patterns.map((pattern) => {
        if (typeof pattern === "string") {
            pattern = lit(pattern);
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

    const childNodes = cleanPatterns.map((pattern) => pattern.node);
    const node = {
        ir: "Alt",
        branches: childNodes,
    };

    const allNamedGroups = cleanPatterns.flatMap((p) => p.namedGroups || []);

    return new Pattern({
        node,
        namedGroups: allNamedGroups,
    });
}

/**
 * Makes the provided patterns optional (matches 0 or 1 times).
 *
 * This function creates a pattern that may or may not be present. If the pattern
 * is absent, the overall match can still succeed. This is equivalent to the ?
 * quantifier in regular expressions.
 *
 * @param {...(Pattern|string)} patterns - One or more patterns to be optionally matched.
 *                                          Strings are automatically converted to literal patterns.
 *                                          Multiple patterns are concatenated together.
 * @returns {Pattern} A new Pattern object representing the optional pattern(s).
 *
 * @throws {STRlingError} If any parameter is not a Pattern or string, or if duplicate named groups
 *                        are found.
 *
 * @example
 * // Simple Use: Match a letter with optional trailing digit
 * const pattern = s.merge(s.letter(), s.may(s.digit()));
 * 'A B2 C'.match(new RegExp(pattern, 'g'));  // ['A', 'B2', 'C']
 *
 * @example
 * // Advanced Use: Optional protocol in URL pattern
 * const protocol = s.may(s.merge(s.anyOf('http', 'https'), '://'));
 * const domain = s.merge(s.letter(1, 0), '.', s.letter(2, 3));
 * const urlPattern = s.merge(protocol, domain);
 * new RegExp(urlPattern).test('https://example.com');  // true
 * new RegExp(urlPattern).test('example.com');  // true
 *
 * @see {@link anyOf} For alternation between patterns
 * @see {@link merge} For concatenating patterns
 */
export function may(...patterns) {
    const cleanPatterns = patterns.map((pattern) => {
        if (typeof pattern === "string") {
            pattern = lit(pattern);
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

    let bodyNode;
    if (cleanPatterns.length === 1) {
        bodyNode = cleanPatterns[0].node;
    } else {
        bodyNode = {
            ir: "Seq",
            parts: cleanPatterns.map((pattern) => pattern.node),
        };
    }

    const node = {
        ir: "Quant",
        child: bodyNode,
        min: 0,
        max: 1,
        mode: "Greedy",
    };

    const allNamedGroups = cleanPatterns.flatMap((p) => p.namedGroups || []);

    return new Pattern({
        node,
        namedGroups: allNamedGroups,
    });
}

/**
 * Concatenates the provided patterns into a single sequential pattern.
 *
 * This function creates a pattern that matches all provided patterns in order,
 * one after another. It's the fundamental operation for building complex patterns
 * from simpler components.
 *
 * @param {...(Pattern|string)} patterns - One or more patterns to be concatenated.
 *                                          Strings are automatically converted to literal patterns.
 * @returns {Pattern} A new Pattern object representing the concatenated sequence.
 *
 * @throws {STRlingError} If any parameter is not a Pattern or string, or if duplicate named groups
 *                        are found across the patterns.
 *
 * @example
 * // Simple Use: Match digit followed by literal text
 * const pattern = s.merge(s.digit(), ',.');
 * const match = 'test5,.'.match(new RegExp(pattern));
 * match[0];  // '5,.'
 *
 * @example
 * // Advanced Use: Build a complete email pattern
 * const username = s.merge(s.alphaNum(1, 0), s.may(s.merge('.', s.alphaNum(1, 0))));
 * const atSign = s.lit('@');
 * const domain = s.merge(s.alphaNum(1, 0), '.', s.letter(2, 4));
 * const email = s.merge(username, atSign, domain);
 * new RegExp(email).test('user@example.com');  // true
 *
 * @see {@link anyOf} For alternation (OR operation)
 * @see {@link capture} For creating numbered capture groups
 * @see {@link group} For creating named capture groups
 */
export function merge(...patterns) {
    const cleanPatterns = patterns.map((pattern) => {
        if (typeof pattern === "string") {
            pattern = lit(pattern);
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

    const childNodes = cleanPatterns.map((pattern) => pattern.node);

    // If only one pattern, no need to wrap in a Seq
    if (childNodes.length === 1) {
        return cleanPatterns[0];
    }

    const node = {
        ir: "Seq",
        parts: childNodes,
    };

    const allNamedGroups = cleanPatterns.flatMap((p) => p.namedGroups || []);

    return new Pattern({
        node,
        namedGroups: allNamedGroups,
    });
}

/**
 * Creates a numbered capture group for extracting matched content by index.
 *
 * Capture groups allow you to extract specific portions of a matched pattern
 * using numeric indices. Unlike named groups, capture groups can be repeated
 * with quantifiers, and each repetition creates a new numbered group.
 *
 * @param {...(Pattern|string)} patterns - One or more patterns to be captured.
 *                                          Strings are automatically converted to literal patterns.
 *                                          Multiple patterns are concatenated.
 * @returns {Pattern} A new Pattern object representing the numbered capture group.
 *
 * @throws {STRlingError} If any parameter is not a Pattern or string, or if duplicate named groups
 *                        are found within the captured patterns.
 *
 * @example
 * // Simple Use: Capture a digit-comma-period sequence
 * const pattern = s.capture(s.digit(), ',.');
 * const match = '5,.'.match(new RegExp(pattern));
 * match[0];  // '5,.' (full match)
 * match[1];  // '5,.' (first capture group)
 *
 * @example
 * // Advanced Use: Multiple captures with repetition
 * const threeDigitGroup = s.capture(s.digit(3));
 * const fourGroups = threeDigitGroup.rep(4);
 * const text = "Here is a number: 111222333444";
 * const match = text.match(new RegExp(fourGroups));
 * match[0];  // '111222333444' (full match)
 * match[1];  // '111' (first capture)
 * match[2];  // '222' (second capture)
 * match[3];  // '333' (third capture)
 * match[4];  // '444' (fourth capture)
 *
 * @see {@link group} For creating named capture groups
 * @see {@link merge} For non-capturing concatenation
 */
export function capture(...patterns) {
    const cleanPatterns = patterns.map((pattern) => {
        if (typeof pattern === "string") {
            pattern = lit(pattern);
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

    // Count named groups and throw error if not unique
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

    let bodyNode;
    if (cleanPatterns.length === 1) {
        bodyNode = cleanPatterns[0].node;
    } else {
        bodyNode = {
            ir: "Seq",
            parts: cleanPatterns.map((pattern) => pattern.node),
        };
    }

    const node = {
        ir: "Group",
        capturing: true,
        name: null,
        body: bodyNode,
    };

    const allNamedGroups = cleanPatterns.flatMap((p) => p.namedGroups || []);

    return new Pattern({
        node,
        namedGroups: allNamedGroups,
        numberedGroup: true,
    });
}

/**
 * Creates a named capture group that can be referenced by name for extracting matched content.
 *
 * Named groups allow you to extract specific portions of a matched pattern using
 * descriptive names rather than numeric indices, making your code more readable
 * and maintainable.
 *
 * @param {string} name - The unique name for the group (e.g., 'area_code'). Must be a valid
 *                        identifier and must be unique within the entire pattern.
 * @param {...(Pattern|string)} patterns - One or more patterns to be captured.
 *                                          Strings are automatically converted to literal patterns.
 *                                          Multiple patterns are concatenated.
 * @returns {Pattern} A new Pattern object representing the named capture group.
 *
 * @throws {STRlingError} If name is not a string, if any pattern parameter is not a Pattern or
 *                        string, or if duplicate named groups are found.
 *
 * @example
 * // Simple Use: Capture a digit-comma-period sequence with a name
 * const pattern = s.group('my_group', s.digit(), ',.');
 * const match = '5,.'.match(new RegExp(pattern));
 * match.groups.my_group;  // '5,.'
 *
 * @example
 * // Advanced Use: Build a phone number pattern with named groups
 * const first = s.group("first", s.digit(3));
 * const second = s.group("second", s.digit(3));
 * const third = s.group("third", s.digit(4));
 * const phonePattern = s.merge(first, "-", second, "-", third);
 * const text = "Here is a phone number: 123-456-7890.";
 * const match = text.match(new RegExp(phonePattern));
 * match[0];              // '123-456-7890'
 * match.groups.first;    // '123'
 * match.groups.second;   // '456'
 * match.groups.third;    // '7890'
 *
 * @pitfall
 * Named groups CANNOT be repeated with quantifiers like .rep(1, 3) because
 * each repetition would create multiple groups with the same name, which is not
 * allowed. For repeatable patterns, use s.capture() for numbered groups or
 * s.merge() for non-capturing concatenation.
 *
 * @see {@link capture} For numbered, repeatable capture groups
 * @see {@link merge} For non-capturing concatenation
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
            pattern = lit(pattern);
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

    // Count named groups and throw error if not unique
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

    let bodyNode;
    if (cleanPatterns.length === 1) {
        bodyNode = cleanPatterns[0].node;
    } else {
        bodyNode = {
            ir: "Seq",
            parts: cleanPatterns.map((pattern) => pattern.node),
        };
    }

    const node = {
        ir: "Group",
        capturing: true,
        name: name,
        body: bodyNode,
    };

    const allNamedGroups = cleanPatterns.flatMap((p) => p.namedGroups || []);

    return new Pattern({
        node,
        namedGroups: [...allNamedGroups, name],
    });
}
