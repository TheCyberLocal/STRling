package com.strling.simply;
import java.util.Arrays;

import com.strling.core.Nodes.*;
import java.util.ArrayList;
import java.util.List;

/**
 * Pattern constructors for building composite patterns in STRling.
 *
 * <p>This module provides high-level functions for creating complex pattern structures
 * through composition. Functions here handle alternation (anyOf), optionality (may),
 * concatenation (merge), and grouping operations (capture, group). These are the
 * primary building blocks for constructing sophisticated regex patterns in a
 * readable and maintainable way.</p>
 */
public class Constructors {

    /**
     * Merges multiple patterns into a sequence.
     *
     * <p>Creates a single pattern that matches all the provided patterns in order.
     * This is the fundamental operation for building complex patterns from simpler
     * components.</p>
     *
     * @param patterns Variable number of Pattern objects or strings to merge.
     *                Strings are automatically converted to literal patterns
     * @return A new Pattern object representing the merged sequence
     * @throws STRlingError If any parameter is not a Pattern or string
     *
     * <p><b>Examples:</b></p>
     * <pre>
     * // Match digit followed by letter
     * Pattern pattern = merge(digit(), letter());
     *
     * // Match "hello" followed by space followed by "world"
     * Pattern pattern = merge("hello", " ", "world");
     * </pre>
     *
     * <p><b>Notes:</b> Empty input results in an empty pattern. Single input returns
     * that pattern unchanged. Multiple patterns are combined into a Seq node.</p>
     */
    public static Pattern merge(Object... patterns) {
        if (patterns == null || patterns.length == 0) {
            // Return empty pattern
            Node node = new Seq(new ArrayList<>());
            return new Pattern(node, false, false, false);
        }

        // Convert all to patterns
        List<Node> nodes = new ArrayList<>();
        for (Object obj : patterns) {
            if (obj instanceof String) {
                obj = Pattern.lit((String) obj);
            }

            if (!(obj instanceof Pattern)) {
                String message = "\n" +
                    "Method: simply.merge(*patterns)\n\n" +
                    "All parameters must be instances of `Pattern` or `str`.\n\n" +
                    "Use a string such as \"123abc$\" to match literal characters, or use a predefined set like `simply.letter()`.";
                throw new STRlingError(message);
            }

            nodes.add(((Pattern) obj).node);
        }

        // If single pattern, return it directly
        if (nodes.size() == 1) {
            return new Pattern(nodes.get(0), false, false, false);
        }

        // Create sequence
        Node seqNode = new Seq(nodes);
        return new Pattern(seqNode, false, false, true);
    }

    /**
     * Matches any one of the provided patterns (alternation/OR operation).
     *
     * <p>This function creates a pattern that succeeds if any of the provided patterns
     * match at the current position. It's equivalent to the | operator in regular
     * expressions.</p>
     *
     * @param patterns One or more patterns to be matched.
     *                Strings are automatically converted to literal patterns.
     * @return A new Pattern object representing the alternation of all provided patterns.
     * @throws STRlingError If any parameter is not a Pattern or string, or if duplicate named groups
     *                      are found across the patterns.
     *
     * <p><b>Examples:</b></p>
     * <pre>
     * // Match either 'cat' or 'dog'
     * Pattern pattern = anyOf("cat", "dog");
     *
     * // Match different number formats
     * Pattern pattern1 = merge(digit(3), letter(3));
     * Pattern pattern2 = merge(letter(3), digit(3));
     * Pattern eitherPattern = anyOf(pattern1, pattern2);
     * </pre>
     */
    public static Pattern anyOf(Object... patterns) {
        List<Pattern> cleanPatterns = new ArrayList<>();
        for (Object obj : patterns) {
            if (obj instanceof String) {
                obj = Pattern.lit((String) obj);
            }

            if (!(obj instanceof Pattern)) {
                String message = "\n" +
                    "Method: simply.anyOf(...patterns)\n\n" +
                    "The parameters must be instances of Pattern or string.\n\n" +
                    "Use a string such as \"123abc$\" to match literal characters, or use a predefined set like simply.letter().";
                throw new STRlingError(message);
            }

            cleanPatterns.add((Pattern) obj);
        }

        // Check for duplicate named groups
        java.util.Map<String, Integer> namedGroupCounts = new java.util.HashMap<>();
        for (Pattern pattern : cleanPatterns) {
            for (String groupName : pattern.getNamedGroups()) {
                namedGroupCounts.put(groupName, namedGroupCounts.getOrDefault(groupName, 0) + 1);
            }
        }

        // Find duplicates
        List<String> duplicates = new ArrayList<>();
        for (java.util.Map.Entry<String, Integer> entry : namedGroupCounts.entrySet()) {
            if (entry.getValue() > 1) {
                duplicates.add(entry.getKey() + ": " + entry.getValue());
            }
        }

        if (!duplicates.isEmpty()) {
            String duplicateInfo = String.join(", ", duplicates);
            String message = "\n" +
                "Method: simply.anyOf(...patterns)\n\n" +
                "Named groups must be unique.\n" +
                "Duplicate named groups found: " + duplicateInfo + ".\n\n" +
                "If you need later reference change the named group argument to simply.capture().\n" +
                "If you don't need later reference change the named group argument to simply.merge().";
            throw new STRlingError(message);
        }

        // Build alternation
        List<Node> childNodes = new ArrayList<>();
        for (Pattern pattern : cleanPatterns) {
            childNodes.add(pattern.node);
        }
        Node node = new Alt(childNodes);

        // Collect all named groups
        List<String> allNamedGroups = new ArrayList<>();
        for (Pattern pattern : cleanPatterns) {
            allNamedGroups.addAll(pattern.getNamedGroups());
        }

        return new Pattern(node, false, false, true, allNamedGroups, false);
    }

    /**
     * Makes the provided patterns optional (matches 0 or 1 times).
     *
     * <p>This function creates a pattern that may or may not be present. If the pattern
     * is absent, the overall match can still succeed. This is equivalent to the ?
     * quantifier in regular expressions.
     *
     * @param patterns One or more patterns to be optionally matched.
     *                Strings are automatically converted to literal patterns.
     *                Multiple patterns are concatenated together.
     * @return A new Pattern object representing the optional pattern(s).
     * @throws STRlingError If any parameter is not a Pattern or string, or if duplicate named groups
     *                      are found.
     *
     * <p><b>Examples:</b></p>
     * <pre>
     * // Match a letter with optional trailing digit
     * Pattern pattern = merge(letter(), may(digit()));
     *
     * // Optional protocol in URL pattern
     * Pattern protocol = may(merge(anyOf("http", "https"), "://"));
     * Pattern domain = merge(letter(1, 0), ".", letter(2, 3));
     * Pattern urlPattern = merge(protocol, domain);
     * </pre>
     */
    public static Pattern may(Object... patterns) {
        List<Pattern> cleanPatterns = new ArrayList<>();
        for (Object obj : patterns) {
            if (obj instanceof String) {
                obj = Pattern.lit((String) obj);
            }

            if (!(obj instanceof Pattern)) {
                String message = "\n" +
                    "Method: simply.may(...patterns)\n\n" +
                    "The parameters must be instances of Pattern or string.\n\n" +
                    "Use a string such as \"123abc$\" to match literal characters, or use a predefined set like simply.letter().";
                throw new STRlingError(message);
            }

            cleanPatterns.add((Pattern) obj);
        }

        // Check for duplicate named groups
        java.util.Map<String, Integer> namedGroupCounts = new java.util.HashMap<>();
        for (Pattern pattern : cleanPatterns) {
            for (String groupName : pattern.getNamedGroups()) {
                namedGroupCounts.put(groupName, namedGroupCounts.getOrDefault(groupName, 0) + 1);
            }
        }

        // Find duplicates
        List<String> duplicates = new ArrayList<>();
        for (java.util.Map.Entry<String, Integer> entry : namedGroupCounts.entrySet()) {
            if (entry.getValue() > 1) {
                duplicates.add(entry.getKey() + ": " + entry.getValue());
            }
        }

        if (!duplicates.isEmpty()) {
            String duplicateInfo = String.join(", ", duplicates);
            String message = "\n" +
                "Method: simply.may(...patterns)\n\n" +
                "Named groups must be unique.\n" +
                "Duplicate named groups found: " + duplicateInfo + ".\n\n" +
                "If you need later reference change the named group argument to simply.capture().\n" +
                "If you don't need later reference change the named group argument to simply.merge().";
            throw new STRlingError(message);
        }

        // Build body node
        Node bodyNode;
        if (cleanPatterns.size() == 1) {
            bodyNode = cleanPatterns.get(0).node;
        } else {
            List<Node> childNodes = new ArrayList<>();
            for (Pattern pattern : cleanPatterns) {
                childNodes.add(pattern.node);
            }
            bodyNode = new Seq(childNodes);
        }

        // Create quantifier node for optional (0, 1)
        Node node = new Quant(bodyNode, 0, 1, "Greedy");

        // Collect all named groups
        List<String> allNamedGroups = new ArrayList<>();
        for (Pattern pattern : cleanPatterns) {
            allNamedGroups.addAll(pattern.getNamedGroups());
        }

        return new Pattern(node, false, false, true, allNamedGroups, false);
    }

    /**
     * Creates a numbered capture group for extracting matched content by index.
     *
     * <p>Capture groups allow you to extract specific portions of a matched pattern
     * using numeric indices. Unlike named groups, capture groups can be repeated
     * with quantifiers, and each repetition creates a new numbered group.
     *
     * @param patterns One or more patterns to be captured.
     *                Strings are automatically converted to literal patterns.
     *                Multiple patterns are concatenated.
     * @return A new Pattern object representing the numbered capture group.
     * @throws STRlingError If any parameter is not a Pattern or string, or if duplicate named groups
     *                      are found within the captured patterns.
     *
     * <p><b>Examples:</b></p>
     * <pre>
     * // Capture a digit-comma-period sequence
     * Pattern pattern = capture(digit(), ",.");
     *
     * // Multiple captures with repetition
     * Pattern threeDigitGroup = capture(digit(3));
     * Pattern fourGroups = threeDigitGroup.call(4);
     * </pre>
     */
    public static Pattern capture(Object... patterns) {
        List<Pattern> cleanPatterns = new ArrayList<>();
        for (Object obj : patterns) {
            if (obj instanceof String) {
                obj = Pattern.lit((String) obj);
            }

            if (!(obj instanceof Pattern)) {
                String message = "\n" +
                    "Method: simply.capture(...patterns)\n\n" +
                    "The parameters must be instances of Pattern or string.\n\n" +
                    "Use a string such as \"123abc$\" to match literal characters, or use a predefined set like simply.letter().";
                throw new STRlingError(message);
            }

            cleanPatterns.add((Pattern) obj);
        }

        // Check for duplicate named groups
        java.util.Map<String, Integer> namedGroupCounts = new java.util.HashMap<>();
        for (Pattern pattern : cleanPatterns) {
            for (String groupName : pattern.getNamedGroups()) {
                namedGroupCounts.put(groupName, namedGroupCounts.getOrDefault(groupName, 0) + 1);
            }
        }

        // Find duplicates
        List<String> duplicates = new ArrayList<>();
        for (java.util.Map.Entry<String, Integer> entry : namedGroupCounts.entrySet()) {
            if (entry.getValue() > 1) {
                duplicates.add(entry.getKey() + ": " + entry.getValue());
            }
        }

        if (!duplicates.isEmpty()) {
            String duplicateInfo = String.join(", ", duplicates);
            String message = "\n" +
                "Method: simply.capture(...patterns)\n\n" +
                "Named groups must be unique.\n" +
                "Duplicate named groups found: " + duplicateInfo + ".\n\n" +
                "If you need later reference change the named group argument to simply.capture().\n" +
                "If you don't need later reference change the named group argument to simply.merge().";
            throw new STRlingError(message);
        }

        // Build body node
        Node bodyNode;
        if (cleanPatterns.size() == 1) {
            bodyNode = cleanPatterns.get(0).node;
        } else {
            List<Node> childNodes = new ArrayList<>();
            for (Pattern pattern : cleanPatterns) {
                childNodes.add(pattern.node);
            }
            bodyNode = new Seq(childNodes);
        }

        // Create numbered group
        Node node = new Group(true, bodyNode, null);

        // Collect all named groups
        List<String> allNamedGroups = new ArrayList<>();
        for (Pattern pattern : cleanPatterns) {
            allNamedGroups.addAll(pattern.getNamedGroups());
        }

        return new Pattern(node, false, false, true, allNamedGroups, true);
    }

    /**
     * Creates a named capture group that can be referenced by name for extracting matched content.
     *
     * <p>Named groups allow you to extract specific portions of a matched pattern using
     * descriptive names rather than numeric indices, making your code more readable
     * and maintainable.
     *
     * @param name The unique name for the group (e.g., 'area_code'). Must be a valid
     *            identifier and must be unique within the entire pattern.
     * @param patterns One or more patterns to be captured.
     *                Strings are automatically converted to literal patterns.
     *                Multiple patterns are concatenated.
     * @return A new Pattern object representing the named capture group.
     * @throws STRlingError If name is not a string, if any pattern parameter is not a Pattern or
     *                      string, or if duplicate named groups are found.
     *
     * <p><b>Examples:</b></p>
     * <pre>
     * // Capture a digit-comma-period sequence with a name
     * Pattern pattern = group("my_group", digit(), ",.");
     *
     * // Build a phone number pattern with named groups
     * Pattern first = group("first", digit(3));
     * Pattern second = group("second", digit(3));
     * Pattern third = group("third", digit(4));
     * Pattern phonePattern = merge(first, "-", second, "-", third);
     * </pre>
     *
     * <p><b>Note:</b> Named groups CANNOT be repeated with quantifiers like .call(1, 3) because
     * each repetition would create multiple groups with the same name, which is not
     * allowed. For repeatable patterns, use capture() for numbered groups or
     * merge() for non-capturing concatenation.</p>
     */
    public static Pattern group(String name, Object... patterns) {
        if (name == null) {
            String message = "\n" +
                "Method: simply.group(name, ...patterns)\n\n" +
                "The group is missing a specified name.\n" +
                "The name parameter must be a string like 'groupName'.";
            throw new STRlingError(message);
        }

        List<Pattern> cleanPatterns = new ArrayList<>();
        for (Object obj : patterns) {
            if (obj instanceof String) {
                obj = Pattern.lit((String) obj);
            }

            if (!(obj instanceof Pattern)) {
                String message = "\n" +
                    "Method: simply.group(name, ...patterns)\n\n" +
                    "The parameters must be instances of Pattern or string.\n\n" +
                    "Use a string such as \"123abc$\" to match literal characters, or use a predefined set like simply.letter().";
                throw new STRlingError(message);
            }

            cleanPatterns.add((Pattern) obj);
        }

        // Check for duplicate named groups
        java.util.Map<String, Integer> namedGroupCounts = new java.util.HashMap<>();
        for (Pattern pattern : cleanPatterns) {
            for (String groupName : pattern.getNamedGroups()) {
                namedGroupCounts.put(groupName, namedGroupCounts.getOrDefault(groupName, 0) + 1);
            }
        }

        // Find duplicates
        List<String> duplicates = new ArrayList<>();
        for (java.util.Map.Entry<String, Integer> entry : namedGroupCounts.entrySet()) {
            if (entry.getValue() > 1) {
                duplicates.add(entry.getKey() + ": " + entry.getValue());
            }
        }

        if (!duplicates.isEmpty()) {
            String duplicateInfo = String.join(", ", duplicates);
            String message = "\n" +
                "Method: simply.group(name, ...patterns)\n\n" +
                "Named groups must be unique.\n" +
                "Duplicate named groups found: " + duplicateInfo + ".\n\n" +
                "If you need later reference change the named group argument to simply.capture().\n" +
                "If you don't need later reference change the named group argument to simply.merge().";
            throw new STRlingError(message);
        }

        // Build body node
        Node bodyNode;
        if (cleanPatterns.size() == 1) {
            bodyNode = cleanPatterns.get(0).node;
        } else {
            List<Node> childNodes = new ArrayList<>();
            for (Pattern pattern : cleanPatterns) {
                childNodes.add(pattern.node);
            }
            bodyNode = new Seq(childNodes);
        }

        // Create named group
        Node node = new Group(true, bodyNode, name);

        // Collect all named groups and add this group's name
        List<String> allNamedGroups = new ArrayList<>();
        for (Pattern pattern : cleanPatterns) {
            allNamedGroups.addAll(pattern.getNamedGroups());
        }
        allNamedGroups.add(name);

        return new Pattern(node, false, false, true, allNamedGroups, false);
    }
}
