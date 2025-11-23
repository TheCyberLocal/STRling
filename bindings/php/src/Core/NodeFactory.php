<?php

namespace STRling\Core;

use STRling\Core\Nodes\Node;
use STRling\Core\Nodes\ClassItem;
use STRling\Core\Nodes\Alternation;
use STRling\Core\Nodes\Sequence;
use STRling\Core\Nodes\Literal;
use STRling\Core\Nodes\Dot;
use STRling\Core\Nodes\Anchor;
use STRling\Core\Nodes\CharacterClass;
use STRling\Core\Nodes\Range;
use STRling\Core\Nodes\Escape;
use STRling\Core\Nodes\UnicodeProperty;
use STRling\Core\Nodes\Quantifier;
use STRling\Core\Nodes\Group;
use STRling\Core\Nodes\Backreference;
use STRling\Core\Nodes\Lookahead;
use STRling\Core\Nodes\NegativeLookahead;
use STRling\Core\Nodes\Lookbehind;
use STRling\Core\Nodes\NegativeLookbehind;

class NodeFactory
{
    public static function fromArray(array $data): Node|ClassItem
    {
        return match ($data['type']) {
            'Alternation' => new Alternation(
                array_map(fn($a) => self::fromArray($a), $data['alternatives'])
            ),
            'Sequence' => new Sequence(
                array_map(fn($p) => self::fromArray($p), $data['parts'])
            ),
            'Literal' => new Literal($data['value']),
            'Dot' => new Dot(),
            'Anchor' => new Anchor($data['at']),
            'CharacterClass' => new CharacterClass(
                $data['negated'],
                array_map(fn($m) => self::fromArray($m), $data['members'])
            ),
            'Range' => new Range($data['from'], $data['to']),
            'Escape' => new Escape($data['kind']),
            'UnicodeProperty' => new UnicodeProperty(
                $data['value'],
                $data['name'] ?? null,
                $data['negated'] ?? false
            ),
            'Quantifier' => new Quantifier(
                self::fromArray($data['target']),
                $data['min'],
                $data['max'] ?? null,
                $data['greedy'],
                $data['lazy'],
                $data['possessive']
            ),
            'Group' => new Group(
                $data['capturing'],
                self::fromArray($data['body']),
                $data['name'] ?? null,
                $data['atomic'] ?? null,
                $data['number'] ?? null,
                isset($data['expression']) ? self::fromArray($data['expression']) : null
            ),
            'Backreference' => new Backreference(
                $data['index'] ?? null,
                $data['name'] ?? null
            ),
            'Lookahead' => new Lookahead(self::fromArray($data['body'])),
            'NegativeLookahead' => new NegativeLookahead(self::fromArray($data['body'])),
            'Lookbehind' => new Lookbehind(self::fromArray($data['body'])),
            'NegativeLookbehind' => new NegativeLookbehind(self::fromArray($data['body'])),
            default => throw new \InvalidArgumentException("Unknown node type: {$data['type']}"),
        };
    }
}
