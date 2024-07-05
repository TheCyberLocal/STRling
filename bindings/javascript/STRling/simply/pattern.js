/**
 * Custom error class for STRling.
 * @extends {Error}
 */
class STRlingError extends Error {
  /**
   * Creates an instance of STRlingError.
   * @param {string} message - The error message.
   */
  constructor(message) {
    const formattedMessage = message.replace("\n", "\n\t");
    super(formattedMessage);
    this.name = "STRlingError";
    this.message = formattedMessage;
  }

  /**
   * Returns the error message as a string.
   * @returns {string} The error message.
   */
  toString() {
    return `\n\nSTRlingError: Invalid Pattern Attempted.\n\n\t${this.message}`;
  }
}

/**
 * Escapes a string to be used as a regex pattern.
 * @param {string} text - The text to escape.
 * @returns {Pattern} The escaped pattern.
 */
function lit(text) {
  const escapedText = text
    .replace(/[.*+?^${}()|[\]\\]/g, "\\$&")
    .replace(/\//g, "\\/");
  return new Pattern(escapedText);
}

/**
 * Generates a repetition pattern string.
 * @param {number} [minRep] - The minimum number of repetitions.
 * @param {number} [maxRep] - The maximum number of repetitions.
 * @returns {string} The repetition pattern string.
 * @throws {STRlingError} If minRep is greater than maxRep.
 */
function repeat(minRep, maxRep) {
  if (minRep !== undefined && maxRep !== undefined) {
    if (maxRep === 0) {
      return `{${minRep},}`;
    }
    if (minRep > maxRep) {
      const message = `
            Method: Pattern.__call__(minRep, maxRep)

            The minRep must not be greater than the maxRep.

            Ensure the lesser number is on the left and the greater number is on the right.
            `;
      throw new STRlingError(message);
    }
    return `{${minRep},${maxRep}}`;
  } else if (minRep !== undefined) {
    return `{${minRep}}`;
  } else {
    return "";
  }
}

/**
 * Represents a regex pattern.
 */
class Pattern {
  /**
   * Creates an instance of Pattern.
   * @param {string} pattern - The regex pattern.
   * @param {boolean} [customSet=false] - Indicates if the pattern is a custom character set.
   * @param {boolean} [negated=false] - Indicates if the pattern is negated.
   * @param {boolean} [composite=false] - Indicates if the pattern is composite.
   * @param {Array} [namedGroups=[]] - List of named groups.
   * @param {boolean} [numberedGroup=false] - Indicates if the pattern is a numbered group.
   */
  constructor(
    pattern,
    customSet = false,
    negated = false,
    composite = false,
    namedGroups = [],
    numberedGroup = false,
  ) {
    this.pattern = pattern;
    this.customSet = customSet;
    this.negated = negated;
    this.composite = composite;
    this.namedGroups = namedGroups;
    this.numberedGroup = numberedGroup;
  }

  /**
   * Applies a repetition pattern to the current pattern.
   * @param {number} [minRep] - The minimum number of repetitions.
   * @param {number} [maxRep] - The maximum number of repetitions.
   * @returns {Pattern} A new Pattern object with the repetition pattern applied.
   * @throws {STRlingError} If arguments are invalid.
   */
  call(minRep, maxRep) {
    if (minRep === undefined && maxRep === undefined) {
      return this;
    }

    if (
      (minRep !== undefined && !Number.isInteger(minRep)) ||
      (maxRep !== undefined && !Number.isInteger(maxRep))
    ) {
      const message = `
            Method: Pattern.call(minRep, maxRep)

            The minRep and maxRep arguments must be integers (0-9).
            `;
      throw new STRlingError(message);
    }

    if (
      (minRep !== undefined && minRep < 0) ||
      (maxRep !== undefined && maxRep < 0)
    ) {
      const message = `
            Method: Pattern.call(minRep, maxRep)

            The minRep and maxRep must be 0 or greater.
            `;
      throw new STRlingError(message);
    }

    if (
      this.namedGroups.length &&
      minRep !== undefined &&
      maxRep !== undefined
    ) {
      const message = `
            Method: Pattern.call(minRep, maxRep)

            Named groups cannot be repeated as they must be unique.

            Consider using an unlabeled group (merge) or a numbered group (capture).
            `;
      throw new STRlingError(message);
    }

    if (
      this.pattern.length > 1 &&
      this.pattern[this.pattern.length - 1] === "}" &&
      this.pattern[this.pattern.length - 2] !== "\\"
    ) {
      const message = `
            Method: Pattern.call(minRep, maxRep)

            Cannot re-invoke pattern to specify range that already exists.

            Examples of invalid syntax:
                simply.letter(1, 2)(3, 4) // double invoked range is invalid
                myPattern = simply.letter(1, 2) // myPattern was set range (1, 2) // valid
                myNewPattern = myPattern(3, 4) // myPattern was reinvoked (3, 4) // invalid

            Set the range on the first invocation, don't reassign it.

            Examples of valid syntax:
                You can either specify the range now:
                    myPattern = simply.letter(1, 2)

                Or you can specify the range later:
                    myPattern = simply.letter() // myPattern was never assigned a range
                    myNewPattern = myPattern(1, 2) // myPattern was invoked with (1, 2) for the first time.
            `;
      throw new STRlingError(message);
    }

    let newPattern;
    if (this.numberedGroup) {
      if (maxRep !== undefined) {
        const message = `
                Method: Pattern.call(minRep, maxRep)

                The maxRep parameter was specified when capture takes only one parameter, the exact number of copies.

                Consider using an unlabeled group (merge) for a range.
                `;
        throw new STRlingError(message);
      } else {
        newPattern = `(?:${this.pattern.repeat(minRep)})`;
      }
    } else {
      newPattern = this.pattern + repeat(minRep, maxRep);
    }

    return this.createModifiedInstance(newPattern);
  }

  /**
   * Returns the pattern object as a RegEx string.
   * @returns {string} The pattern string.
   */
  toString() {
    return this.pattern;
  }

  /**
   * Creates a modified instance of the pattern.
   * @param {string} newPattern - The new pattern string.
   * @param {Object} [kwargs] - Additional properties for the new instance.
   * @returns {Pattern} The new Pattern instance.
   */
  static createModifiedInstance(newPattern, kwargs = {}) {
    return new Pattern(newPattern, ...Object.values(kwargs));
  }
}

module.exports = {
  STRlingError,
  Pattern,
  lit,
  repeat,
};
