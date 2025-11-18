package com.strling.simply;

import com.strling.core.Nodes.*;
import java.util.Arrays;
import java.util.ArrayList;
import java.util.List;

/**
 * Character set and range functions for pattern matching in STRling.
 *
 * <p>This module provides functions for creating character class patterns, including
 * ranges (between), custom sets (customSet), and utilities for combining sets.
 * Character sets are fundamental building blocks for matching specific groups of
 * characters, and these functions make it easy to define complex character matching
 * rules without dealing with raw regex character class syntax.</p>
 */
public class Sets {
    
    /**
     * Matches all characters within and including the start and end of a letter or digit range.
     *
     * @param start The starting character or digit of the range
     * @param end The ending character or digit of the range
     * @param minRep The minimum number of characters to match
     * @param maxRep The maximum number of characters to match
     * @return An instance of the Pattern class
     */
    public static Pattern between(Object start, Object end, Integer minRep, Integer maxRep) {
        if (start instanceof String && end instanceof String) {
            return betweenChars((String) start, (String) end, minRep, maxRep);
        } else if (start instanceof Integer && end instanceof Integer) {
            return betweenDigits((Integer) start, (Integer) end, minRep, maxRep);
        } else {
            String message = "\n" +
                "Method: simply.between(start, end)\n\n" +
                "The 'start' and 'end' arguments must both be integers (0-9) or letters of the same case (A-Z or a-z).";
            throw new STRlingError(message);
        }
    }
    
    /**
     * Matches all characters within and including the start and end of a letter or digit range.
     *
     * @param start The starting character or digit of the range
     * @param end The ending character or digit of the range
     * @return An instance of the Pattern class
     */
    public static Pattern between(Object start, Object end) {
        return between(start, end, null, null);
    }
    
    /**
     * Helper method for between with character ranges.
     */
    private static Pattern betweenChars(String start, String end, Integer minRep, Integer maxRep) {
        // Validation logic
        if (start.length() != 1 || end.length() != 1) {
            throw new STRlingError("The 'start' and 'end' characters must be single letters.");
        }
        
        if (!start.matches("[a-zA-Z]") || !end.matches("[a-zA-Z]")) {
            throw new STRlingError("The 'start' and 'end' must be alphabetical characters.");
        }
        
        boolean startLower = Character.isLowerCase(start.charAt(0));
        boolean endLower = Character.isLowerCase(end.charAt(0));
        if (startLower != endLower) {
            throw new STRlingError("The 'start' and 'end' characters must be of the same case.");
        }
        
        if (start.charAt(0) > end.charAt(0)) {
            throw new STRlingError("The 'start' character must not be lexicographically greater than the 'end' character.");
        }
        
        ClassRange rangeNode = new ClassRange(start, end);
        Node node = new CharClass(false, Arrays.asList(rangeNode));
        Pattern p = new Pattern(node, true, false, false);
        return (minRep != null) ? p.call(minRep, maxRep) : p;
    }
    
    /**
     * Helper method for between with digit ranges.
     */
    private static Pattern betweenDigits(Integer start, Integer end, Integer minRep, Integer maxRep) {
        // Validation logic
        if (start > end) {
            throw new STRlingError("The 'start' integer must not be greater than the 'end' integer.");
        }
        
        if (start < 0 || start > 9 || end < 0 || end > 9) {
            throw new STRlingError("The 'start' and 'end' integers must be single digits (0-9).");
        }
        
        ClassRange rangeNode = new ClassRange(String.valueOf(start), String.valueOf(end));
        Node node = new CharClass(false, Arrays.asList(rangeNode));
        Pattern p = new Pattern(node, true, false, false);
        return (minRep != null) ? p.call(minRep, maxRep) : p;
    }
    
    /**
     * Matches any character not within or including the start and end of a letter or digit range.
     *
     * @param start The starting character or digit of the range
     * @param end The ending character or digit of the range
     * @param minRep The minimum number of characters to match
     * @param maxRep The maximum number of characters to match
     * @return An instance of the Pattern class
     */
    public static Pattern notBetween(Object start, Object end, Integer minRep, Integer maxRep) {
        if (start instanceof String && end instanceof String) {
            return notBetweenChars((String) start, (String) end, minRep, maxRep);
        } else if (start instanceof Integer && end instanceof Integer) {
            return notBetweenDigits((Integer) start, (Integer) end, minRep, maxRep);
        } else {
            String message = "\n" +
                "Method: simply.notBetween(start, end)\n\n" +
                "The 'start' and 'end' arguments must both be integers (0-9) or letters of the same case (A-Z or a-z).";
            throw new STRlingError(message);
        }
    }
    
    /**
     * Matches any character not within or including the start and end of a letter or digit range.
     *
     * @param start The starting character or digit of the range
     * @param end The ending character or digit of the range
     * @return An instance of the Pattern class
     */
    public static Pattern notBetween(Object start, Object end) {
        return notBetween(start, end, null, null);
    }
    
    /**
     * Helper method for notBetween with character ranges.
     */
    private static Pattern notBetweenChars(String start, String end, Integer minRep, Integer maxRep) {
        // Validation logic (similar to betweenChars)
        if (start.length() != 1 || end.length() != 1) {
            throw new STRlingError("The 'start' and 'end' characters must be single letters.");
        }
        
        if (!start.matches("[a-zA-Z]") || !end.matches("[a-zA-Z]")) {
            throw new STRlingError("The 'start' and 'end' must be alphabetical characters.");
        }
        
        boolean startLower = Character.isLowerCase(start.charAt(0));
        boolean endLower = Character.isLowerCase(end.charAt(0));
        if (startLower != endLower) {
            throw new STRlingError("The 'start' and 'end' characters must be of the same case.");
        }
        
        if (start.charAt(0) > end.charAt(0)) {
            throw new STRlingError("The 'start' character must not be lexicographically greater than the 'end' character.");
        }
        
        ClassRange rangeNode = new ClassRange(start, end);
        Node node = new CharClass(true, Arrays.asList(rangeNode));  // negated = true
        Pattern p = new Pattern(node, true, false, false);
        return (minRep != null) ? p.call(minRep, maxRep) : p;
    }
    
    /**
     * Helper method for notBetween with digit ranges.
     */
    private static Pattern notBetweenDigits(Integer start, Integer end, Integer minRep, Integer maxRep) {
        // Validation logic
        if (start > end) {
            throw new STRlingError("The 'start' integer must not be greater than the 'end' integer.");
        }
        
        if (start < 0 || start > 9 || end < 0 || end > 9) {
            throw new STRlingError("The 'start' and 'end' integers must be single digits (0-9).");
        }
        
        ClassRange rangeNode = new ClassRange(String.valueOf(start), String.valueOf(end));
        Node node = new CharClass(true, Arrays.asList(rangeNode));  // negated = true
        Pattern p = new Pattern(node, true, false, false);
        return (minRep != null) ? p.call(minRep, maxRep) : p;
    }
    
    /**
     * Matches any of the provided patterns, but they can't include subpatterns.
     *
     * @param patterns One or more non-composite patterns to match
     * @return An instance of the Pattern class
     */
    public static Pattern inChars(Object... patterns) {
        List<Pattern> cleanPatterns = new ArrayList<>();
        for (Object obj : patterns) {
            if (obj instanceof String) {
                obj = Pattern.lit((String) obj);
            }
            
            if (!(obj instanceof Pattern)) {
                String message = "\n" +
                    "Method: simply.inChars(...patterns)\n\n" +
                    "The parameters must be instances of Pattern or string.\n\n" +
                    "Use a string such as \"123abc$\" to match literal characters, or use a predefined set like simply.letter().";
                throw new STRlingError(message);
            }
            
            cleanPatterns.add((Pattern) obj);
        }
        
        // Check if any pattern is composite (Seq, Alt, Group, Quant, Look, etc.)
        String[] compositeNodeTypes = {"Seq", "Alt", "Group", "Quant", "Look"};
        for (Pattern p : cleanPatterns) {
            String nodeType = p.node.getClass().getSimpleName();
            for (String compType : compositeNodeTypes) {
                if (nodeType.equals(compType)) {
                    String message = "\n" +
                        "Method: simply.inChars(...patterns)\n\n" +
                        "All patterns must be non-composite.";
                    throw new STRlingError(message);
                }
            }
        }
        
        // Build the character class items by extracting them from input patterns
        List<ClassItem> items = new ArrayList<>();
        for (Pattern pattern : cleanPatterns) {
            String nodeType = pattern.node.getClass().getSimpleName();
            if (nodeType.equals("Lit")) {
                // For literals, add each character as a ClassLiteral item
                Lit litNode = (Lit) pattern.node;
                for (char c : litNode.value.toCharArray()) {
                    items.add(new ClassLiteral(String.valueOf(c)));
                }
            } else if (nodeType.equals("CharClass")) {
                // For character classes, add their items directly
                CharClass ccNode = (CharClass) pattern.node;
                items.addAll(ccNode.items);
            }
            // Handle other node types as needed
        }
        
        Node node = new CharClass(false, items);
        return new Pattern(node, true, false, false);
    }
    
    /**
     * Matches anything but the provided patterns, but they can't include subpatterns.
     *
     * @param patterns One or more non-composite patterns to avoid
     * @return An instance of the Pattern class
     */
    public static Pattern notInChars(Object... patterns) {
        List<Pattern> cleanPatterns = new ArrayList<>();
        for (Object obj : patterns) {
            if (obj instanceof String) {
                obj = Pattern.lit((String) obj);
            }
            
            if (!(obj instanceof Pattern)) {
                String message = "\n" +
                    "Method: simply.notInChars(...patterns)\n\n" +
                    "The parameters must be instances of Pattern or string.\n\n" +
                    "Use a string such as \"123abc$\" to match literal characters, or use a predefined set like simply.letter().";
                throw new STRlingError(message);
            }
            
            cleanPatterns.add((Pattern) obj);
        }
        
        // Check if any pattern is composite
        for (Pattern p : cleanPatterns) {
            if (p.isComposite()) {
                String message = "\n" +
                    "Method: simply.notInChars(...patterns)\n\n" +
                    "All patterns must be non-composite.";
                throw new STRlingError(message);
            }
        }
        
        // Build the character class items by extracting them from input patterns
        List<ClassItem> items = new ArrayList<>();
        for (Pattern pattern : cleanPatterns) {
            String nodeType = pattern.node.getClass().getSimpleName();
            if (nodeType.equals("Lit")) {
                // For literals, add each character as a ClassLiteral item
                Lit litNode = (Lit) pattern.node;
                for (char c : litNode.value.toCharArray()) {
                    items.add(new ClassLiteral(String.valueOf(c)));
                }
            } else if (nodeType.equals("CharClass")) {
                // For character classes, add their items directly
                CharClass ccNode = (CharClass) pattern.node;
                items.addAll(ccNode.items);
            }
            // Handle other node types as needed
        }
        
        Node node = new CharClass(true, items);
        return new Pattern(node, true, false, false);
    }
}
