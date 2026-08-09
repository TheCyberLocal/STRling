<?php

namespace STRling\Tests;

use PHPUnit\Framework\TestCase;
use STRling\Core\Parser;
use STRling\Compiler;
use STRling\Emitters\Pcre2Emitter;
use STRling\Core\Nodes\Flags;

/**
 * Interaction Tests - Parser → Compiler → Emitter handoffs
 *
 * This test suite validates the handoff between pipeline stages:
 * - Parser → Compiler: Ensures AST is correctly consumed
 * - Compiler → Emitter: Ensures IR is correctly transformed to regex
 */
class InteractionTest extends TestCase
{
    private Compiler $compiler;
    private Pcre2Emitter $emitter;

    protected function setUp(): void
    {
        $this->compiler = new Compiler();
        $this->emitter = new Pcre2Emitter();
    }

    // ========================================================================
    // Parser → Compiler Handoff Tests
    // ========================================================================

    public function testParserCompiler_SimpleLiteral(): void
    {
        $parser = new Parser("hello");
        [$flags, $ast] = $parser->parse();

        $ir = $this->compiler->compile($ast);

        $this->assertNotNull($ir);
        $serialized = json_decode(json_encode($ir), true);
        $this->assertEquals('Lit', $serialized['ir']);
    }

    public function testParserCompiler_Quantifier(): void
    {
        $parser = new Parser("a+");
        [$flags, $ast] = $parser->parse();

        $ir = $this->compiler->compile($ast);

        $serialized = json_decode(json_encode($ir), true);
        $this->assertEquals('Quant', $serialized['ir']);
    }

    public function testParserCompiler_CharacterClass(): void
    {
        $parser = new Parser("[abc]");
        [$flags, $ast] = $parser->parse();

        $ir = $this->compiler->compile($ast);

        $serialized = json_decode(json_encode($ir), true);
        $this->assertEquals('CharClass', $serialized['ir']);
    }

    public function testParserCompiler_CapturingGroup(): void
    {
        $parser = new Parser("(abc)");
        [$flags, $ast] = $parser->parse();

        $ir = $this->compiler->compile($ast);

        $serialized = json_decode(json_encode($ir), true);
        $this->assertEquals('Group', $serialized['ir']);
    }

    public function testParserCompiler_Alternation(): void
    {
        $parser = new Parser("a|b");
        [$flags, $ast] = $parser->parse();

        $ir = $this->compiler->compile($ast);

        $serialized = json_decode(json_encode($ir), true);
        $this->assertEquals('Alt', $serialized['ir']);
    }

    public function testParserCompiler_NamedGroup(): void
    {
        $parser = new Parser("(?<name>abc)");
        [$flags, $ast] = $parser->parse();

        $ir = $this->compiler->compile($ast);

        $serialized = json_decode(json_encode($ir), true);
        $this->assertEquals('Group', $serialized['ir']);
    }

    public function testParserCompiler_Lookahead(): void
    {
        $parser = new Parser("(?=abc)");
        [$flags, $ast] = $parser->parse();

        $ir = $this->compiler->compile($ast);

        $serialized = json_decode(json_encode($ir), true);
        $this->assertEquals('Look', $serialized['ir']);
    }

    public function testParserCompiler_Lookbehind(): void
    {
        $parser = new Parser("(?<=abc)");
        [$flags, $ast] = $parser->parse();

        $ir = $this->compiler->compile($ast);

        $serialized = json_decode(json_encode($ir), true);
        $this->assertEquals('Look', $serialized['ir']);
    }

    // ========================================================================
    // Compiler → Emitter Handoff Tests
    // ========================================================================

    public function testCompilerEmitter_SimpleLiteral(): void
    {
        $regex = $this->compileToRegex("hello");
        $this->assertEquals("hello", $regex);
    }

    public function testCompilerEmitter_DigitShorthand(): void
    {
        $regex = $this->compileToRegex("\\d+");
        $this->assertEquals("\\d+", $regex);
    }

    public function testCompilerEmitter_CharacterClass(): void
    {
        $regex = $this->compileToRegex("[abc]");
        $this->assertEquals("[abc]", $regex);
    }

    public function testCompilerEmitter_CharacterClassRange(): void
    {
        $regex = $this->compileToRegex("[a-z]");
        $this->assertEquals("[a-z]", $regex);
    }

    public function testCompilerEmitter_NegatedClass(): void
    {
        $regex = $this->compileToRegex("[^abc]");
        $this->assertEquals("[^abc]", $regex);
    }

    public function testCompilerEmitter_QuantifierPlus(): void
    {
        $regex = $this->compileToRegex("a+");
        $this->assertEquals("a+", $regex);
    }

    public function testCompilerEmitter_QuantifierStar(): void
    {
        $regex = $this->compileToRegex("a*");
        $this->assertEquals("a*", $regex);
    }

    public function testCompilerEmitter_QuantifierOptional(): void
    {
        $regex = $this->compileToRegex("a?");
        $this->assertEquals("a?", $regex);
    }

    public function testCompilerEmitter_QuantifierExact(): void
    {
        $regex = $this->compileToRegex("a{3}");
        $this->assertEquals("a{3}", $regex);
    }

    public function testCompilerEmitter_QuantifierRange(): void
    {
        $regex = $this->compileToRegex("a{2,5}");
        $this->assertEquals("a{2,5}", $regex);
    }

    public function testCompilerEmitter_QuantifierLazy(): void
    {
        $regex = $this->compileToRegex("a+?");
        $this->assertEquals("a+?", $regex);
    }

    public function testCompilerEmitter_CapturingGroup(): void
    {
        $regex = $this->compileToRegex("(abc)");
        $this->assertEquals("(abc)", $regex);
    }

    public function testCompilerEmitter_NonCapturingGroup(): void
    {
        $regex = $this->compileToRegex("(?:abc)");
        $this->assertEquals("(?:abc)", $regex);
    }

    public function testCompilerEmitter_NamedGroup(): void
    {
        $regex = $this->compileToRegex("(?<name>abc)");
        $this->assertEquals("(?<name>abc)", $regex);
    }

    public function testCompilerEmitter_Alternation(): void
    {
        $regex = $this->compileToRegex("cat|dog");
        $this->assertEquals("cat|dog", $regex);
    }

    public function testCompilerEmitter_Anchors(): void
    {
        $regex = $this->compileToRegex("^abc\$");
        $this->assertEquals("^abc\$", $regex);
    }

    public function testCompilerEmitter_PositiveLookahead(): void
    {
        $regex = $this->compileToRegex("foo(?=bar)");
        $this->assertEquals("foo(?=bar)", $regex);
    }

    public function testCompilerEmitter_NegativeLookahead(): void
    {
        $regex = $this->compileToRegex("foo(?!bar)");
        $this->assertEquals("foo(?!bar)", $regex);
    }

    public function testCompilerEmitter_PositiveLookbehind(): void
    {
        $regex = $this->compileToRegex("(?<=foo)bar");
        $this->assertEquals("(?<=foo)bar", $regex);
    }

    public function testCompilerEmitter_NegativeLookbehind(): void
    {
        $regex = $this->compileToRegex("(?<!foo)bar");
        $this->assertEquals("(?<!foo)bar", $regex);
    }

    // ========================================================================
    // Semantic Edge Case Tests
    // ========================================================================

    public function test_semantic_duplicate_capture_group(): void
    {
        $this->expectException(\STRling\Core\STRlingParseError::class);
        $parser = new Parser("(?<name>a)(?<name>b)");
        $parser->parse();
    }

    public function test_semantic_ranges(): void
    {
        // Invalid range [z-a] should produce an error
        $this->expectException(\STRling\Core\STRlingParseError::class);
        $parser = new Parser("[z-a]");
        $parser->parse();
    }

    // ========================================================================
    // Full Pipeline Tests
    // ========================================================================

    public function testFullPipeline_PhoneNumber(): void
    {
        $regex = $this->compileToRegex("(\\d{3})[-. ]?(\\d{3})[-. ]?(\\d{4})");
        $this->assertEquals("(\\d{3})[-. ]?(\\d{3})[-. ]?(\\d{4})", $regex);
    }

    public function testFullPipeline_IPv4(): void
    {
        $regex = $this->compileToRegex("(\\d{1,3})\\.(\\d{1,3})\\.(\\d{1,3})\\.(\\d{1,3})");
        $this->assertEquals("(\\d{1,3})\\.(\\d{1,3})\\.(\\d{1,3})\\.(\\d{1,3})", $regex);
    }

    // ========================================================================
    // Helper Methods
    // ========================================================================

    private function compileToRegex(string $dsl): string
    {
        $parser = new Parser($dsl);
        [$flags, $ast] = $parser->parse();
        $ir = $this->compiler->compile($ast);
        return $this->emitter->emit($ir, $flags);
    }
}
