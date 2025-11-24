package strling

import kotlin.test.*
import kotlinx.serialization.json.JsonPrimitive
import strling.core.*

/**
 * US Phone Number Pattern Test
 * 
 * Validates the Simply API by constructing a US phone number pattern
 * that matches the TypeScript "Gold Standard" implementation.
 * 
 * Target pattern: ^(\d{3})[-. ]?(\d{3})[-. ]?(\d{4})$
 */
class UsPhoneTest {
    
    @Test
    fun `Should build US phone pattern using Simply API`() {
        // Build pattern: ^(\d{3})[-. ]?(\d{3})[-. ]?(\d{4})$
        val pattern = Simply.merge(
            Simply.start(),
            Simply.capture(Simply.digit(3)),
            Simply.may(Simply.anyOf("-. ")),
            Simply.capture(Simply.digit(3)),
            Simply.may(Simply.anyOf("-. ")),
            Simply.capture(Simply.digit(4)),
            Simply.end()
        )
        
        // Verify it's a sequence
        assertTrue(pattern.node is Sequence, "Pattern should be a Sequence")
        
        val seq = pattern.node as Sequence
        assertEquals(7, seq.parts.size, "Should have 7 parts")
        
        // Verify structure
        assertTrue(seq.parts[0] is Anchor, "Part 0 should be Anchor")
        assertEquals("Start", (seq.parts[0] as Anchor).at, "Should be Start anchor")
        
        assertTrue(seq.parts[1] is Group, "Part 1 should be Group")
        assertTrue((seq.parts[1] as Group).capturing, "Should be capturing")
        
        assertTrue(seq.parts[2] is Quantifier, "Part 2 should be Quantifier")
        assertEquals(0, (seq.parts[2] as Quantifier).min, "Should have min 0")
        assertEquals(JsonPrimitive(1), (seq.parts[2] as Quantifier).max, "Should have max 1")
        
        assertTrue(seq.parts[6] is Anchor, "Part 6 should be Anchor")
        assertEquals("End", (seq.parts[6] as Anchor).at, "Should be End anchor")
    }
    
    @Test
    fun `Should demonstrate zero nulls - no explicit null parameters`() {
        // All these calls should work without passing null explicitly
        val d3 = Simply.digit(3)
        val d4 = Simply.digit(4)
        val sep = Simply.anyOf("-. ")
        
        // Build the pattern using only non-null parameters
        val phone = Simply.merge(
            Simply.start(),
            Simply.capture(d3),
            Simply.may(sep),
            Simply.capture(Simply.digit(3)),
            Simply.may(Simply.anyOf("-. ")),
            Simply.capture(d4),
            Simply.end()
        )
        
        assertNotNull(phone, "Pattern should not be null")
        assertTrue(phone.node is Sequence, "Should create valid pattern")
    }
    
    @Test
    fun `Should use gold standard naming - anyOf for character sets`() {
        // The API should use anyOf, not inChars
        val charSet = Simply.anyOf("-. ")
        
        assertTrue(charSet.node is CharacterClass, "anyOf should create CharacterClass")
        val cc = charSet.node as CharacterClass
        assertFalse(cc.negated, "Should not be negated")
        assertEquals(3, cc.members.size, "Should have 3 characters")
    }
    
    @Test
    fun `Should support merge for sequential patterns`() {
        val merged = Simply.merge(
            Simply.digit(3),
            "-",
            Simply.digit(4)
        )
        
        assertTrue(merged.node is Sequence, "merge should create Sequence")
        val seq = merged.node as Sequence
        assertEquals(3, seq.parts.size, "Should have 3 parts")
    }
    
    @Test
    fun `Should support may for optional patterns`() {
        val optional = Simply.may(Simply.anyOf("-. "))
        
        assertTrue(optional.node is Quantifier, "may should create Quantifier")
        val quant = optional.node as Quantifier
        assertEquals(0, quant.min, "Should have min 0")
        assertEquals(JsonPrimitive(1), quant.max, "Should have max 1")
    }
    
    @Test
    fun `Should support capture for numbered groups`() {
        val captured = Simply.capture(Simply.digit(3))
        
        assertTrue(captured.node is Group, "capture should create Group")
        val group = captured.node as Group
        assertTrue(group.capturing, "Should be capturing")
        assertNull(group.name, "Should not have a name (numbered group)")
    }
    
    @Test
    fun `Should support fluent pattern methods`() {
        // Test optional() method
        val digit = Simply.digit()
        val optionalDigit = digit.optional()
        
        assertTrue(optionalDigit.node is Quantifier, "optional() should create Quantifier")
        
        // Test asCapture() method
        val capturedDigit = digit.asCapture()
        assertTrue(capturedDigit.node is Group, "asCapture() should create Group")
        
        // Test repeat() method
        val repeatedDigit = digit.repeat(2, 4)
        assertTrue(repeatedDigit.node is Quantifier, "repeat() should create Quantifier")
        val quant = repeatedDigit.node as Quantifier
        assertEquals(2, quant.min, "Should have min 2")
        assertEquals(JsonPrimitive(4), quant.max, "Should have max 4")
    }
    
    @Test
    fun `Should support method chaining`() {
        // Demonstrate fluent chaining
        val pattern = Simply.digit(3).asCapture()
        
        assertTrue(pattern.node is Group, "Should create Group")
        val group = pattern.node as Group
        assertTrue(group.capturing, "Should be capturing")
        
        // The body should be a quantified digit pattern
        assertTrue(group.body is Quantifier, "Body should be Quantifier")
    }
    
    @Test
    fun `Should validate pattern structure matches TypeScript reference`() {
        // This is the exact pattern from the acceptance criteria
        val phone = Simply.merge(
            Simply.start(),
            Simply.capture(Simply.digit(3)),
            Simply.may(Simply.anyOf("-. ")),
            Simply.capture(Simply.digit(3)),
            Simply.may(Simply.anyOf("-. ")),
            Simply.capture(Simply.digit(4)),
            Simply.end()
        )
        
        // Expected structure:
        // Sequence[
        //   Anchor(Start),
        //   Group(Quantifier(digit, 3, 3)),
        //   Quantifier(CharClass[-. ], 0, 1),
        //   Group(Quantifier(digit, 3, 3)),
        //   Quantifier(CharClass[-. ], 0, 1),
        //   Group(Quantifier(digit, 4, 4)),
        //   Anchor(End)
        // ]
        
        val seq = phone.node as Sequence
        
        // Part 1: First capture group with 3 digits
        val group1 = seq.parts[1] as Group
        assertTrue(group1.capturing)
        val quant1 = group1.body as Quantifier
        assertEquals(3, quant1.min)
        assertEquals(JsonPrimitive(3), quant1.max)
        
        // Part 2: Optional separator
        val sep1 = seq.parts[2] as Quantifier
        assertEquals(0, sep1.min)
        assertEquals(JsonPrimitive(1), sep1.max)
        assertTrue(sep1.target is CharacterClass)
        
        // Part 3: Second capture group with 3 digits
        val group2 = seq.parts[3] as Group
        assertTrue(group2.capturing)
        val quant2 = group2.body as Quantifier
        assertEquals(3, quant2.min)
        
        // Part 5: Third capture group with 4 digits
        val group3 = seq.parts[5] as Group
        assertTrue(group3.capturing)
        val quant3 = group3.body as Quantifier
        assertEquals(4, quant3.min)
        assertEquals(JsonPrimitive(4), quant3.max)
    }
    
    @Test
    fun `Should support all basic static patterns`() {
        // Verify all basic pattern creators exist and work
        assertNotNull(Simply.start())
        assertNotNull(Simply.end())
        assertNotNull(Simply.digit())
        assertNotNull(Simply.letter())
        assertNotNull(Simply.alphaNum())
        assertNotNull(Simply.whitespace())
        assertNotNull(Simply.literal("test"))
        
        // Verify they create appropriate node types
        assertTrue(Simply.start().node is Anchor)
        assertTrue(Simply.end().node is Anchor)
        assertTrue(Simply.digit().node is CharacterClass)
        assertTrue(Simply.letter().node is CharacterClass)
        assertTrue(Simply.literal("x").node is Literal)
    }
    
    @Test
    fun `Should support between for ranges`() {
        // Test digit range
        val digitRange = Simply.between(0, 9)
        assertTrue(digitRange.node is CharacterClass)
        
        // Test letter range
        val letterRange = Simply.between('a', 'z')
        assertTrue(letterRange.node is CharacterClass)
        
        val cc = letterRange.node as CharacterClass
        assertFalse(cc.negated)
        assertEquals(1, cc.members.size)
        assertTrue(cc.members[0] is Range)
    }
    
    @Test
    fun `Should reject invalid between ranges`() {
        // Invalid: start > end
        assertFails { Simply.between(9, 0) }
        
        // Invalid: mixed case letters
        assertFails { Simply.between('a', 'Z') }
        
        // Invalid: mixed types
        assertFails { Simply.between('a', 9) }
    }
    
    @Test
    fun `Should support named groups`() {
        val pattern = Simply.group("areaCode", Simply.digit(3))
        
        assertTrue(pattern.node is Group)
        val group = pattern.node as Group
        assertTrue(group.capturing)
        assertEquals("areaCode", group.name)
        assertEquals(listOf("areaCode"), pattern.namedGroups)
    }
    
    @Test
    fun `Should propagate named groups through combinators`() {
        // Create patterns with named groups
        val group1 = Simply.group("first", Simply.digit(3))
        val group2 = Simply.group("second", Simply.letter(2))
        
        // Test merge propagates named groups
        val merged = Simply.merge(group1, "-", group2)
        assertEquals(listOf("first", "second"), merged.namedGroups)
        
        // Test anyOf propagates named groups
        val anyOfPattern = Simply.anyOf(group1, group2)
        assertEquals(setOf("first", "second"), anyOfPattern.namedGroups.toSet())
        
        // Test may propagates named groups
        val optional = Simply.may(group1)
        assertEquals(listOf("first"), optional.namedGroups)
        
        // Test capture propagates named groups
        val captured = Simply.capture(group1)
        assertEquals(listOf("first"), captured.namedGroups)
        
        // Test nested group combines named groups
        val nestedGroup = Simply.group("outer", group1)
        assertEquals(listOf("first", "outer"), nestedGroup.namedGroups)
    }
    
    @Test
    fun `Should prevent named group repetition`() {
        val namedPattern = Simply.group("test", Simply.literal("x"))
        
        // Should fail when trying to repeat more than once
        assertFails { namedPattern.repeat(2) }
        assertFails { namedPattern.repeat(0, 2) }
        
        // But repeat(0, 1) should work (same as optional)
        assertNotNull(namedPattern.repeat(0, 1))
        
        // And repeat(1, 1) should work (exactly once)
        assertNotNull(namedPattern.repeat(1, 1))
    }
    
    @Test
    fun `Should validate between with mixed types correctly`() {
        // Valid: both are digits (using string)
        assertNotNull(Simply.between("0", "9"))
        
        // Valid: both are letters (using string)
        assertNotNull(Simply.between("a", "z"))
        
        // Invalid: mixed digit and letter strings
        assertFails { Simply.between("0", "z") }
        assertFails { Simply.between("a", "9") }
    }
}
