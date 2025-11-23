<?php

namespace STRling\Tests\Core;

use PHPUnit\Framework\TestCase;
use STRling\Core\Nodes\Flags;
use STRling\Core\Nodes\Literal;
use STRling\Core\Nodes\Dot;
use STRling\Core\Nodes\Anchor;
use STRling\Core\Nodes\Alternation;
use STRling\Core\Nodes\Sequence;
use STRling\Core\Nodes\CharacterClass;
use STRling\Core\Nodes\Range;
use STRling\Core\Nodes\Escape;
use STRling\Core\Nodes\Quantifier;
use STRling\Core\Nodes\Group;
use STRling\Core\Nodes\Backreference;
use STRling\Core\Nodes\Lookahead;
use STRling\Core\Nodes\NegativeLookbehind;

/**
 * Test suite for AST Node data structures.
 * 
 * @package STRling\Tests\Core
 */
class NodesTest extends TestCase
{
    public function testFlagsCreation(): void
    {
        $flags = new Flags();
        $this->assertFalse($flags->ignoreCase);
        $this->assertFalse($flags->multiline);
        $this->assertFalse($flags->dotAll);
    }
    
    public function testFlagsFromLetters(): void
    {
        $flags = Flags::fromLetters('ims');
        $this->assertTrue($flags->ignoreCase);
        $this->assertTrue($flags->multiline);
        $this->assertTrue($flags->dotAll);
        $this->assertFalse($flags->unicode);
        $this->assertFalse($flags->extended);
    }
    
    public function testFlagsJsonSerialize(): void
    {
        $flags = Flags::fromLetters('i');
        $dict = $flags->jsonSerialize();
        
        $this->assertArrayHasKey('ignoreCase', $dict);
        $this->assertTrue($dict['ignoreCase']);
        $this->assertFalse($dict['multiline']);
    }
    
    public function testLiteralNode(): void
    {
        $lit = new Literal('hello');
        $dict = $lit->jsonSerialize();
        
        $this->assertEquals('Literal', $dict['type']);
        $this->assertEquals('hello', $dict['value']);
    }
    
    public function testDotNode(): void
    {
        $dot = new Dot();
        $dict = $dot->jsonSerialize();
        
        $this->assertEquals('Dot', $dict['type']);
    }
    
    public function testAnchorNode(): void
    {
        $anchor = new Anchor('Start');
        $dict = $anchor->jsonSerialize();
        
        $this->assertEquals('Anchor', $dict['type']);
        $this->assertEquals('Start', $dict['at']);
    }
    
    public function testAlternationNode(): void
    {
        $alt = new Alternation([
            new Literal('a'),
            new Literal('b'),
            new Literal('c')
        ]);
        
        $dict = $alt->jsonSerialize();
        $this->assertEquals('Alternation', $dict['type']);
        $this->assertCount(3, $dict['alternatives']);
        $this->assertEquals('Literal', $dict['alternatives'][0]->jsonSerialize()['type']);
        $this->assertEquals('a', $dict['alternatives'][0]->jsonSerialize()['value']);
    }
    
    public function testSequenceNode(): void
    {
        $seq = new Sequence([
            new Literal('hello'),
            new Literal(' '),
            new Literal('world')
        ]);
        
        $dict = $seq->jsonSerialize();
        $this->assertEquals('Sequence', $dict['type']);
        $this->assertCount(3, $dict['parts']);
    }
    
    public function testCharacterClassWithLiterals(): void
    {
        $charClass = new CharacterClass(false, [
            new Literal('a'),
            new Literal('b'),
            new Literal('c')
        ]);
        
        $dict = $charClass->jsonSerialize();
        $this->assertEquals('CharacterClass', $dict['type']);
        $this->assertFalse($dict['negated']);
        $this->assertCount(3, $dict['members']);
        $this->assertEquals('Literal', $dict['members'][0]->jsonSerialize()['type']);
        $this->assertEquals('a', $dict['members'][0]->jsonSerialize()['value']);
    }
    
    public function testCharacterClassWithRange(): void
    {
        $charClass = new CharacterClass(false, [
            new Range('a', 'z'),
            new Range('0', '9')
        ]);
        
        $dict = $charClass->jsonSerialize();
        $this->assertCount(2, $dict['members']);
        $this->assertEquals('Range', $dict['members'][0]->jsonSerialize()['type']);
        $this->assertEquals('a', $dict['members'][0]->jsonSerialize()['from']);
        $this->assertEquals('z', $dict['members'][0]->jsonSerialize()['to']);
    }
    
    public function testCharacterClassWithEscape(): void
    {
        $charClass = new CharacterClass(false, [
            new Escape('d'),
            new Escape('w')
        ]);
        
        $dict = $charClass->jsonSerialize();
        $this->assertEquals('Escape', $dict['members'][0]->jsonSerialize()['type']);
        $this->assertEquals('d', $dict['members'][0]->jsonSerialize()['kind']);
    }
    
    public function testCharacterClassNegated(): void
    {
        $charClass = new CharacterClass(true, [
            new Literal('a')
        ]);
        
        $dict = $charClass->jsonSerialize();
        $this->assertTrue($dict['negated']);
    }
    
    public function testQuantifierNode(): void
    {
        $quant = new Quantifier(
            new Literal('a'),
            1,
            3,
            true,  // greedy
            false, // lazy
            false  // possessive
        );
        
        $dict = $quant->jsonSerialize();
        $this->assertEquals('Quantifier', $dict['type']);
        $this->assertEquals(1, $dict['min']);
        $this->assertEquals(3, $dict['max']);
        $this->assertTrue($dict['greedy']);
        $this->assertFalse($dict['lazy']);
        $this->assertEquals('Literal', $dict['target']->jsonSerialize()['type']);
    }
    
    public function testQuantifierUnbounded(): void
    {
        $quant = new Quantifier(
            new Literal('a'),
            0,
            'inf',
            false, // greedy
            true,  // lazy
            false  // possessive
        );
        
        $dict = $quant->jsonSerialize();
        $this->assertEquals('inf', $dict['max']);
        $this->assertTrue($dict['lazy']);
    }
    
    public function testGroupCapturing(): void
    {
        $group = new Group(
            true,
            new Literal('test')
        );
        
        $dict = $group->jsonSerialize();
        $this->assertEquals('Group', $dict['type']);
        $this->assertTrue($dict['capturing']);
        $this->assertEquals('Literal', $dict['body']->jsonSerialize()['type']);
    }
    
    public function testGroupNonCapturing(): void
    {
        $group = new Group(
            false,
            new Literal('test')
        );
        
        $dict = $group->jsonSerialize();
        $this->assertFalse($dict['capturing']);
    }
    
    public function testGroupNamed(): void
    {
        $group = new Group(
            true,
            new Literal('test'),
            'mygroup'
        );
        
        $dict = $group->jsonSerialize();
        $this->assertEquals('mygroup', $dict['name']);
    }
    
    public function testBackreferenceByIndex(): void
    {
        $backref = new Backreference(index: 1);
        $dict = $backref->jsonSerialize();
        
        $this->assertEquals('Backreference', $dict['type']);
        $this->assertEquals(1, $dict['index']);
        $this->assertArrayNotHasKey('name', $dict);
    }
    
    public function testBackreferenceByName(): void
    {
        $backref = new Backreference(name: 'mygroup');
        $dict = $backref->jsonSerialize();
        
        $this->assertEquals('mygroup', $dict['name']);
        $this->assertArrayNotHasKey('index', $dict);
    }
    
    public function testLookAhead(): void
    {
        $look = new Lookahead(
            new Literal('test')
        );
        
        $dict = $look->jsonSerialize();
        $this->assertEquals('Lookahead', $dict['type']);
        $this->assertEquals('Literal', $dict['body']->jsonSerialize()['type']);
    }
    
    public function testLookBehindNegative(): void
    {
        $look = new NegativeLookbehind(
            new Literal('test')
        );
        
        $dict = $look->jsonSerialize();
        $this->assertEquals('NegativeLookbehind', $dict['type']);
        $this->assertEquals('Literal', $dict['body']->jsonSerialize()['type']);
    }
}
