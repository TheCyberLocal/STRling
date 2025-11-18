<?php

namespace STRling\Tests\Core;

use PHPUnit\Framework\TestCase;
use STRling\Core\IRAlt;
use STRling\Core\IRSeq;
use STRling\Core\IRLit;
use STRling\Core\IRDot;
use STRling\Core\IRAnchor;
use STRling\Core\IRCharClass;
use STRling\Core\IRClassLiteral;
use STRling\Core\IRClassRange;
use STRling\Core\IRClassEscape;
use STRling\Core\IRQuant;
use STRling\Core\IRGroup;
use STRling\Core\IRBackref;
use STRling\Core\IRLook;

/**
 * Test suite for IR Node data structures.
 * 
 * @package STRling\Tests\Core
 */
class IRTest extends TestCase
{
    public function testIRLitNode(): void
    {
        $lit = new IRLit('hello');
        $dict = $lit->toDict();
        
        $this->assertEquals('Lit', $dict['ir']);
        $this->assertEquals('hello', $dict['value']);
    }
    
    public function testIRDotNode(): void
    {
        $dot = new IRDot();
        $dict = $dot->toDict();
        
        $this->assertEquals('Dot', $dict['ir']);
    }
    
    public function testIRAnchorNode(): void
    {
        $anchor = new IRAnchor('Start');
        $dict = $anchor->toDict();
        
        $this->assertEquals('Anchor', $dict['ir']);
        $this->assertEquals('Start', $dict['at']);
    }
    
    public function testIRAltNode(): void
    {
        $alt = new IRAlt([
            new IRLit('a'),
            new IRLit('b')
        ]);
        
        $dict = $alt->toDict();
        $this->assertEquals('Alt', $dict['ir']);
        $this->assertCount(2, $dict['branches']);
        $this->assertEquals('Lit', $dict['branches'][0]['ir']);
    }
    
    public function testIRSeqNode(): void
    {
        $seq = new IRSeq([
            new IRLit('hello'),
            new IRLit(' '),
            new IRLit('world')
        ]);
        
        $dict = $seq->toDict();
        $this->assertEquals('Seq', $dict['ir']);
        $this->assertCount(3, $dict['parts']);
    }
    
    public function testIRCharClassWithLiterals(): void
    {
        $charClass = new IRCharClass(false, [
            new IRClassLiteral('a'),
            new IRClassLiteral('b')
        ]);
        
        $dict = $charClass->toDict();
        $this->assertEquals('CharClass', $dict['ir']);
        $this->assertFalse($dict['negated']);
        $this->assertCount(2, $dict['items']);
        $this->assertEquals('Char', $dict['items'][0]['ir']);
        $this->assertEquals('a', $dict['items'][0]['char']);
    }
    
    public function testIRCharClassWithRange(): void
    {
        $charClass = new IRCharClass(false, [
            new IRClassRange('a', 'z')
        ]);
        
        $dict = $charClass->toDict();
        $this->assertEquals('Range', $dict['items'][0]['ir']);
        $this->assertEquals('a', $dict['items'][0]['from']);
        $this->assertEquals('z', $dict['items'][0]['to']);
    }
    
    public function testIRCharClassWithEscape(): void
    {
        $charClass = new IRCharClass(false, [
            new IRClassEscape('d')
        ]);
        
        $dict = $charClass->toDict();
        $this->assertEquals('Esc', $dict['items'][0]['ir']);
        $this->assertEquals('d', $dict['items'][0]['type']);
    }
    
    public function testIRCharClassNegated(): void
    {
        $charClass = new IRCharClass(true, [
            new IRClassLiteral('a')
        ]);
        
        $dict = $charClass->toDict();
        $this->assertTrue($dict['negated']);
    }
    
    public function testIRQuantNode(): void
    {
        $quant = new IRQuant(
            new IRLit('a'),
            1,
            5,
            'Greedy'
        );
        
        $dict = $quant->toDict();
        $this->assertEquals('Quant', $dict['ir']);
        $this->assertEquals(1, $dict['min']);
        $this->assertEquals(5, $dict['max']);
        $this->assertEquals('Greedy', $dict['mode']);
    }
    
    public function testIRQuantUnbounded(): void
    {
        $quant = new IRQuant(
            new IRLit('a'),
            0,
            'Inf',
            'Lazy'
        );
        
        $dict = $quant->toDict();
        $this->assertEquals('Inf', $dict['max']);
        $this->assertEquals('Lazy', $dict['mode']);
    }
    
    public function testIRGroupCapturing(): void
    {
        $group = new IRGroup(
            true,
            new IRLit('test')
        );
        
        $dict = $group->toDict();
        $this->assertEquals('Group', $dict['ir']);
        $this->assertTrue($dict['capturing']);
    }
    
    public function testIRGroupNamed(): void
    {
        $group = new IRGroup(
            true,
            new IRLit('test'),
            'mygroup'
        );
        
        $dict = $group->toDict();
        $this->assertEquals('mygroup', $dict['name']);
    }
    
    public function testIRBackrefByIndex(): void
    {
        $backref = new IRBackref(byIndex: 1);
        $dict = $backref->toDict();
        
        $this->assertEquals('Backref', $dict['ir']);
        $this->assertEquals(1, $dict['byIndex']);
    }
    
    public function testIRBackrefByName(): void
    {
        $backref = new IRBackref(byName: 'mygroup');
        $dict = $backref->toDict();
        
        $this->assertEquals('mygroup', $dict['byName']);
    }
    
    public function testIRLookAhead(): void
    {
        $look = new IRLook(
            'Ahead',
            false,
            new IRLit('test')
        );
        
        $dict = $look->toDict();
        $this->assertEquals('Look', $dict['ir']);
        $this->assertEquals('Ahead', $dict['dir']);
        $this->assertFalse($dict['neg']);
    }
    
    public function testIRLookBehindNegative(): void
    {
        $look = new IRLook(
            'Behind',
            true,
            new IRLit('test')
        );
        
        $dict = $look->toDict();
        $this->assertEquals('Behind', $dict['dir']);
        $this->assertTrue($dict['neg']);
    }
}
