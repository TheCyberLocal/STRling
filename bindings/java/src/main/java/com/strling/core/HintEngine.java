package com.strling.core;

public final class HintEngine {

    private HintEngine() {}

    /**
     * Provide a short contextual hint for known error messages. Returns null when
     * no hint is available.
     */
    public static String getHint(String message, String text, int pos) {
        if (message == null) return null;

        switch (message) {
            case "Unterminated group":
                return "A group opened with '(' was not terminated. Add a matching ')' at the appropriate place.";
            case "Unterminated character class":
                return "A character class opened with '[' was not terminated. Add a matching ']' to close it.";
            case "Unexpected token":
                return "The token does not have a matching opening '('. Consider escaping it with '\\)'.";
            case "Cannot quantify anchor":
                return "Anchors match positions and cannot be quantified; they don't consume characters and therefore cannot be quantified.";
            case "Inline modifiers `(?imsx)` are not supported":
                return "Inline modifiers are not supported; use the %flags directive instead to set inline options.";
            default:
                return null;
        }
    }
}
