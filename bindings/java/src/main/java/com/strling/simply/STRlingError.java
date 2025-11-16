package com.strling.simply;

/**
 * Custom error class for STRling pattern errors.
 *
 * This error class provides formatted, user-friendly error messages when invalid
 * patterns are constructed or invalid arguments are provided to pattern functions.
 * Error messages are automatically formatted with consistent indentation for
 * better readability in console output.
 */
public class STRlingError extends RuntimeException {
    private final String message;

    /**
     * Create a new STRlingError with formatted message.
     *
     * @param message The error message (can be multiline and will be reformatted).
     */
    public STRlingError(String message) {
        // Dedent and format the message
        this.message = dedent(message).trim().replace("\n", "\n\t");
    }

    /**
     * Return the formatted error message with header and indentation.
     *
     * @return Formatted error message string.
     */
    @Override
    public String getMessage() {
        return "\n\nSTRlingError: Invalid Pattern Attempted.\n\n\t" + this.message;
    }

    /**
     * Return the formatted error message.
     *
     * @return Formatted error message string.
     */
    @Override
    public String toString() {
        return getMessage();
    }

    /**
     * Dedent a multi-line string by removing common leading whitespace.
     *
     * @param text The text to dedent.
     * @return Dedented text.
     */
    private static String dedent(String text) {
        if (text == null || text.isEmpty()) {
            return text;
        }

        String[] lines = text.split("\n");
        int minIndent = Integer.MAX_VALUE;

        // Find minimum indentation (excluding empty lines)
        for (String line : lines) {
            if (line.trim().isEmpty()) {
                continue;
            }
            int indent = 0;
            while (indent < line.length() && Character.isWhitespace(line.charAt(indent))) {
                indent++;
            }
            minIndent = Math.min(minIndent, indent);
        }

        // Remove the common indentation
        if (minIndent == Integer.MAX_VALUE) {
            return text;
        }

        StringBuilder result = new StringBuilder();
        for (String line : lines) {
            if (line.trim().isEmpty()) {
                result.append("\n");
            } else {
                result.append(line.substring(Math.min(minIndent, line.length()))).append("\n");
            }
        }

        return result.toString();
    }
}
