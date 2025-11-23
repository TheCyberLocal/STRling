<?php

namespace Tests\Core;

use PHPUnit\Framework\TestCase;
use STRling\Core\IR\Alt;
use STRling\Core\IR\Anchor;
use STRling\Core\IR\BackRef;
use STRling\Core\IR\Char;
use STRling\Core\IR\Dot;
use STRling\Core\IR\Esc;
use STRling\Core\IR\Group;
use STRling\Core\IR\LookAround;
use STRling\Core\IR\Range;
use STRling\Core\IR\Lit;

class IRTest extends TestCase
{
    public function testCharSerialization(): void
    {
        $node = new Char('a');
        $json = json_encode($node);
        $dict = json_decode($json, true);

        $this->assertEquals('Char', $dict['ir']);
        $this->assertEquals('a', $dict['char']);
    }

    public function testLitSerialization(): void
    {
        $node = new Lit('abc');
        $json = json_encode($node);
        $dict = json_decode($json, true);

        $this->assertEquals('Lit', $dict['ir']);
        $this->assertEquals('abc', $dict['value']);
    }

    public function testEscSerialization(): void
    {
        $node = new Esc('d');
        $json = json_encode($node);
        $dict = json_decode($json, true);

        $this->assertEquals('Esc', $dict['ir']);
        $this->assertEquals('d', $dict['type']);
    }

    public function testDotSerialization(): void
    {
        $node = new Dot();
        $json = json_encode($node);
        $dict = json_decode($json, true);

        $this->assertEquals('Dot', $dict['ir']);
    }

    public function testRangeSerialization(): void
    {
        $node = new Range('a', 'z');
        $json = json_encode($node);
        $dict = json_decode($json, true);

        $this->assertEquals('Range', $dict['ir']);
        $this->assertEquals('a', $dict['from']);
        $this->assertEquals('z', $dict['to']);
    }

    public function testAnchorSerialization(): void
    {
        $node = new Anchor('StartLine');
        $json = json_encode($node);
        $dict = json_decode($json, true);

        $this->assertEquals('Anchor', $dict['ir']);
        $this->assertEquals('StartLine', $dict['at']);
    }

    public function testGroupSerialization(): void
    {
        $child = new Lit('abc');
        $node = new Group($child, true, 'name1');
        $json = json_encode($node);
        $dict = json_decode($json, true);

        $this->assertEquals('Group', $dict['ir']);
        $this->assertTrue($dict['capturing']);
        $this->assertEquals('name1', $dict['name']);
        $this->assertEquals('Lit', $dict['body']['ir']);
    }

    public function testAtomicGroupSerialization(): void
    {
        $child = new Lit('abc');
        $node = new Group($child, false, null, null, true);
        $json = json_encode($node);
        $dict = json_decode($json, true);

        $this->assertEquals('Group', $dict['ir']);
        $this->assertFalse($dict['capturing']);
        $this->assertTrue($dict['atomic']);
        $this->assertEquals('Lit', $dict['body']['ir']);
    }

    public function testAltSerialization(): void
    {
        $left = new Char('a');
        $right = new Char('b');
        $node = new Alt([$left, $right]);
        $json = json_encode($node);
        $dict = json_decode($json, true);

        $this->assertEquals('Alt', $dict['ir']);
        $this->assertCount(2, $dict['branches']);
        $this->assertEquals('Char', $dict['branches'][0]['ir']);
    }

    public function testBackRefSerialization(): void
    {
        $node = new BackRef(1, 'name1');
        $json = json_encode($node);
        $dict = json_decode($json, true);

        $this->assertEquals('Backref', $dict['ir']);
        $this->assertEquals(1, $dict['byIndex']);
        $this->assertEquals('name1', $dict['byName']);
    }

    public function testLookAroundSerialization(): void
    {
        $child = new Lit('abc');
        $node = new LookAround('Lookahead', true, $child);
        $json = json_encode($node);
        $dict = json_decode($json, true);

        $this->assertEquals('Look', $dict['ir']);
        $this->assertEquals('Ahead', $dict['dir']);
        $this->assertTrue($dict['neg']);
        $this->assertEquals('Lit', $dict['body']['ir']);
    }
}
