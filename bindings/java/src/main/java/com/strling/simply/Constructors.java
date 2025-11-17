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
}
