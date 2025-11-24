package com.strling.simply;

import com.strling.core.Nodes;
import java.util.ArrayList;
import java.util.List;

/**
 * Core Pattern class and error types for STRling.
 *
 * <p>This module defines the fundamental Pattern class that represents all STRling
 * patterns, along with the STRlingError exception class. The Pattern class provides
 * chainable methods for applying quantifiers, repetitions, and other modifiers to
 * patterns. It serves as the foundation for all pattern construction in the Simply API,
 * wrapping internal AST nodes and providing a user-friendly interface for pattern
 * manipulation and compilation.</p>
 */
public class Pattern {
    // Global Simply instance for compilation
    private static final Simply s = new Simply();

    // Package-private to allow access from other Simply classes
    final Nodes.Node node;
    private final boolean customSet;
    private final boolean negated;
    private final boolean composite;
    private final List<String> namedGroups;
    private final boolean numberedGroup;

    /**
     * Creates a new Pattern with default attributes.
     *
     * @param node The AST node representing this pattern
     */
    public Pattern(Nodes.Node node) {
        this(node, false, false, false, new ArrayList<>(), false);
    }

    /**
     * Creates a new Pattern with custom set attributes.
     *
     * @param node The AST node representing this pattern
     * @param customSet Indicates if the pattern is a custom character set
     * @param negated Indicates if the pattern is a negated custom character set
     * @param composite Indicates if the pattern is a composite pattern
     */
    public Pattern(Nodes.Node node, boolean customSet, boolean negated, boolean composite) {
        this(node, customSet, negated, composite, new ArrayList<>(), false);
    }

    /**
     * Creates a new Pattern with all attributes.
     *
     * @param node The AST node representing this pattern
     * @param customSet Indicates if the pattern is a custom character set
     * @param negated Indicates if the pattern is a negated custom character set
     * @param composite Indicates if the pattern is a composite pattern
     * @param namedGroups List of named groups within the pattern
     * @param numberedGroup Indicates if the pattern is a numbered group
     */
    public Pattern(Nodes.Node node, boolean customSet, boolean negated, boolean composite,
                   List<String> namedGroups, boolean numberedGroup) {
        this.node = node;
        this.customSet = customSet;
        this.negated = negated;
        this.composite = composite;
        this.namedGroups = new ArrayList<>(namedGroups);
        this.numberedGroup = numberedGroup;
    }

    /**
     * Get the AST node for this pattern.
     *
     * @return The AST node.
     */
    public Nodes.Node getNode() {
        return node;
    }

    /**
     * Check if this is a custom character set.
     *
     * @return true if custom set.
     */
    public boolean isCustomSet() {
        return customSet;
    }

    /**
     * Check if this is a negated pattern.
     *
     * @return true if negated.
     */
    public boolean isNegated() {
        return negated;
    }

    /**
     * Check if this is a composite pattern.
     *
     * @return true if composite.
     */
    public boolean isComposite() {
        return composite;
    }

    /**
     * Get the list of named groups.
     *
     * @return List of named group names.
     */
    public List<String> getNamedGroups() {
        return new ArrayList<>(namedGroups);
    }

    /**
     * Check if this is a numbered group.
     *
     * @return true if numbered group.
     */
    public boolean isNumberedGroup() {
        return numberedGroup;
    }

    /**
     * Applies a repetition pattern to the current pattern.
     *
     * <p>Parameters: (minRep/exactRep, maxRep)
     * <ul>
     *   <li>minRep (optional): Specifies the minimum number of characters to match.
     *   <li>maxRep (optional): Specifies the maximum number of characters to match,
     *       0 means unlimited, null means match exact count of minRep.
     * </ul>
     *
     * @param minRep Minimum repetitions (or exact count if maxRep is null).
     * @param maxRep Maximum repetitions (0 for unlimited, null for exact match).
     * @return A new Pattern object with the repetition pattern applied.
     */
    public Pattern call(Integer minRep, Integer maxRep) {
        // Prevent errors if invoked with no range
        if (minRep == null && maxRep == null) {
            return this;
        }

        // If minRep or maxRep are specified out of valid range
        if (minRep != null && minRep < 0 || maxRep != null && maxRep < 0) {
            String message = "Method: Pattern.call(minRep, maxRep)\n\n" +
                    "The `minRep` and `maxRep` must be 0 or greater.";
            throw new STRlingError(message);
        }

        // Named group is unique and not repeatable
        if (!this.namedGroups.isEmpty() && minRep != null && maxRep != null) {
            String message = "Method: Pattern.call(minRep, maxRep)\n\n" +
                    "Named groups cannot be repeated as they must be unique.\n\n" +
                    "Consider using an unlabeled group (merge) or a numbered group (capture).";
            throw new STRlingError(message);
        }

        // A group already assigned a specified range cannot be reassigned
        if (this.node instanceof Nodes.Quant) {
            String message = "Method: Pattern.call(minRep, maxRep)\n\n" +
                    "Cannot re-invoke pattern to specify range that already exists.\n\n" +
                    "Examples of invalid syntax:\n" +
                    "    simply.letter(1, 2).call(3, 4) // double invoked range is invalid\n" +
                    "    myPattern = simply.letter(1, 2) // myPattern was set range (1, 2) // valid\n" +
                    "    myNewPattern = myPattern.call(3, 4) // myPattern was reinvoked (3, 4) // invalid\n\n" +
                    "Set the range on the first invocation, don't reassign it.\n\n" +
                    "Examples of valid syntax:\n" +
                    "    You can either specify the range now:\n" +
                    "        myPattern = simply.letter(1, 2)\n\n" +
                    "    Or you can specify the range later:\n" +
                    "        myPattern = simply.letter() // myPattern was never assigned a range\n" +
                    "        myNewPattern = myPattern.call(1, 2) // myPattern was invoked with (1, 2) for the first time.";
            throw new STRlingError(message);
        }

        // Validate range
        if (minRep != null && maxRep != null && maxRep != 0 && minRep > maxRep) {
            String message = "Method: Pattern.call(minRep, maxRep)\n\n" +
                    "The `minRep` must not be greater than the `maxRep`.\n\n" +
                    "Ensure the lesser number is on the left and the greater number is on the right.";
            throw new STRlingError(message);
        }

        // Create Quant node instead of appending a string
        if (this.numberedGroup) {
            if (maxRep != null) {
                String message = "Method: Pattern.call(minRep, maxRep)\n\n" +
                        "The `maxRep` parameter was specified when capture takes only one parameter, the exact number of copies.\n\n" +
                        "Consider using an unlabeled group (merge) for a range.";
                throw new STRlingError(message);
            } else {
                // Handle numbered groups differently by duplicating the node
                List<Nodes.Node> children = new ArrayList<>();
                for (int i = 0; i < minRep; i++) {
                    children.add(this.node);
                }
                Nodes.Seq newNode = new Nodes.Seq(children);
                return createModifiedInstance(newNode);
            }
        } else {
            // Regular case: create a quantifier node
            Object qMax = maxRep == null ? minRep : (maxRep == 0 ? "Inf" : maxRep);
            Nodes.Quant newNode = new Nodes.Quant(this.node, minRep, qMax, "Greedy");
            return createModifiedInstance(newNode);
        }
    }

    /**
     * Applies an exact repetition count to the current pattern.
     *
     * @param exactRep Exact number of repetitions.
     * @return A new Pattern object with the repetition applied.
     */
    public Pattern call(int exactRep) {
        return call(exactRep, null);
    }

    /**
     * Returns the compiled regex string.
     *
     * @return The compiled PCRE2 regex string.
     */
    @Override
    public String toString() {
        return s.build(this);
    }

    /**
     * Returns a copy of the pattern instance with a new node.
     *
     * @param newNode The new AST node.
     * @return A new Pattern instance with the modified node.
     */
    protected Pattern createModifiedInstance(Nodes.Node newNode) {
        return new Pattern(newNode, this.customSet, this.negated, this.composite,
                this.namedGroups, this.numberedGroup);
    }

    /**
     * Create a literal pattern from a string.
     *
     * <p>This function wraps a plain string in a Pattern object, treating all characters
     * as literals (no special regex meaning). It's the foundation for mixing literal
     * text with pattern-based matching.
     *
     * @param text The text to use as a literal.
     * @return A Pattern object representing the literal text.
     */
    public static Pattern lit(String text) {
        return new Pattern(new Nodes.Lit(text));
    }
}
