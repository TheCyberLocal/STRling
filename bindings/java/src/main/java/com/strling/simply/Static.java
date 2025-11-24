package com.strling.simply;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;

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
            new ClassEscape("d")
        ));
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
            new ClassRange(String.valueOf('A'), String.valueOf('Z')),
            new ClassRange(String.valueOf('a'), String.valueOf('z'))
        ));
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
            new ClassRange(String.valueOf('A'), String.valueOf('Z')),
            new ClassRange(String.valueOf('a'), String.valueOf('z')),
            new ClassRange(String.valueOf('0'), String.valueOf('9'))
        ));
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
        List<ClassItem> items = new ArrayList<>();
        for (int i = 0; i < specialChars.length(); i++) {
            items.add(new ClassLiteral(String.valueOf(specialChars.charAt(i))));
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

    /**
     * Matches any character that is not a letter or digit.
     *
     * @param minRep Minimum number of characters to match.
     * @param maxRep Maximum number of characters to match. Use 0 for unlimited repetition.
     * @return A new Pattern object representing the negated alphanumeric character class.
     */
    public static Pattern notAlphaNum(Integer minRep, Integer maxRep) {
        Node node = new CharClass(true, Arrays.<ClassItem>asList(
            new ClassRange(String.valueOf('A'), String.valueOf('Z')),
            new ClassRange(String.valueOf('a'), String.valueOf('z')),
            new ClassRange(String.valueOf('0'), String.valueOf('9'))
        ));
        Pattern p = new Pattern(node, true, false, false);
        return (minRep != null) ? p.call(minRep, maxRep) : p;
    }

    /**
     * Matches a single character that is not a letter or digit.
     *
     * @return A new Pattern object representing a negated alphanumeric character.
     */
    public static Pattern notAlphaNum() {
        return notAlphaNum(null, null);
    }

    /**
     * Matches any uppercase letter (A-Z).
     *
     * @param minRep Minimum number of characters to match.
     * @param maxRep Maximum number of characters to match. Use 0 for unlimited repetition.
     * @return A new Pattern object representing the uppercase letter character class.
     */
    public static Pattern upper(Integer minRep, Integer maxRep) {
        Node node = new CharClass(false, Arrays.<ClassItem>asList(
            new ClassRange(String.valueOf('A'), String.valueOf('Z'))
        ));
        Pattern p = new Pattern(node, true, false, false);
        return (minRep != null) ? p.call(minRep, maxRep) : p;
    }

    /**
     * Matches a single uppercase letter (A-Z).
     *
     * @return A new Pattern object representing an uppercase letter character.
     */
    public static Pattern upper() {
        return upper(null, null);
    }

    /**
     * Matches any character that is not an uppercase letter.
     *
     * @param minRep Minimum number of characters to match.
     * @param maxRep Maximum number of characters to match. Use 0 for unlimited repetition.
     * @return A new Pattern object representing the negated uppercase letter character class.
     */
    public static Pattern notUpper(Integer minRep, Integer maxRep) {
        Node node = new CharClass(true, Arrays.<ClassItem>asList(
            new ClassRange(String.valueOf('A'), String.valueOf('Z'))
        ));
        Pattern p = new Pattern(node, true, false, false);
        return (minRep != null) ? p.call(minRep, maxRep) : p;
    }

    /**
     * Matches a single character that is not an uppercase letter.
     *
     * @return A new Pattern object representing a negated uppercase letter character.
     */
    public static Pattern notUpper() {
        return notUpper(null, null);
    }

    /**
     * Matches any lowercase letter (a-z).
     *
     * @param minRep Minimum number of characters to match.
     * @param maxRep Maximum number of characters to match. Use 0 for unlimited repetition.
     * @return A new Pattern object representing the lowercase letter character class.
     */
    public static Pattern lower(Integer minRep, Integer maxRep) {
        Node node = new CharClass(false, Arrays.<ClassItem>asList(
            new ClassRange(String.valueOf('a'), String.valueOf('z'))
        ));
        Pattern p = new Pattern(node, true, false, false);
        return (minRep != null) ? p.call(minRep, maxRep) : p;
    }

    /**
     * Matches a single lowercase letter (a-z).
     *
     * @return A new Pattern object representing a lowercase letter character.
     */
    public static Pattern lower() {
        return lower(null, null);
    }

    /**
     * Matches any character that is not a lowercase letter.
     *
     * @param minRep Minimum number of characters to match.
     * @param maxRep Maximum number of characters to match. Use 0 for unlimited repetition.
     * @return A new Pattern object representing the negated lowercase letter character class.
     */
    public static Pattern notLower(Integer minRep, Integer maxRep) {
        Node node = new CharClass(true, Arrays.<ClassItem>asList(
            new ClassRange(String.valueOf('a'), String.valueOf('z'))
        ));
        Pattern p = new Pattern(node, true, false, false);
        return (minRep != null) ? p.call(minRep, maxRep) : p;
    }

    /**
     * Matches a single character that is not a lowercase letter.
     *
     * @return A new Pattern object representing a negated lowercase letter character.
     */
    public static Pattern notLower() {
        return notLower(null, null);
    }

    /**
     * Matches any character that is not a letter.
     *
     * @param minRep Minimum number of characters to match.
     * @param maxRep Maximum number of characters to match. Use 0 for unlimited repetition.
     * @return A new Pattern object representing the negated letter character class.
     */
    public static Pattern notLetter(Integer minRep, Integer maxRep) {
        Node node = new CharClass(true, Arrays.<ClassItem>asList(
            new ClassRange(String.valueOf('A'), String.valueOf('Z')),
            new ClassRange(String.valueOf('a'), String.valueOf('z'))
        ));
        Pattern p = new Pattern(node, true, false, false);
        return (minRep != null) ? p.call(minRep, maxRep) : p;
    }

    /**
     * Matches a single character that is not a letter.
     *
     * @return A new Pattern object representing a negated letter character.
     */
    public static Pattern notLetter() {
        return notLetter(null, null);
    }

    /**
     * Matches any character that is not a special character.
     *
     * @param minRep Minimum number of characters to match.
     * @param maxRep Maximum number of characters to match. Use 0 for unlimited repetition.
     * @return A new Pattern object representing the negated special character class.
     */
    public static Pattern notSpecialChar(Integer minRep, Integer maxRep) {
        String specialChars = "!\"#$%&'()*+,-./:;<=>?@[\\]^_`{|}~";
        List<ClassItem> items = new ArrayList<>();
        for (int i = 0; i < specialChars.length(); i++) {
            items.add(new ClassLiteral(String.valueOf(specialChars.charAt(i))));
        }
        Node node = new CharClass(true, items);
        Pattern p = new Pattern(node, true, false, false);
        return (minRep != null) ? p.call(minRep, maxRep) : p;
    }

    /**
     * Matches a single character that is not a special character.
     *
     * @return A new Pattern object representing a negated special character.
     */
    public static Pattern notSpecialChar() {
        return notSpecialChar(null, null);
    }

    /**
     * Matches any hex-digit character (A-F, a-f, 0-9).
     *
     * @param minRep Minimum number of characters to match.
     * @param maxRep Maximum number of characters to match. Use 0 for unlimited repetition.
     * @return A new Pattern object representing the hex-digit character class.
     */
    public static Pattern hexDigit(Integer minRep, Integer maxRep) {
        Node node = new CharClass(false, Arrays.<ClassItem>asList(
            new ClassRange(String.valueOf('A'), String.valueOf('F')),
            new ClassRange(String.valueOf('a'), String.valueOf('f')),
            new ClassRange(String.valueOf('0'), String.valueOf('9'))
        ));
        Pattern p = new Pattern(node, true, false, false);
        return (minRep != null) ? p.call(minRep, maxRep) : p;
    }

    /**
     * Matches a single hex-digit character (A-F, a-f, 0-9).
     *
     * @return A new Pattern object representing a hex-digit character.
     */
    public static Pattern hexDigit() {
        return hexDigit(null, null);
    }

    /**
     * Matches any character that is not a hex-digit.
     *
     * @param minRep Minimum number of characters to match.
     * @param maxRep Maximum number of characters to match. Use 0 for unlimited repetition.
     * @return A new Pattern object representing the negated hex-digit character class.
     */
    public static Pattern notHexDigit(Integer minRep, Integer maxRep) {
        Node node = new CharClass(true, Arrays.<ClassItem>asList(
            new ClassRange(String.valueOf('A'), String.valueOf('F')),
            new ClassRange(String.valueOf('a'), String.valueOf('f')),
            new ClassRange(String.valueOf('0'), String.valueOf('9'))
        ));
        Pattern p = new Pattern(node, true, false, false);
        return (minRep != null) ? p.call(minRep, maxRep) : p;
    }

    /**
     * Matches a single character that is not a hex-digit.
     *
     * @return A new Pattern object representing a negated hex-digit character.
     */
    public static Pattern notHexDigit() {
        return notHexDigit(null, null);
    }

    /**
     * Matches any character that is not a digit.
     *
     * @param minRep Minimum number of characters to match.
     * @param maxRep Maximum number of characters to match. Use 0 for unlimited repetition.
     * @return A new Pattern object representing the negated digit character class.
     */
    public static Pattern notDigit(Integer minRep, Integer maxRep) {
        Node node = new CharClass(false, Arrays.<ClassItem>asList(
            new ClassEscape("D")
        ));
        Pattern p = new Pattern(node, true, false, false);
        return (minRep != null) ? p.call(minRep, maxRep) : p;
    }

    /**
     * Matches a single character that is not a digit.
     *
     * @return A new Pattern object representing a negated digit character.
     */
    public static Pattern notDigit() {
        return notDigit(null, null);
    }

    /**
     * Matches any whitespace character.
     *
     * @param minRep Minimum number of characters to match.
     * @param maxRep Maximum number of characters to match. Use 0 for unlimited repetition.
     * @return A new Pattern object representing the whitespace character class.
     */
    public static Pattern whitespace(Integer minRep, Integer maxRep) {
        Node node = new CharClass(false, Arrays.<ClassItem>asList(
            new ClassEscape("s")
        ));
        Pattern p = new Pattern(node, true, false, false);
        return (minRep != null) ? p.call(minRep, maxRep) : p;
    }

    /**
     * Matches a single whitespace character.
     *
     * @return A new Pattern object representing a whitespace character.
     */
    public static Pattern whitespace() {
        return whitespace(null, null);
    }

    /**
     * Matches any character that is not a whitespace character.
     *
     * @param minRep Minimum number of characters to match.
     * @param maxRep Maximum number of characters to match. Use 0 for unlimited repetition.
     * @return A new Pattern object representing the negated whitespace character class.
     */
    public static Pattern notWhitespace(Integer minRep, Integer maxRep) {
        Node node = new CharClass(true, Arrays.<ClassItem>asList(
            new ClassEscape("s")
        ));
        Pattern p = new Pattern(node, true, false, false);
        return (minRep != null) ? p.call(minRep, maxRep) : p;
    }

    /**
     * Matches a single character that is not a whitespace character.
     *
     * @return A new Pattern object representing a negated whitespace character.
     */
    public static Pattern notWhitespace() {
        return notWhitespace(null, null);
    }

    /**
     * Matches a newline character.
     *
     * @param minRep Minimum number of characters to match.
     * @param maxRep Maximum number of characters to match. Use 0 for unlimited repetition.
     * @return A new Pattern object representing the newline character class.
     */
    public static Pattern newline(Integer minRep, Integer maxRep) {
        Node node = new CharClass(false, Arrays.<ClassItem>asList(
            new ClassEscape("n")
        ));
        Pattern p = new Pattern(node, true, false, false);
        return (minRep != null) ? p.call(minRep, maxRep) : p;
    }

    /**
     * Matches a single newline character.
     *
     * @return A new Pattern object representing a newline character.
     */
    public static Pattern newline() {
        return newline(null, null);
    }

    /**
     * Matches any character that is not a newline.
     *
     * @param minRep Minimum number of characters to match.
     * @param maxRep Maximum number of characters to match. Use 0 for unlimited repetition.
     * @return A new Pattern object representing the negated newline character class.
     */
    public static Pattern notNewline(Integer minRep, Integer maxRep) {
        Node node = new CharClass(true, Arrays.<ClassItem>asList(
            new ClassEscape("n")
        ));
        Pattern p = new Pattern(node, true, false, false);
        return (minRep != null) ? p.call(minRep, maxRep) : p;
    }

    /**
     * Matches a single character that is not a newline.
     *
     * @return A new Pattern object representing a negated newline character.
     */
    public static Pattern notNewline() {
        return notNewline(null, null);
    }

    /**
     * Matches a tab character.
     *
     * @param minRep Minimum number of characters to match.
     * @param maxRep Maximum number of characters to match. Use 0 for unlimited repetition.
     * @return A new Pattern object representing the tab character class.
     */
    public static Pattern tab(Integer minRep, Integer maxRep) {
        Node node = new CharClass(false, Arrays.<ClassItem>asList(
            new ClassEscape("t")
        ));
        Pattern p = new Pattern(node, true, false, false);
        return (minRep != null) ? p.call(minRep, maxRep) : p;
    }

    /**
     * Matches a single tab character.
     *
     * @return A new Pattern object representing a tab character.
     */
    public static Pattern tab() {
        return tab(null, null);
    }

    /**
     * Matches a carriage return character.
     *
     * @param minRep Minimum number of characters to match.
     * @param maxRep Maximum number of characters to match. Use 0 for unlimited repetition.
     * @return A new Pattern object representing the carriage return character class.
     */
    public static Pattern carriage(Integer minRep, Integer maxRep) {
        Node node = new CharClass(false, Arrays.<ClassItem>asList(
            new ClassEscape("r")
        ));
        Pattern p = new Pattern(node, true, false, false);
        return (minRep != null) ? p.call(minRep, maxRep) : p;
    }

    /**
     * Matches a single carriage return character.
     *
     * @return A new Pattern object representing a carriage return character.
     */
    public static Pattern carriage() {
        return carriage(null, null);
    }

    /**
     * Matches a word boundary.
     *
     * @param minRep Minimum number of characters to match.
     * @param maxRep Maximum number of characters to match. Use 0 for unlimited repetition.
     * @return A new Pattern object representing the word boundary.
     */
    public static Pattern bound(Integer minRep, Integer maxRep) {
        Node node = new CharClass(false, Arrays.<ClassItem>asList(
            new ClassEscape("b")
        ));
        Pattern p = new Pattern(node, true, false, false);
        return (minRep != null) ? p.call(minRep, maxRep) : p;
    }

    /**
     * Matches a single word boundary.
     *
     * @return A new Pattern object representing a word boundary.
     */
    public static Pattern bound() {
        return bound(null, null);
    }

    /**
     * Matches any character that is not a word boundary.
     *
     * @param minRep Minimum number of characters to match.
     * @param maxRep Maximum number of characters to match. Use 0 for unlimited repetition.
     * @return A new Pattern object representing the negated word boundary.
     */
    public static Pattern notBound(Integer minRep, Integer maxRep) {
        Node node = new Anchor("NotWordBoundary");
        Pattern p = new Pattern(node, false, false, false);
        return (minRep != null) ? p.call(minRep, maxRep) : p;
    }

    /**
     * Matches any position that is not a word boundary.
     *
     * @return A new Pattern object representing a negated word boundary.
     */
    public static Pattern notBound() {
        return notBound(null, null);
    }
}
