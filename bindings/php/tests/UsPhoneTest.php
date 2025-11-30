<?php

namespace STRling\Tests;

use PHPUnit\Framework\TestCase;
use STRling\Simply;
use STRling\Pattern;

/**
 * Test suite demonstrating the Simply API with a US phone number pattern.
 * 
 * This test validates the Simply API's ability to construct complex patterns
 * using static methods with exact structural parity to Python/TypeScript bindings.
 * 
 * @package STRling\Tests
 */
class UsPhoneTest extends TestCase
{
    /**
     * Test building a US phone number pattern using the Simply API.
     * 
     * Demonstrates the target UX with structural identity:
     * - Uses Simply::capture($inner), NOT $inner->capture()
     * - Uses `may`, `inChars`, `merge` naming
     *   Note: `inChars` matches TypeScript exactly (camelCase). Python uses `in_chars` (snake_case)
     */
    public function testUsPhonePattern(): void
    {
        // Build US phone pattern: ^(\d{3})[-. ]?(\d{3})[-. ]?(\d{4})$
        $phone = Simply::merge(
            Simply::start(),
            Simply::capture(Simply::digit(3)),
            Simply::may(Simply::inChars("-. ")),
            Simply::capture(Simply::digit(3)),
            Simply::may(Simply::inChars("-. ")),
            Simply::capture(Simply::digit(4)),
            Simply::end()
        );
        
        // Verify we got a Pattern object
        $this->assertInstanceOf(Pattern::class, $phone);
        
        // Compile to IR (JSON format for demonstration)
        $ir = $phone->compile();
        $this->assertIsString($ir);
        
        // Verify the IR contains expected structure
        $this->assertStringContainsString('"type"', $ir);
        $this->assertStringContainsString('Seq', $ir);
        $this->assertStringContainsString('Group', $ir);
        $this->assertStringContainsString('Anchor', $ir);
    }
    
    /**
     * Test individual Simply API methods.
     */
    public function testSimplyApiMethods(): void
    {
        // Test digit() with various signatures
        $digit1 = Simply::digit();  // Match single digit
        $this->assertInstanceOf(Pattern::class, $digit1);
        
        $digit3 = Simply::digit(3);  // Match exactly 3 digits
        $this->assertInstanceOf(Pattern::class, $digit3);
        
        $digit35 = Simply::digit(3, 5);  // Match 3-5 digits
        $this->assertInstanceOf(Pattern::class, $digit35);
        
        // Test inChars()
        $sep = Simply::inChars("-. ");
        $this->assertInstanceOf(Pattern::class, $sep);
        
        // Test start() and end()
        $start = Simply::start();
        $end = Simply::end();
        $this->assertInstanceOf(Pattern::class, $start);
        $this->assertInstanceOf(Pattern::class, $end);
        
        // Test capture()
        $captured = Simply::capture($digit3);
        $this->assertInstanceOf(Pattern::class, $captured);
        
        // Test may()
        $optional = Simply::may($sep);
        $this->assertInstanceOf(Pattern::class, $optional);
        
        // Test merge()
        $merged = Simply::merge($start, $digit3, $end);
        $this->assertInstanceOf(Pattern::class, $merged);
    }
    
    /**
     * Test structural identity - capture wraps the pattern.
     */
    public function testStructuralIdentity(): void
    {
        // The API uses Simply::capture($inner), not $inner->capture()
        $digit = Simply::digit(3);
        $captured = Simply::capture($digit);
        
        // Both should be Pattern objects
        $this->assertInstanceOf(Pattern::class, $digit);
        $this->assertInstanceOf(Pattern::class, $captured);
        
        // Verify they compile without errors
        $digitIr = $digit->compile();
        $capturedIr = $captured->compile();
        
        $this->assertIsString($digitIr);
        $this->assertIsString($capturedIr);
        
        // Captured version should contain Group in IR
        $this->assertStringContainsString('Group', $capturedIr);
    }
}
