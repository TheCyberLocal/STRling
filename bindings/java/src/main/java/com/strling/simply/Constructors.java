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
}
