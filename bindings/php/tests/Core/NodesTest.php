<?php

namespace STRling\Tests\Core;

use PHPUnit\Framework\TestCase;
use STRling\Core\Flags;
use STRling\Core\Lit;
use STRling\Core\Dot;
use STRling\Core\Anchor;
use STRling\Core\Alt;
use STRling\Core\Seq;
use STRling\Core\CharClass;
use STRling\Core\ClassLiteral;
use STRling\Core\ClassRange;
use STRling\Core\ClassEscape;
use STRling\Core\Quant;
use STRling\Core\Group;
use STRling\Core\Backref;
use STRling\Core\Look;

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
    
    public function testFlagsToDict(): void
    {
        $flags = Flags::fromLetters('i');
        $dict = $flags->toDict();
        
        $this->assertArrayHasKey('ignoreCase', $dict);
        $this->assertTrue($dict['ignoreCase']);
        $this->assertFalse($dict['multiline']);
    }
    
    public function testLitNode(): void
    {
        $lit = new Lit('hello');
        $dict = $lit->toDict();
        
        $this->assertEquals('Lit', $dict['kind']);
        $this->assertEquals('hello', $dict['value']);
    }
    
    public function testDotNode(): void
    {
        $dot = new Dot();
        $dict = $dot->toDict();
        
        $this->assertEquals('Dot', $dict['kind']);
    }
    
    public function testAnchorNode(): void
    {
        $anchor = new Anchor('Start');
        $dict = $anchor->toDict();
        
        $this->assertEquals('Anchor', $dict['kind']);
        $this->assertEquals('Start', $dict['at']);
    }
    
    public function testAltNode(): void
    {
        $alt = new Alt([
            new Lit('a'),
            new Lit('b'),
            new Lit('c')
        ]);
        
        $dict = $alt->toDict();
        $this->assertEquals('Alt', $dict['kind']);
        $this->assertCount(3, $dict['branches']);
        $this->assertEquals('Lit', $dict['branches'][0]['kind']);
        $this->assertEquals('a', $dict['branches'][0]['value']);
    }
    
    public function testSeqNode(): void
    {
        $seq = new Seq([
            new Lit('hello'),
            new Lit(' '),
            new Lit('world')
        ]);
        
        $dict = $seq->toDict();
        $this->assertEquals('Seq', $dict['kind']);
        $this->assertCount(3, $dict['parts']);
    }
    
    public function testCharClassWithLiterals(): void
    {
        $charClass = new CharClass(false, [
            new ClassLiteral('a'),
            new ClassLiteral('b'),
            new ClassLiteral('c')
        ]);
        
        $dict = $charClass->toDict();
        $this->assertEquals('CharClass', $dict['kind']);
        $this->assertFalse($dict['negated']);
        $this->assertCount(3, $dict['items']);
        $this->assertEquals('Char', $dict['items'][0]['kind']);
        $this->assertEquals('a', $dict['items'][0]['char']);
    }
    
    public function testCharClassWithRange(): void
    {
        $charClass = new CharClass(false, [
            new ClassRange('a', 'z'),
            new ClassRange('0', '9')
        ]);
        
        $dict = $charClass->toDict();
        $this->assertCount(2, $dict['items']);
        $this->assertEquals('Range', $dict['items'][0]['kind']);
        $this->assertEquals('a', $dict['items'][0]['from']);
        $this->assertEquals('z', $dict['items'][0]['to']);
    }
    
    public function testCharClassWithEscape(): void
    {
        $charClass = new CharClass(false, [
            new ClassEscape('d'),
            new ClassEscape('w')
        ]);
        
        $dict = $charClass->toDict();
        $this->assertEquals('Esc', $dict['items'][0]['kind']);
        $this->assertEquals('d', $dict['items'][0]['type']);
    }
    
    public function testCharClassNegated(): void
    {
        $charClass = new CharClass(true, [
            new ClassLiteral('a')
        ]);
        
        $dict = $charClass->toDict();
        $this->assertTrue($dict['negated']);
    }
    
    public function testQuantNode(): void
    {
        $quant = new Quant(
            new Lit('a'),
            1,
            3,
            'Greedy'
        );
        
        $dict = $quant->toDict();
        $this->assertEquals('Quant', $dict['kind']);
        $this->assertEquals(1, $dict['min']);
        $this->assertEquals(3, $dict['max']);
        $this->assertEquals('Greedy', $dict['mode']);
        $this->assertEquals('Lit', $dict['child']['kind']);
    }
    
    public function testQuantUnbounded(): void
    {
        $quant = new Quant(
            new Lit('a'),
            0,
            'Inf',
            'Lazy'
        );
        
        $dict = $quant->toDict();
        $this->assertEquals('Inf', $dict['max']);
        $this->assertEquals('Lazy', $dict['mode']);
    }
    
    public function testGroupCapturing(): void
    {
        $group = new Group(
            true,
            new Lit('test')
        );
        
        $dict = $group->toDict();
        $this->assertEquals('Group', $dict['kind']);
        $this->assertTrue($dict['capturing']);
        $this->assertEquals('Lit', $dict['body']['kind']);
    }
    
    public function testGroupNonCapturing(): void
    {
        $group = new Group(
            false,
            new Lit('test')
        );
        
        $dict = $group->toDict();
        $this->assertFalse($dict['capturing']);
    }
    
    public function testGroupNamed(): void
    {
        $group = new Group(
            true,
            new Lit('test'),
            'mygroup'
        );
        
        $dict = $group->toDict();
        $this->assertEquals('mygroup', $dict['name']);
    }
    
    public function testBackrefByIndex(): void
    {
        $backref = new Backref(byIndex: 1);
        $dict = $backref->toDict();
        
        $this->assertEquals('Backref', $dict['kind']);
        $this->assertEquals(1, $dict['byIndex']);
        $this->assertArrayNotHasKey('byName', $dict);
    }
    
    public function testBackrefByName(): void
    {
        $backref = new Backref(byName: 'mygroup');
        $dict = $backref->toDict();
        
        $this->assertEquals('mygroup', $dict['byName']);
        $this->assertArrayNotHasKey('byIndex', $dict);
    }
    
    public function testLookAhead(): void
    {
        $look = new Look(
            'Ahead',
            false,
            new Lit('test')
        );
        
        $dict = $look->toDict();
        $this->assertEquals('Look', $dict['kind']);
        $this->assertEquals('Ahead', $dict['dir']);
        $this->assertFalse($dict['neg']);
    }
    
    public function testLookBehindNegative(): void
    {
        $look = new Look(
            'Behind',
            true,
            new Lit('test')
        );
        
        $dict = $look->toDict();
        $this->assertEquals('Behind', $dict['dir']);
        $this->assertTrue($dict['neg']);
    }
}
