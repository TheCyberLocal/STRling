<?php

declare(strict_types=1);

namespace STRling\Core;

use STRling\Core\Nodes\{
    Node, Alternation, Sequence, Literal, Dot, Anchor, CharacterClass, Quantifier, Group, Backreference,
    Lookahead, NegativeLookahead, Lookbehind, NegativeLookbehind,
    ClassItem, Escape, Range, Flags
};

/**
 * STRling Parser - Recursive Descent Parser for STRling DSL
 *
 * Transforms STRling pattern syntax into Abstract Syntax Tree (AST) nodes.
 */
class Parser
{
    private Flags $flags;
    private string $src;
    private int $i = 0;
    private int $len;
    private bool $extendedMode = false;
    private int $inClass = 0;
    private int $capCount = 0;
    /** @var array<string> */
    private array $capNames = [];

    private const CONTROL_ESCAPES = [
        'n' => "\n",
        'r' => "\r",
        't' => "\t",
        'f' => "\f",
        'v' => "\v",
    ];

    public function __construct(string $text)
    {
        [$this->flags, $this->src] = $this->parseDirectives($text);
        $this->len = strlen($this->src);
        $this->extendedMode = $this->flags->extended;
    }

    /**
     * @return array{Flags, Node}
     */
    public function parse(): array
    {
        $node = $this->parseAlt();
        $this->skipWsAndComments();

        if (!$this->eof()) {
            $ch = $this->peek();
            if ($ch === ')') {
                throw new STRlingParseError("Unmatched ')'", $this->i, $this->src);
            }
            throw new STRlingParseError("Unexpected trailing input", $this->i, $this->src);
        }

        return [$this->flags, $node];
    }

    /**
     * @return array{Flags, string}
     */
    private function parseDirectives(string $text): array
    {
        $flags = new Flags();
        $lines = explode("\n", $text);
        $patternLines = [];
        $inPattern = false;

        foreach ($lines as $line) {
            $trimmed = trim($line);

            if ($trimmed === '' || str_starts_with($trimmed, '#')) {
                if (!$inPattern) {
                    continue;
                }
                $patternLines[] = $line;
                continue;
            }

            if (str_starts_with($trimmed, '%')) {
                if ($inPattern) {
                    throw new STRlingParseError("Directive after pattern", 0, $text);
                }
                if (preg_match('/^%flags\\s*(.*)/i', $trimmed, $m)) {
                    $flagStr = strtolower(preg_replace('/[,\\[\\]\\s]/', '', $m[1]));
                    $flags = Flags::fromLetters($flagStr, function(string $ch) use ($text) {
                        throw new STRlingParseError("Invalid flag '$ch'", 0, $text);
                    });
                } else {
                    throw new STRlingParseError("Malformed directive", 0, $text);
                }
                continue;
            }

            $inPattern = true;
            // Check if a directive appears mid-line
            if (preg_match("/%flags\\b/", $trimmed) && !str_starts_with($trimmed, "%")) {
                throw new STRlingParseError("Directive after pattern", 0, $text);
            }
            $patternLines[] = $line;
        }

        $text = implode("\n", $patternLines);
        return [$flags, $text];
    }

    private function eof(): bool
    {
        return $this->i >= $this->len;
    }

    private function peek(int $offset = 0): string
    {
        $j = $this->i + $offset;
        return $j < $this->len ? $this->src[$j] : '';
    }

    private function take(): string
    {
        if ($this->eof()) {
            return '';
        }
        return $this->src[$this->i++];
    }

    private function match(string $s): bool
    {
        $slen = strlen($s);
        if ($this->i + $slen > $this->len) {
            return false;
        }
        if (substr($this->src, $this->i, $slen) === $s) {
            $this->i += $slen;
            return true;
        }
        return false;
    }

    private function skipWsAndComments(): void
    {
        if (!$this->extendedMode || $this->inClass > 0) {
            return;
        }
        while (!$this->eof()) {
            $ch = $this->peek();
            if (in_array($ch, [' ', "\t", "\r", "\n"], true)) {
                $this->i++;
                continue;
            }
            if ($ch === '#') {
                while (!$this->eof() && !in_array($this->peek(), ["\r", "\n"], true)) {
                    $this->i++;
                }
                continue;
            }
            break;
        }
    }

    private function parseAlt(): Node
    {
        $this->skipWsAndComments();

        if ($this->peek() === '|') {
            throw new STRlingParseError("Alternation lacks left-hand side", $this->i, $this->src);
        }

        $branches = [$this->parseSeq()];
        $this->skipWsAndComments();

        while ($this->peek() === '|') {
            $pipePos = $this->i;
            $this->take();
            $this->skipWsAndComments();

            if ($this->peek() === '|') {
                throw new STRlingParseError("Empty alternation", $pipePos, $this->src);
            }
            if ($this->eof() || $this->peek() === ')') {
                throw new STRlingParseError("Alternation lacks right-hand side", $pipePos, $this->src);
            }

            $branches[] = $this->parseSeq();
            $this->skipWsAndComments();
        }

        return count($branches) === 1 ? $branches[0] : new Alternation($branches);
    }

    private function parseSeq(): Node
    {
        $parts = [];

        while (true) {
            $this->skipWsAndComments();
            $ch = $this->peek();

            // Check for invalid quantifier at start
            if (in_array($ch, ['*', '+', '?', '{'], true) && count($parts) === 0) {
                throw new STRlingParseError("Invalid quantifier '{$ch}'", $this->i, $this->src);
            }

            if ($ch === '' || $ch === '|' || $ch === ')') {
                break;
            }

            $atom = $this->parseAtom();
            $atom = $this->parseQuantIfAny($atom);
            $parts[] = $atom;
        }

        if (count($parts) === 1) {
            return $parts[0];
        }

        return new Sequence($parts);
    }

    private function parseAtom(): Node
    {
        $this->skipWsAndComments();
        $ch = $this->peek();

        if ($ch === '.') {
            $this->take();
            return new Dot();
        }
        if ($ch === '^') {
            $this->take();
            return new Anchor('Start');
        }
        if ($ch === '$') {
            $this->take();
            return new Anchor('End');
        }
        if ($ch === '(') {
            return $this->parseGroupOrLook();
        }
        if ($ch === '[') {
            return $this->parseCharClass();
        }
        if ($ch === '\\') {
            return $this->parseEscapeAtom();
        }
        if ($ch === ')') {
            throw new STRlingParseError("Unmatched ')'", $this->i, $this->src);
        }

        return new Literal($this->take());
    }

    private function parseQuantIfAny(Node $child): Node
    {
        $ch = $this->peek();
        $min = null;
        $max = null;
        $greedy = true;
        $lazy = false;
        $possessive = false;

        if ($ch === '*') {
            $min = 0;
            $max = null;
            $this->take();
        } elseif ($ch === '+') {
            $min = 1;
            $max = null;
            $this->take();
        } elseif ($ch === '?') {
            $min = 0;
            $max = 1;
            $this->take();
        } elseif ($ch === '{') {
            $save = $this->i;
            $this->take();

            // Look ahead to check for invalid brace quantifier content
            $lookAhead = '';
            $j = $this->i;
            while ($j < $this->len && $this->src[$j] !== '}') {
                $lookAhead .= $this->src[$j];
                $j++;
            }
            if ($j < $this->len && $this->src[$j] === '}' && $lookAhead !== '' && !preg_match('/^\d+(,\d*)?$/', $lookAhead)) {
                throw new STRlingParseError("Brace quantifier: Invalid brace quantifier content", $save, $this->src);
            }

            $m = $this->readIntOptional();
            if ($m === null) {
                $this->i = $save;
                return $child;
            }

            $min = $m;
            $max = $m;

            if ($this->peek() === ',') {
                $this->take();
                $n = $this->readIntOptional();
                $max = $n; // null means infinity
            }

            if ($this->peek() !== '}') {
                throw new STRlingParseError("Incomplete quantifier", $this->i, $this->src);
            }
            $this->take();

            // Validate range
            if ($max !== null && $min > $max) {
                throw new STRlingParseError("Invalid quantifier range", $save, $this->src);
            }
        } else {
            return $child;
        }

        // Check anchor quantification
        if ($child instanceof Anchor) {
            throw new STRlingParseError("Cannot quantify anchor", $this->i, $this->src);
        }

        // Check for lazy/possessive
        $nxt = $this->peek();
        if ($nxt === '?') {
            $greedy = false;
            $lazy = true;
            $this->take();
        } elseif ($nxt === '+') {
            $greedy = false;
            $possessive = true;
            $this->take();
        }

        return new Quantifier($child, $min, $max, $greedy, $lazy, $possessive);
    }

    private function readIntOptional(): ?int
    {
        $s = '';
        while (ctype_digit($this->peek())) {
            $s .= $this->take();
        }
        return $s !== '' ? (int)$s : null;
    }

    private function parseGroupOrLook(): Node
    {
        $this->take(); // consume '('

        // Non-capturing
        if ($this->match('?:')) {
            $body = $this->parseAlt();
            if (!$this->match(')')) {
                throw new STRlingParseError("Unterminated group", $this->i, $this->src);
            }
            return new Group(false, $body);
        }

        // Lookbehind positive
        if ($this->match('?<=')) {
            $body = $this->parseAlt();
            if (!$this->match(')')) {
                throw new STRlingParseError("Unterminated lookbehind", $this->i, $this->src);
            }
            return new Lookbehind($body);
        }

        // Lookbehind negative
        if ($this->match('?<!')) {
            $body = $this->parseAlt();
            if (!$this->match(')')) {
                throw new STRlingParseError("Unterminated lookbehind", $this->i, $this->src);
            }
            return new NegativeLookbehind($body);
        }

        // Inline modifiers
        if ($this->peek() === '?' && preg_match('/^[imsx]+\)/', substr($this->src, $this->i + 1))) {
            throw new STRlingParseError("Inline modifiers are not supported", $this->i - 1, $this->src);
        }

        // Named capturing group
        if ($this->match('?<')) {
            $name = '';
            while ($this->peek() !== '>' && $this->peek() !== '') {
                $name .= $this->take();
            }
            if (!$this->match('>')) {
                throw new STRlingParseError("Unterminated group name", $this->i, $this->src);
            }
            if ($name === '' || !preg_match('/^[a-zA-Z_][a-zA-Z0-9_]*$/', $name)) {
                throw new STRlingParseError("Invalid group name", $this->i, $this->src);
            }
            if (in_array($name, $this->capNames, true)) {
                throw new STRlingParseError("Duplicate group name <{$name}>", $this->i, $this->src);
            }
            $this->capCount++;
            $this->capNames[] = $name;

            $body = $this->parseAlt();
            if (!$this->match(')')) {
                throw new STRlingParseError("Unterminated group", $this->i, $this->src);
            }
            return new Group(true, $body, $name);
        }

        // Atomic group
        if ($this->match('?>')) {
            $body = $this->parseAlt();
            if (!$this->match(')')) {
                throw new STRlingParseError("Unterminated atomic group", $this->i, $this->src);
            }
            return new Group(false, $body, null, true);
        }

        // Lookahead positive
        if ($this->match('?=')) {
            $body = $this->parseAlt();
            if (!$this->match(')')) {
                throw new STRlingParseError("Unterminated lookahead", $this->i, $this->src);
            }
            return new Lookahead($body);
        }

        // Lookahead negative
        if ($this->match('?!')) {
            $body = $this->parseAlt();
            if (!$this->match(')')) {
                throw new STRlingParseError("Unterminated lookahead", $this->i, $this->src);
            }
            return new NegativeLookahead($body);
        }

        // Regular capturing group
        $this->capCount++;
        $body = $this->parseAlt();
        if (!$this->match(')')) {
            throw new STRlingParseError("Unterminated group", $this->i, $this->src);
        }
        return new Group(true, $body);
    }

    private function parseCharClass(): Node
    {
        $this->take(); // consume '['
        $this->inClass++;

        $neg = false;
        if ($this->peek() === '^') {
            $neg = true;
            $this->take();
        }

        if ($this->peek() === ']') {
            throw new STRlingParseError("Unterminated character class", $this->i, $this->src);
        }

        $items = [];

        while (!$this->eof() && $this->peek() !== ']') {
            if ($this->peek() === '\\') {
                $items[] = $this->parseClassEscape();
            } else {
                $ch = $this->take();

                // Check for range
                if ($this->peek() === '-' && $this->peek(1) !== ']') {
                    $this->take(); // consume '-'
                    $endCh = $this->take();
                    if (ord($endCh) < ord($ch)) {
                        throw new STRlingParseError("Invalid character range", $this->i, $this->src);
                    }
                    $items[] = new Range($ch, $endCh);
                } else {
                    $items[] = new Literal($ch);
                }
            }
        }

        if ($this->eof()) {
            throw new STRlingParseError("Unterminated character class", $this->i, $this->src);
        }

        $this->take(); // consume ']'
        $this->inClass--;

        return new CharacterClass($neg, $items);
    }

    private function parseClassEscape(): ClassItem
    {
        $startPos = $this->i;
        $this->take(); // consume '\'

        $nxt = $this->peek();

        // Shorthand classes
        if (in_array($nxt, ['d', 'D', 'w', 'W', 's', 'S'], true)) {
            $kind = match($this->take()) {
                'd' => 'digit',
                'D' => 'not-digit',
                'w' => 'word',
                'W' => 'not-word',
                's' => 'space',
                'S' => 'not-space',
            };
            return new Escape($kind);
        }

        // Unicode property
        if ($nxt === 'p' || $nxt === 'P') {
            $tp = $this->take();
            if (!$this->match('{')) {
                throw new STRlingParseError("Expected { after \\p/\\P", $startPos, $this->src);
            }
            $prop = '';
            while ($this->peek() !== '}' && $this->peek() !== '') {
                $prop .= $this->take();
            }
            if (!$this->match('}')) {
                throw new STRlingParseError("Unterminated \\p{...}", $startPos, $this->src);
            }
            return new Escape($tp === 'P' ? 'not-property' : 'property');
        }

        // Control escapes
        if (isset(self::CONTROL_ESCAPES[$nxt])) {
            $this->take();
            return new Literal(self::CONTROL_ESCAPES[$nxt]);
        }

        // Backspace in class
        if ($nxt === 'b') {
            $this->take();
            return new Literal("\x08");
        }

        // Null
        if ($nxt === '0') {
            $this->take();
            return new Literal("\x00");
        }

        // Unknown escape for alphanumeric
        if (ctype_alnum($nxt)) {
            throw new STRlingParseError("Unknown escape sequence \\{$nxt}", $startPos, $this->src);
        }

        // Identity escape (punctuation)
        return new Literal($this->take());
    }

    private function parseEscapeAtom(): Node
    {
        $startPos = $this->i;
        $this->take(); // consume '\'

        $nxt = $this->peek();

        // Backreference by index
        if (ctype_digit($nxt) && $nxt !== '0') {
            $num = 0;
            while (ctype_digit($this->peek())) {
                $num = $num * 10 + (int)$this->take();
                if ($num > $this->capCount) {
                    throw new STRlingParseError("Backreference to undefined group \\{$num}", $startPos, $this->src);
                }
            }
            return new Backreference($num, null);
        }

        // Anchors
        if ($nxt === 'b') { $this->take(); return new Anchor('WordBoundary'); }
        if ($nxt === 'B') { $this->take(); return new Anchor('NotWordBoundary'); }
        if ($nxt === 'A') { $this->take(); return new Anchor('AbsoluteStart'); }
        if ($nxt === 'Z') { $this->take(); return new Anchor('EndBeforeFinalNewline'); }

        // Named backref
        if ($nxt === 'k') {
            $this->take();
            if (!$this->match('<')) {
                throw new STRlingParseError("Expected '<' after \\k", $startPos, $this->src);
            }
            $name = '';
            while ($this->peek() !== '>' && $this->peek() !== '') {
                $name .= $this->take();
            }
            if (!$this->match('>')) {
                throw new STRlingParseError("Unterminated named backref", $startPos, $this->src);
            }
            if (!in_array($name, $this->capNames, true)) {
                throw new STRlingParseError("Backreference to undefined group <{$name}>", $startPos, $this->src);
            }
            return new Backreference(null, $name);
        }

        // Shorthand classes
        if (in_array($nxt, ['d', 'D', 'w', 'W', 's', 'S'], true)) {
            $kind = match($this->take()) {
                'd' => 'digit',
                'D' => 'not-digit',
                'w' => 'word',
                'W' => 'not-word',
                's' => 'space',
                'S' => 'not-space',
            };
            return new CharacterClass(false, [new Escape($kind)]);
        }

        // Unicode property
        if ($nxt === 'p' || $nxt === 'P') {
            $tp = $this->take();
            if (!$this->match('{')) {
                throw new STRlingParseError("Expected { after \\p/\\P", $startPos, $this->src);
            }
            $prop = '';
            while ($this->peek() !== '}' && $this->peek() !== '') {
                $prop .= $this->take();
            }
            if (!$this->match('}')) {
                throw new STRlingParseError("Unterminated \\p{...}", $startPos, $this->src);
            }
            return new CharacterClass(false, [new Escape($tp === 'P' ? 'not-property' : 'property')]);
        }

        // Control escapes
        if (isset(self::CONTROL_ESCAPES[$nxt])) {
            $this->take();
            return new Literal(self::CONTROL_ESCAPES[$nxt]);
        }

        // Hex escape
        if ($nxt === 'x') {
            $this->take();
            return new Literal($this->parseHexEscape($startPos));
        }

        // Unicode escape
        if ($nxt === 'u' || $nxt === 'U') {
            return new Literal($this->parseUnicodeEscape($startPos));
        }

        // Null
        if ($nxt === '0') {
            $this->take();
            return new Literal("\x00");
        }

        // Unknown escape for alphanumeric
        if (ctype_alnum($nxt)) {
            throw new STRlingParseError("Unknown escape sequence \\{$nxt}", $startPos, $this->src);
        }

        // Identity escape (punctuation)
        return new Literal($this->take());
    }

    private function parseHexEscape(int $startPos): string
    {
        if ($this->match('{')) {
            $hex = '';
            while (ctype_xdigit($this->peek())) {
                $hex .= $this->take();
            }
            if (!$this->match('}')) {
                throw new STRlingParseError("Unterminated \\x{...}", $startPos, $this->src);
            }
            $cp = hexdec($hex ?: '0');
            return mb_chr((int)$cp, 'UTF-8');
        }

        $h1 = $this->take();
        $h2 = $this->take();
        if (!ctype_xdigit($h1) || !ctype_xdigit($h2)) {
            throw new STRlingParseError("Invalid \\xHH escape", $startPos, $this->src);
        }
        return chr((int)hexdec($h1 . $h2));
    }

    private function parseUnicodeEscape(int $startPos): string
    {
        $tp = $this->take();

        if ($tp === 'u' && $this->match('{')) {
            $hex = '';
            while (ctype_xdigit($this->peek())) {
                $hex .= $this->take();
            }
            if (!$this->match('}')) {
                throw new STRlingParseError("Unterminated \\u{...}", $startPos, $this->src);
            }
            $cp = hexdec($hex ?: '0');
            return mb_chr((int)$cp, 'UTF-8');
        }

        if ($tp === 'u') {
            $hex = '';
            for ($i = 0; $i < 4; $i++) {
                $hex .= $this->take();
            }
            if (!preg_match('/^[0-9A-Fa-f]{4}$/', $hex)) {
                throw new STRlingParseError("Invalid \\uHHHH escape", $startPos, $this->src);
            }
            return mb_chr((int)hexdec($hex), 'UTF-8');
        }

        if ($tp === 'U') {
            $hex = '';
            for ($i = 0; $i < 8; $i++) {
                $hex .= $this->take();
            }
            if (!preg_match('/^[0-9A-Fa-f]{8}$/', $hex)) {
                throw new STRlingParseError("Invalid \\UHHHHHHHH escape", $startPos, $this->src);
            }
            return mb_chr((int)hexdec($hex), 'UTF-8');
        }

        throw new STRlingParseError("Invalid unicode escape", $startPos, $this->src);
    }
}
