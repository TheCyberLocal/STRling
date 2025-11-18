package com.strling.simply;

/**
 * Custom error class for STRling pattern errors.
 *
 * <p>This error class provides formatted, user-friendly error messages when invalid
 * patterns are constructed or invalid arguments are provided to pattern functions.
 * Error messages are automatically formatted with consistent indentation for
 * better readability in console output.</p>
 */
public class STRlingError extends RuntimeException {
    private final String message;

    /**
     * Creates an instance of STRlingError.
     *
     * <p>The error message is automatically formatted with consistent indentation
     * for improved readability when displayed in terminals or logs.</p>
     *
     * @param message The error message. Can be multiline and will be reformatted
     */
    public STRlingError(String message) {
        // Dedent and format the message
        this.message = dedent(message).trim().replace("\n", "\n\t");
    }

    /**
     * Returns the error message as a formatted string.
     *
     * <p>Formats the error message with a clear header and indented content
     * for improved visibility in console output.</p>
     *
     * @return The formatted error message with header and indentation
     */
    @Override
    public String getMessage() {
        return "\n\nSTRlingError: Invalid Pattern Attempted.\n\n\t" + this.message;
    }

    /**
     * Returns the formatted error message.
     *
     * @return The formatted error string
     */
    @Override
    public String toString() {
        return getMessage();
    }

    /**
     * Dedents a multi-line string by removing common leading whitespace.
     *
     * @param text The text to dedent
     * @return Dedented text
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
