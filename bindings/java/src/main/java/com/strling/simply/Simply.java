package com.strling.simply;

import com.strling.core.Compiler;
import com.strling.core.Nodes;
import com.strling.core.IR;
import com.strling.emitters.Pcre2Emitter;

/**
 * Central manager for pattern compilation and emission.
 *
 * <p>This internal class handles the compilation pipeline, transforming Pattern
 * objects through the AST -> IR -> emitted regex string stages.</p>
 */
public class Simply {
    private final Compiler compiler;

    /**
     * Creates a new Simply compiler instance.
     */
    public Simply() {
        this.compiler = new Compiler();
    }

    /**
     * Compiles a Pattern object's node to a regex string.
     *
     * @param patternObj The Pattern object to compile
     * @return The compiled regex string in PCRE2 format
     */
    public String build(Pattern patternObj) {
        return build(patternObj, null);
    }

    /**
     * Compiles a Pattern object's node to a regex string.
     *
     * @param patternObj The Pattern object to compile
     * @param flags Optional regex flags to apply
     * @return The compiled regex string in PCRE2 format
     */
    public String build(Pattern patternObj, Nodes.Flags flags) {
        IR.IROp irRoot = compiler.compile(patternObj.getNode());
        return Pcre2Emitter.emit(irRoot, flags);
    }

    // --- Static API ---

    /**
     * Merges multiple patterns into a sequence.
     * @see Constructors#merge(Object...)
     */
    public static Pattern merge(Object... patterns) {
        return Constructors.merge(patterns);
    }

    /**
     * Creates a numbered capture group.
     * @see Constructors#capture(Object...)
     */
    public static Pattern capture(Object... patterns) {
        return Constructors.capture(patterns);
    }

    /**
     * Creates a named capture group.
     * @see Constructors#group(String, Object...)
     */
    public static Pattern group(String name, Object... patterns) {
        return Constructors.group(name, patterns);
    }

    /**
     * Makes the provided patterns optional.
     * @see Constructors#may(Object...)
     */
    public static Pattern may(Object... patterns) {
        return Constructors.may(patterns);
    }

    /**
     * Matches any of the characters in the string (Character Class).
     * <p>Example: <code>anyOf("-. ")</code> matches '-', '.', or ' '.</p>
     * @see Sets#inChars(Object...)
     */
    public static Pattern anyOf(String chars) {
        return Sets.inChars(chars);
    }

    /**
     * Matches any of the provided patterns (Alternation).
     * <p>Example: <code>anyOf("cat", "dog")</code> matches "cat" or "dog".</p>
     * @see Constructors#anyOf(Object...)
     */
    public static Pattern anyOf(Object... patterns) {
        return Constructors.anyOf(patterns);
    }

    /**
     * Matches a single digit (0-9).
     */
    public static Pattern digit() {
        return Static.digit();
    }

    /**
     * Matches an exact number of digits.
     */
    public static Pattern digit(int count) {
        return Static.digit(count);
    }

    /**
     * Matches a number of digits between min and max.
     */
    public static Pattern digit(int min, int max) {
        return Static.digit(min, max);
    }

    /**
     * Matches the start of the string.
     */
    public static Pattern start() {
        return Static.start();
    }

    /**
     * Matches the end of the string.
     */
    public static Pattern end() {
        return Static.end();
    }
}
