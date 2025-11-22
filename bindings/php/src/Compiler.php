<?php

namespace STRling;

use STRling\Core\Node;
use STRling\Core\IRNode;
use STRling\Core\Nodes;
use STRling\Core\IR;

class Compiler
{
    public function compile(Node $ast): IRNode
    {
        return $this->visit($ast);
    }

    private function visit(Node|Nodes\ClassItem $node): IRNode
    {
        return match (true) {
            $node instanceof Nodes\Literal => $this->visitLiteral($node),
            $node instanceof Nodes\Sequence => $this->visitSequence($node),
            $node instanceof Nodes\Alternation => $this->visitAlternation($node),
            $node instanceof Nodes\Quantifier => $this->visitQuantifier($node),
            $node instanceof Nodes\Group => $this->visitGroup($node),
            $node instanceof Nodes\CharacterClass => $this->visitCharacterClass($node),
            $node instanceof Nodes\Anchor => $this->visitAnchor($node),
            $node instanceof Nodes\Dot => new IR\Esc('Dot'),
            $node instanceof Nodes\Backreference => $this->visitBackreference($node),
            $node instanceof Nodes\Lookahead => new IR\LookAround('Lookahead', false, $this->visit($node->body)),
            $node instanceof Nodes\NegativeLookahead => new IR\LookAround('Lookahead', true, $this->visit($node->body)),
            $node instanceof Nodes\Lookbehind => new IR\LookAround('Lookbehind', false, $this->visit($node->body)),
            $node instanceof Nodes\NegativeLookbehind => new IR\LookAround('Lookbehind', true, $this->visit($node->body)),
            // Class Items
            $node instanceof Nodes\Range => new IR\Range($node->from, $node->to),
            $node instanceof Nodes\Escape => new IR\Esc($node->kind),
            $node instanceof Nodes\UnicodeProperty => new IR\Esc(
                $node->negated ? 'P' : 'p',
                $node->value
            ),
            default => throw new \RuntimeException("Unknown node type: " . get_class($node)),
        };
    }

    private function visitLiteral(Nodes\Literal $node): IR\Lit
    {
        return new IR\Lit($node->value);
    }

    private function visitSequence(Nodes\Sequence $node): IR\Seq|IR\Lit
    {
        $parts = [];
        $buffer = '';

        foreach ($node->parts as $part) {
            if ($part instanceof Nodes\Literal) {
                $buffer .= $part->value;
            } else {
                if ($buffer !== '') {
                    $parts[] = new IR\Lit($buffer);
                    $buffer = '';
                }
                $parts[] = $this->visit($part);
            }
        }

        if ($buffer !== '') {
            $parts[] = new IR\Lit($buffer);
        }

        if (count($parts) === 1 && $parts[0] instanceof IR\Lit) {
            return $parts[0];
        }

        return new IR\Seq($parts);
    }

    private function visitAlternation(Nodes\Alternation $node): IR\Alt
    {
        return new IR\Alt(array_map(fn($n) => $this->visit($n), $node->alternatives));
    }

    private function visitQuantifier(Nodes\Quantifier $node): IR\Quant
    {
        $mode = match (true) {
            $node->possessive => 'Possessive',
            $node->lazy => 'Lazy',
            default => 'Greedy',
        };

        return new IR\Quant(
            $this->visit($node->target),
            $node->min,
            $node->max ?? 'Inf',
            $mode
        );
    }

    private function visitGroup(Nodes\Group $node): IR\Group
    {
        return new IR\Group(
            $this->visit($node->body),
            $node->capturing,
            $node->name,
            $node->number
        );
    }

    private function visitCharacterClass(Nodes\CharacterClass $node): IR\CharClass
    {
        $items = array_map(function ($item) {
            if ($item instanceof Nodes\Literal) {
                // In character classes, literals are treated as Chars
                // But if the literal string has length > 1, it should probably be split?
                // Spec usually has single chars in classes.
                return new IR\Char($item->value);
            }
            return $this->visit($item);
        }, $node->members);

        return new IR\CharClass($node->negated, $items);
    }

    private function visitAnchor(Nodes\Anchor $node): IR\Anchor
    {
        $type = match ($node->at) {
            '^' => 'StartLine',
            '$' => 'EndLine',
            '\\A' => 'StartText',
            '\\z' => 'EndText',
            '\\b' => 'WordBoundary',
            '\\B' => 'NonWordBoundary',
            default => 'Unknown',
        };
        return new IR\Anchor($type);
    }

    private function visitBackreference(Nodes\Backreference $node): IR\BackRef
    {
        return new IR\BackRef($node->index, $node->name);
    }
}
