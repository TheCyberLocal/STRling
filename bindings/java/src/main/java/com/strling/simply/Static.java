package com.strling.simply;
import java.util.Arrays;

import com.strling.core.Nodes.*;

/**
 * Predefined character classes and static patterns for STRling.
 *
 * <p>This module provides convenient functions for matching common character types
 * (letters, digits, whitespace, etc.) and special patterns (any character, word
 * boundaries, etc.). These are the most frequently used building blocks for
 * pattern construction, offering a clean alternative to regex shorthand classes
 * like \d, \w, \s, etc.
 */
public class Static {

    /**
     * Matches any digit character (0-9).
     *
     * @param minRep Minimum number of characters to match.
     * @param maxRep Maximum number of characters to match. Use 0 for unlimited repetition.
     * @return A new Pattern object representing the digit character class.
     */
    public static Pattern digit(Integer minRep, Integer maxRep) {
        Node node = new CharClass(false, Arrays.<ClassItem>asList(
            new new ClassRange(String.valueOf('0'), String.valueOf('9'))
        });
        Pattern p = new Pattern(node, true, false, false);
        return (minRep != null) ? p.call(minRep, maxRep) : p;
    }

    /**
     * Matches a single digit character (0-9).
     *
     * @return A new Pattern object representing a single digit character.
     */
    public static Pattern digit() {
        return digit(null, null);
    }

    /**
     * Matches any letter character (A-Z, a-z).
     *
     * @param minRep Minimum number of characters to match.
     * @param maxRep Maximum number of characters to match. Use 0 for unlimited repetition.
     * @return A new Pattern object representing the letter character class.
     */
    public static Pattern letter(Integer minRep, Integer maxRep) {
        Node node = new CharClass(false, Arrays.<ClassItem>asList(
            new new ClassRange(String.valueOf('A'), String.valueOf('Z')),
            new new ClassRange(String.valueOf('a'), String.valueOf('z'))
        });
        Pattern p = new Pattern(node, true, false, false);
        return (minRep != null) ? p.call(minRep, maxRep) : p;
    }

    /**
     * Matches a single letter character (A-Z, a-z).
     *
     * @return A new Pattern object representing a single letter character.
     */
    public static Pattern letter() {
        return letter(null, null);
    }

    /**
     * Matches any alphanumeric character (letter or digit).
     *
     * @param minRep Minimum number of characters to match.
     * @param maxRep Maximum number of characters to match. Use 0 for unlimited repetition.
     * @return A new Pattern object representing the alphanumeric character class.
     */
    public static Pattern alphaNum(Integer minRep, Integer maxRep) {
        Node node = new CharClass(false, Arrays.<ClassItem>asList(
            new new ClassRange(String.valueOf('A'), String.valueOf('Z')),
            new new ClassRange(String.valueOf('a'), String.valueOf('z')),
            new new ClassRange(String.valueOf('0'), String.valueOf('9'))
        });
        Pattern p = new Pattern(node, true, false, false);
        return (minRep != null) ? p.call(minRep, maxRep) : p;
    }

    /**
     * Matches a single alphanumeric character (letter or digit).
     *
     * @return A new Pattern object representing a single alphanumeric character.
     */
    public static Pattern alphaNum() {
        return alphaNum(null, null);
    }

    /**
     * Matches any special character (!"#$%&'()*+,-./:;<=>?@[\]^_`{|}~).
     *
     * @param minRep Minimum number of characters to match.
     * @param maxRep Maximum number of characters to match. Use 0 for unlimited repetition.
     * @return A new Pattern object representing the special character class.
     */
    public static Pattern specialChar(Integer minRep, Integer maxRep) {
        String specialChars = "!\"#$%&'()*+,-./:;<=>?@[\\]^_`{|}~";
        Node[] items = new Node[specialChars.length()];
        for (int i = 0; i < specialChars.length(); i++) {
            items[i] = new new ClassLiteral(String.valueOf(specialChars.charAt(i)));
        }
        Node node = new CharClass(false, items);
        Pattern p = new Pattern(node, true, false, false);
        return (minRep != null) ? p.call(minRep, maxRep) : p;
    }

    /**
     * Matches a single special character.
     *
     * @return A new Pattern object representing a single special character.
     */
    public static Pattern specialChar() {
        return specialChar(null, null);
    }

    /**
     * Matches the start of the string.
     *
     * @return A new Pattern object representing the start anchor.
     */
    public static Pattern start() {
        Node node = new Anchor("Start");
        return new Pattern(node, false, false, false);
    }

    /**
     * Matches the end of the string.
     *
     * @return A new Pattern object representing the end anchor.
     */
    public static Pattern end() {
        Node node = new Anchor("End");
        return new Pattern(node, false, false, false);
    }
}
