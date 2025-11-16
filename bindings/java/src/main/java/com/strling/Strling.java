package com.strling;

/**
 * STRling - Next-generation string pattern DSL and compiler.
 * 
 * <p>STRling is a production-grade syntax designed as a user interface for writing
 * powerful regular expressions with an object-oriented approach and instructional
 * error handling. STRling abstracts the complexities of RegEx into a clean,
 * readable, and powerful interface.</p>
 * 
 * <p>Main public entry point for the STRling library.</p>
 * 
 * @version 3.0.0-alpha
 * @author TheCyberLocal
 */
public class Strling {
    /**
     * Library version.
     */
    public static final String VERSION = "3.0.0-alpha";
    
    /**
     * Private constructor to prevent instantiation.
     * This class serves as a namespace for the STRling library.
     */
    private Strling() {
        throw new AssertionError("Strling class should not be instantiated");
    }
}
