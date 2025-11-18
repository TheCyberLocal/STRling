package strling

import kotlin.test.*

/**
 * Test suite for the STRling Kotlin binding.
 * 
 * This file will contain tests for the public API once it is implemented.
 */
class STRlingTest {
    @Test
    fun testVersion() {
        assertNotNull(STRling.version())
    }
}
