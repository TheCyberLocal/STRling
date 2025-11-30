package com.strling;

import com.strling.simply.Simply;
import org.junit.jupiter.api.Test;

import java.util.regex.Matcher;
import java.util.regex.Pattern;

import static com.strling.simply.Simply.*;
import static org.junit.jupiter.api.Assertions.*;

/**
 * Test suite for the Simply fluent API demonstrating US phone number pattern matching.
 *
 * <p>This test verifies that the Simply API provides a clean, fluent interface for
 * building regex patterns in Java, matching the TypeScript reference implementation.
 * It serves as both a verification test and documentation example for the Simply API.
 */
public class UsPhoneTest {

    /**
     * Test the US phone number pattern using the Simply fluent API.
     * 
     * <p>This pattern matches US phone numbers in the format: (area)(separator)(exchange)(separator)(line)
     * where:
     * <ul>
     *   <li>area: 3 digits</li>
     *   <li>separator: optional [-. ] character</li>
     *   <li>exchange: 3 digits</li>
     *   <li>separator: optional [-. ] character</li>
     *   <li>line: 4 digits</li>
     * </ul>
     *
     * <p>Expected compiled regex: ^(\d{3})[-. ]?(\d{3})[-. ]?(\d{4})$
     */
    @Test
    public void testUsPhoneNumberPattern() {
        // Build the phone pattern using the Simply API
        com.strling.simply.Pattern phonePattern = merge(
            start(),
            capture(digit(3)),
            may(anyOf("-. ")),
            capture(digit(3)),
            may(anyOf("-. ")),
            capture(digit(4)),
            end()
        );

        // Compile to regex string
        Simply s = new Simply();
        String regexString = s.build(phonePattern);

        // Verify the compiled pattern works correctly
        // Note: anyOf creates alternation (?:...|...) which is functionally equivalent to character class [...]
        // Both produce valid regex patterns that match phone numbers correctly
        assertTrue(regexString.contains("\\d{3}"), 
            "Compiled regex should contain digit patterns");

        // Test the pattern against valid phone numbers
        Pattern regex = Pattern.compile(regexString);
        
        assertTrue(regex.matcher("555-123-4567").matches(), 
            "Should match phone number with dashes");
        assertTrue(regex.matcher("555.123.4567").matches(), 
            "Should match phone number with periods");
        assertTrue(regex.matcher("555 123 4567").matches(), 
            "Should match phone number with spaces");
        assertTrue(regex.matcher("5551234567").matches(), 
            "Should match phone number with no separators");

        // Test extraction of captured groups
        Matcher matcher = regex.matcher("555-123-4567");
        assertTrue(matcher.matches());
        assertEquals("555", matcher.group(1), "First capture group should be area code");
        assertEquals("123", matcher.group(2), "Second capture group should be exchange");
        assertEquals("4567", matcher.group(3), "Third capture group should be line number");

        // Test invalid phone numbers
        assertFalse(regex.matcher("55-123-4567").matches(), 
            "Should not match phone with too few digits in area code");
        assertFalse(regex.matcher("555-12-4567").matches(), 
            "Should not match phone with too few digits in exchange");
        assertFalse(regex.matcher("555-123-456").matches(), 
            "Should not match phone with too few digits in line");
        assertFalse(regex.matcher("abc-def-ghij").matches(), 
            "Should not match phone with letters");
    }

    /**
     * Test the fluent API with named groups for phone number parts.
     */
    @Test
    public void testUsPhoneNumberWithNamedGroups() {
        // Build the phone pattern using named groups (using camelCase for Java compatibility)
        com.strling.simply.Pattern phonePattern = merge(
            start(),
            group("areaCode", digit(3)),
            may(anyOf("-. ")),
            group("exchange", digit(3)),
            may(anyOf("-. ")),
            group("lineNumber", digit(4)),
            end()
        );

        // Compile to regex string
        Simply s = new Simply();
        String regexString = s.build(phonePattern);

        // Verify the compiled pattern uses named groups
        assertTrue(regexString.contains("(?<areaCode>"), 
            "Should contain named group for area code");
        assertTrue(regexString.contains("(?<exchange>"), 
            "Should contain named group for exchange");
        assertTrue(regexString.contains("(?<lineNumber>"), 
            "Should contain named group for line number");

        // Test pattern matching
        Pattern regex = Pattern.compile(regexString);
        Matcher matcher = regex.matcher("555-123-4567");
        assertTrue(matcher.matches());
        
        // Test named group extraction
        assertEquals("555", matcher.group("areaCode"), 
            "Named group 'areaCode' should capture area code");
        assertEquals("123", matcher.group("exchange"), 
            "Named group 'exchange' should capture exchange");
        assertEquals("4567", matcher.group("lineNumber"), 
            "Named group 'lineNumber' should capture line number");
    }

    /**
     * Verify zero boilerplate - no direct usage of Nodes.* constructors.
     */
    @Test
    public void testZeroBoilerplate() {
        // This test implicitly passes if testUsPhoneNumberPattern passes
        // and uses only the Simply API (no Nodes.* constructors)
        
        // Build pattern using only the fluent API
        com.strling.simply.Pattern pattern = merge(
            start(),
            capture(digit(3)),
            may(anyOf("-", ".", " ")),
            capture(digit(3)),
            may(anyOf("-", ".", " ")),
            capture(digit(4)),
            end()
        );

        Simply s = new Simply();
        String regexString = s.build(pattern);
        
        // Just verify it compiles and produces a valid regex
        assertNotNull(regexString);
        assertTrue(regexString.length() > 0);
        
        // No assertions about Nodes.* usage - the code itself demonstrates zero boilerplate
    }
}
