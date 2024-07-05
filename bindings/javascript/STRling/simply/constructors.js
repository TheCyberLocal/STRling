import { STRlingError, Pattern, lit } from "./pattern";

/**
 * Matches any provided pattern, including patterns consisting of subpatterns.
 * @param {...(Pattern|string)} patterns - One or more patterns to be matched.
 * @returns {Pattern} A Pattern object representing the OR combination of the given patterns.
 * @throws {STRlingError} If any pattern is invalid or named groups are not unique.
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
    pattern.named_groups.forEach((groupName) => {
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
  if (duplicates.length > 0) {
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

  return new Pattern(newPattern, composite=true, namedGroups=subNames);
}

/**
 * Optionally matches the provided patterns. If this pattern is absent, surrounding patterns can still match.
 * @param {...(Pattern|string)} patterns - One or more patterns to be optionally matched.
 * @returns {Pattern} A Pattern object representing the optional match of the given patterns.
 * @throws {STRlingError} If any pattern is invalid or named groups are not unique.
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
    pattern.named_groups.forEach((groupName) => {
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
  if (duplicates.length > 0) {
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

  return new Pattern(newPattern, composite=true, namedGroups=subNames);
}

/**
 * Combines the provided patterns into one larger pattern.
 * @param {...(Pattern|string)} patterns - One or more patterns to be concatenated.
 * @returns {Pattern} A Pattern object representing the concatenation of the given patterns.
 * @throws {STRlingError} If any pattern is invalid or named groups are not unique.
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
    pattern.named_groups.forEach((groupName) => {
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
  if (duplicates.length > 0) {
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

  return new Pattern(newPattern, composite=true, namedGroups=subNames);
}

/**
 * Creates a numbered group that can be indexed for extracting this part of the match.
 * Captures cannot be invoked with a range.
 * @param {...(Pattern|string)} patterns - One or more patterns to be captured.
 * @returns {Pattern} A Pattern object representing the capturing group of the given patterns.
 * @throws {STRlingError} If any pattern is invalid or named groups are not unique.
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

  const namedGroupCounts = {};

  cleanPatterns.forEach((pattern) => {
    pattern.named_groups.forEach((groupName) => {
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
  if (duplicates.length > 0) {
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

  return new Pattern(newPattern, composite=true, numberedGroup=true, namedGroups=subNames);
}

/**
 * Creates a unique named group that can be referenced for extracting this part of the match.
 * Groups cannot be invoked with a range.
 * @param {string} name - The name of the capturing group.
 * @param {...(Pattern|string)} patterns - One or more patterns to be captured.
 * @returns {Pattern} A Pattern object representing the named capturing group of the given patterns.
 * @throws {STRlingError} If the name is invalid, any pattern is invalid, or named groups are not unique.
 */
export function group(name, ...patterns) {
  if (typeof name !== "string") {
    const message = `
        Method: simply.group(name, ...patterns)

        The group is missing a specified name.
        The name parameter must be a string like 'group_name'.
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

  const namedGroupCounts = {};

  cleanPatterns.forEach((pattern) => {
    pattern.named_groups.forEach((groupName) => {
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
  if (duplicates.length > 0) {
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
  const newPattern = `(?P<${name}>${joined})`;

  return new Pattern(newPattern, composite=true, namedGroups=[name, ...subNames]);
}
