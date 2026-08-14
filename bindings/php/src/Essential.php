<?php

declare(strict_types=1);

namespace STRling;

require_once __DIR__ . '/Core/Nodes/Node.php';
require_once __DIR__ . '/Simply.php';

use STRling\Core\Nodes;

/**
 * STRling Essential — compatibility lexical-shape patterns for common string
 * formats. They do not establish semantic validity or standards conformance.
 *
 * Each helper composes the existing Pattern AST so the compiled output
 * flows through the standard pipeline and no raw regex leaks into the
 * public API.
 */
final class Essential
{
    private static function letterItems(): array
    {
        return [
            new Nodes\Range(from: 'A', to: 'Z'),
            new Nodes\Range(from: 'a', to: 'z'),
        ];
    }

    private static function digitItems(): array
    {
        return [new Nodes\Escape('digit')];
    }

    private static function hexItems(): array
    {
        return [
            new Nodes\Range(from: 'A', to: 'F'),
            new Nodes\Range(from: 'a', to: 'f'),
            new Nodes\Range(from: '0', to: '9'),
        ];
    }

    private static function charsItems(string $s): array
    {
        $out = [];
        for ($i = 0; $i < strlen($s); $i++) {
            $out[] = new Nodes\Literal($s[$i]);
        }
        return $out;
    }

    private static function classOf(array $items, int $min, ?int $max): Pattern
    {
        $cc = new Nodes\CharacterClass(negated: false, members: $items);
        if ($min === 1 && $max === 1) {
            return new Pattern($cc);
        }
        $q = new Nodes\Quantifier(
            target: $cc,
            min: $min,
            max: $max,
            greedy: true,
            lazy: false,
            possessive: false
        );
        return new Pattern($q);
    }

    private static function digN(int $min, ?int $max): Pattern
    {
        return self::classOf(self::digitItems(), $min, $max);
    }

    private static function hexN(int $min, ?int $max): Pattern
    {
        return self::classOf(self::hexItems(), $min, $max);
    }

    private static function lettersN(int $min, ?int $max): Pattern
    {
        return self::classOf(self::letterItems(), $min, $max);
    }

    private static function lit(string $s): Pattern
    {
        return new Pattern(new Nodes\Literal($s));
    }

    private static function opt(Pattern $body): Pattern
    {
        $grouped = new Nodes\Group(capturing: false, body: $body->getNode());
        $q = new Nodes\Quantifier(
            target: $grouped,
            min: 0,
            max: 1,
            greedy: true,
            lazy: false,
            possessive: false
        );
        return new Pattern($q);
    }

    private static function altOf(array $branches): Pattern
    {
        $nodes = array_map(fn(Pattern $p) => $p->getNode(), $branches);
        return new Pattern(new Nodes\Alternation(alternatives: $nodes));
    }

    private static function seqOf(array $parts): Pattern
    {
        return Simply::merge(...$parts);
    }

    /**
     * Matches the legacy email-like lexical shape; RFC 5322 conformance is not claimed.
     */
    public static function email(): Pattern
    {
        $local  = self::classOf([...self::letterItems(), ...self::digitItems(), ...self::charsItems('._%+-')], 1, null);
        $domain = self::classOf([...self::letterItems(), ...self::digitItems(), ...self::charsItems('.-')], 1, null);
        $tld    = self::lettersN(2, null);
        return self::seqOf([$local, self::lit('@'), $domain, self::lit('.'), $tld]);
    }

    /**
     * Matches the legacy HTTP(S) URL-like lexical shape; RFC 3986 conformance is not claimed.
     */
    public static function url(): Pattern
    {
        $base     = [...self::letterItems(), ...self::digitItems(), ...self::charsItems("/_-.~%&=:@!$'()*+,;")];
        $withQ    = [...$base, ...self::charsItems('?')];
        $withFrag = [...$withQ, ...self::charsItems('#')];

        $scheme   = self::seqOf([self::lit('http'), self::opt(self::lit('s'))]);
        $host     = self::classOf([...self::letterItems(), ...self::digitItems(), ...self::charsItems('.-')], 1, null);
        $port     = self::opt(self::seqOf([self::lit(':'), self::digN(1, null)]));
        $path     = self::opt(self::seqOf([self::lit('/'), self::classOf($base, 0, null)]));
        $query    = self::opt(self::seqOf([self::lit('?'), self::classOf($withQ, 0, null)]));
        $fragment = self::opt(self::seqOf([self::lit('#'), self::classOf($withFrag, 0, null)]));
        return self::seqOf([$scheme, self::lit('://'), $host, $port, $path, $query, $fragment]);
    }

    /**
     * Matches the RFC 9562 UUID text shape; version=4 constrains version/variant nibbles.
     */
    public static function uuid(int $version = 0): Pattern
    {
        $dash = fn() => self::lit('-');
        if ($version === 4) {
            $variant = self::classOf(self::charsItems('89ABab'), 1, 1);
            return self::seqOf([
                self::hexN(8, 8),  $dash(),
                self::hexN(4, 4),  $dash(),
                self::lit('4'), self::hexN(3, 3), $dash(),
                $variant, self::hexN(3, 3), $dash(),
                self::hexN(12, 12),
            ]);
        }
        return self::seqOf([
            self::hexN(8, 8),  $dash(),
            self::hexN(4, 4),  $dash(),
            self::hexN(4, 4),  $dash(),
            self::hexN(4, 4),  $dash(),
            self::hexN(12, 12),
        ]);
    }

    /**
     * Matches an IPv4-like or full-form IPv6 lexical shape; address validity is not claimed.
     */
    public static function ip(int $version = 0): Pattern
    {
        $ipv4 = fn() => self::seqOf([
            self::digN(1, 3), self::lit('.'),
            self::digN(1, 3), self::lit('.'),
            self::digN(1, 3), self::lit('.'),
            self::digN(1, 3),
        ]);
        $ipv6 = fn() => self::seqOf([
            self::hexN(1, 4), self::lit(':'),
            self::hexN(1, 4), self::lit(':'),
            self::hexN(1, 4), self::lit(':'),
            self::hexN(1, 4), self::lit(':'),
            self::hexN(1, 4), self::lit(':'),
            self::hexN(1, 4), self::lit(':'),
            self::hexN(1, 4), self::lit(':'),
            self::hexN(1, 4),
        ]);
        return match ($version) {
            4 => $ipv4(),
            6 => $ipv6(),
            default => self::altOf([$ipv4(), $ipv6()]),
        };
    }

    /**
     * Matches a timestamp-like lexical shape; RFC 3339 / ISO 8601 validity is not claimed.
     */
    public static function dateTime(): Pattern
    {
        $sign   = self::classOf(self::charsItems('+-'), 1, 1);
        $frac   = self::seqOf([self::lit('.'), self::digN(1, null)]);
        $offset = self::seqOf([$sign, self::digN(2, 2), self::lit(':'), self::digN(2, 2)]);
        return self::seqOf([
            self::digN(4, 4), self::lit('-'), self::digN(2, 2), self::lit('-'), self::digN(2, 2),
            self::lit('T'),
            self::digN(2, 2), self::lit(':'), self::digN(2, 2), self::lit(':'), self::digN(2, 2),
            self::opt($frac),
            self::opt(self::altOf([self::lit('Z'), $offset])),
        ]);
    }
}
