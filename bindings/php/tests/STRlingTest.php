<?php

namespace STRling\Tests;

use PHPUnit\Framework\TestCase;
use STRling\STRling;

/**
 * Basic test suite for STRling PHP binding.
 * 
 * This test class will be expanded in Task 2 with functional tests for the Parser,
 * Compiler, and Validator components.
 * 
 * @package STRling\Tests
 */
class STRlingTest extends TestCase
{
    /**
     * Basic smoke test to verify the package structure is set up correctly.
     */
    public function testPackageStructure(): void
    {
        // Verify the main STRling class exists
        $this->assertTrue(class_exists(STRling::class));
        
        // Verify version constant is defined
        $this->assertIsString(STRling::VERSION);
    }
}
