<?php

namespace STRling\Tests\Core;

use PHPUnit\Framework\TestCase;
use STRling\Core\STRlingParseError;

/**
 * Test suite for Error handling classes.
 * 
 * @package STRling\Tests\Core
 */
class ErrorsTest extends TestCase
{
    public function testBasicError(): void
    {
        $error = new STRlingParseError('Unexpected token', 5);
        
        $this->assertEquals(5, $error->pos);
        $this->assertStringContainsString('Unexpected token', $error->getMessage());
    }
    
    public function testErrorWithText(): void
    {
        $error = new STRlingParseError(
            'Unexpected token',
            5,
            'hello world'
        );
        
        $formatted = $error->toFormattedString();
        $this->assertStringContainsString('STRling Parse Error', $formatted);
        $this->assertStringContainsString('Unexpected token', $formatted);
        $this->assertStringContainsString('hello world', $formatted);
        $this->assertStringContainsString('^', $formatted);
    }
    
    public function testErrorWithHint(): void
    {
        $error = new STRlingParseError(
            'Unexpected token',
            5,
            'hello world',
            'Use quotes around literal strings'
        );
        
        $formatted = $error->toFormattedString();
        $this->assertStringContainsString('Hint:', $formatted);
        $this->assertStringContainsString('Use quotes around literal strings', $formatted);
    }
    
    public function testErrorToString(): void
    {
        $error = new STRlingParseError(
            'Unexpected token',
            5,
            'hello world',
            'Check your syntax'
        );
        
        $toString = (string) $error;
        $this->assertStringContainsString('STRling Parse Error', $toString);
        $this->assertStringContainsString('Hint:', $toString);
    }
    
    public function testMultilineErrorFormatting(): void
    {
        $text = "line 1\nline 2 error\nline 3";
        $error = new STRlingParseError(
            'Syntax error',
            14,  // Position in "line 2 error"
            $text
        );
        
        $formatted = $error->toFormattedString();
        $this->assertStringContainsString('line 2 error', $formatted);
        $this->assertStringContainsString('^', $formatted);
    }
    
    public function testErrorLspDiagnostic(): void
    {
        $error = new STRlingParseError(
            'Unexpected token',
            5,
            'hello world',
            'Use quotes'
        );
        
        $diagnostic = $error->toLspDiagnostic();
        
        $this->assertArrayHasKey('range', $diagnostic);
        $this->assertArrayHasKey('severity', $diagnostic);
        $this->assertArrayHasKey('message', $diagnostic);
        $this->assertArrayHasKey('source', $diagnostic);
        $this->assertArrayHasKey('code', $diagnostic);
        
        $this->assertEquals(1, $diagnostic['severity']);
        $this->assertEquals('STRling', $diagnostic['source']);
        $this->assertStringContainsString('Unexpected token', $diagnostic['message']);
        $this->assertStringContainsString('Hint: Use quotes', $diagnostic['message']);
    }
    
    public function testErrorLspDiagnosticRange(): void
    {
        $error = new STRlingParseError(
            'Error',
            7,
            'hello world'
        );
        
        $diagnostic = $error->toLspDiagnostic();
        $range = $diagnostic['range'];
        
        $this->assertArrayHasKey('start', $range);
        $this->assertArrayHasKey('end', $range);
        $this->assertArrayHasKey('line', $range['start']);
        $this->assertArrayHasKey('character', $range['start']);
        
        // Single line, so line should be 0
        $this->assertEquals(0, $range['start']['line']);
        $this->assertEquals(7, $range['start']['character']);
    }
    
    public function testErrorCodeGeneration(): void
    {
        $error = new STRlingParseError(
            'Unexpected token "}"',
            0,
            'test'
        );
        
        $diagnostic = $error->toLspDiagnostic();
        
        // Error code should be normalized (lowercase, underscores)
        $this->assertIsString($diagnostic['code']);
        $this->assertStringNotContainsString(' ', $diagnostic['code']);
        $this->assertStringNotContainsString('"', $diagnostic['code']);
    }
    
    public function testErrorWithEmptyText(): void
    {
        $error = new STRlingParseError('Error', 5, '');
        
        $formatted = $error->toFormattedString();
        $this->assertStringContainsString('Error at position 5', $formatted);
    }
}
