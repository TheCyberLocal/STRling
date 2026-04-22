<?php

declare(strict_types=1);

namespace STRling\Tests;

use PHPUnit\Framework\TestCase;
use STRling\Essential;
use STRling\Emitters\Pcre2Emitter;

class Essential5Test extends TestCase
{
    private static array $spec;

    public static function setUpBeforeClass(): void
    {
        $dir = __DIR__;
        for ($i = 0; $i < 10; $i++) {
            $candidate = $dir . '/spec/stdlib/essential_5.json';
            if (file_exists($candidate)) {
                self::$spec = json_decode(file_get_contents($candidate), true);
                return;
            }
            $dir = dirname($dir);
        }
        throw new \RuntimeException('essential_5.json not found');
    }

    private function compile(\STRling\Pattern $pat): string
    {
        return chr(1) . '^(?:' . Pcre2Emitter::emit($pat->getNode()) . ')$' . chr(1);
    }

    private function fixtures(string $pattern, string $key): array
    {
        return self::$spec['patterns'][$pattern]['fixtures'][$key];
    }

    private function assertAllMatch(string $regex, array $samples): void
    {
        foreach ($samples as $s) {
            $this->assertSame(1, preg_match($regex, $s), "Expected match: $s with $regex");
        }
    }

    private function assertNoneMatch(string $regex, array $samples): void
    {
        foreach ($samples as $s) {
            $this->assertSame(0, preg_match($regex, $s), "Unexpected match: $s with $regex");
        }
    }

    public function testEmailValid(): void   { $this->assertAllMatch($this->compile(Essential::email()), $this->fixtures('email', 'valid')); }
    public function testEmailInvalid(): void { $this->assertNoneMatch($this->compile(Essential::email()), $this->fixtures('email', 'invalid')); }

    public function testUrlValid(): void   { $this->assertAllMatch($this->compile(Essential::url()), $this->fixtures('url', 'valid')); }
    public function testUrlInvalid(): void { $this->assertNoneMatch($this->compile(Essential::url()), $this->fixtures('url', 'invalid')); }

    public function testUuidDefaultValid(): void   { $this->assertAllMatch($this->compile(Essential::uuid()), $this->fixtures('uuid', 'valid_default')); }
    public function testUuidDefaultInvalid(): void { $this->assertNoneMatch($this->compile(Essential::uuid()), $this->fixtures('uuid', 'invalid_default')); }
    public function testUuidV4Valid(): void   { $this->assertAllMatch($this->compile(Essential::uuid(4)), $this->fixtures('uuid', 'valid_v4')); }
    public function testUuidV4Invalid(): void { $this->assertNoneMatch($this->compile(Essential::uuid(4)), $this->fixtures('uuid', 'invalid_v4')); }

    public function testIpV4Valid(): void   { $this->assertAllMatch($this->compile(Essential::ip(4)), $this->fixtures('ip', 'valid_v4')); }
    public function testIpV4Invalid(): void { $this->assertNoneMatch($this->compile(Essential::ip(4)), $this->fixtures('ip', 'invalid_v4')); }
    public function testIpV6Valid(): void   { $this->assertAllMatch($this->compile(Essential::ip(6)), $this->fixtures('ip', 'valid_v6')); }
    public function testIpV6Invalid(): void { $this->assertNoneMatch($this->compile(Essential::ip(6)), $this->fixtures('ip', 'invalid_v6')); }

    public function testIpAnyValid(): void {
        $r = $this->compile(Essential::ip());
        $this->assertAllMatch($r, $this->fixtures('ip', 'valid_v4'));
        $this->assertAllMatch($r, $this->fixtures('ip', 'valid_v6'));
    }

    public function testDateTimeValid(): void   { $this->assertAllMatch($this->compile(Essential::dateTime()), $this->fixtures('dateTime', 'valid')); }
    public function testDateTimeInvalid(): void { $this->assertNoneMatch($this->compile(Essential::dateTime()), $this->fixtures('dateTime', 'invalid')); }
}
