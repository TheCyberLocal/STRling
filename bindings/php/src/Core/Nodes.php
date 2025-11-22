<?php

namespace STRling\Core;

use JsonSerializable;

// ---- Flags ----

class Flags implements JsonSerializable
{
    public function __construct(
        public bool $ignoreCase = false,
        public bool $multiline = false,
        public bool $dotAll = false,
        public bool $unicode = false,
        public bool $extended = false,
    ) {}

    public static function fromLetters(string $letters): self
    {
        $f = new self();
        $cleaned = str_replace([',', ' '], '', $letters);
        
        foreach (str_split($cleaned) as $ch) {
            match ($ch) {
                'i' => $f->ignoreCase = true,
                'm' => $f->multiline = true,
                's' => $f->dotAll = true,
                'u' => $f->unicode = true,
                'x' => $f->extended = true,
                default => null,
            };
        }
        
        return $f;
    }

    public function jsonSerialize(): mixed
    {
        return [
            'ignoreCase' => $this->ignoreCase,
            'multiline' => $this->multiline,
            'dotAll' => $this->dotAll,
            'unicode' => $this->unicode,
            'extended' => $this->extended,
        ];
    }
}

// ---- Interfaces ----

interface Node extends JsonSerializable {}
interface ClassItem extends JsonSerializable {}

// ---- Concrete Nodes ----

readonly class Alternation implements Node
{
    /** @param Node[] $alternatives */
    public function __construct(
        public array $alternatives
    ) {}

    public function jsonSerialize(): mixed
    {
        return [
            'type' => 'Alternation',
            'alternatives' => $this->alternatives,
        ];
    }
}

readonly class Sequence implements Node
{
    /** @param Node[] $parts */
    public function __construct(
        public array $parts
    ) {}

    public function jsonSerialize(): mixed
    {
        return [
            'type' => 'Sequence',
            'parts' => $this->parts,
        ];
    }
}

readonly class Literal implements Node, ClassItem
{
    public function __construct(
        public string $value
    ) {}

    public function jsonSerialize(): mixed
    {
        return [
            'type' => 'Literal',
            'value' => $this->value,
        ];
    }
}

readonly class Dot implements Node
{
    public function jsonSerialize(): mixed
    {
        return ['type' => 'Dot'];
    }
}

readonly class Anchor implements Node
{
    public function __construct(
        public string $at
    ) {}

    public function jsonSerialize(): mixed
    {
        return [
            'type' => 'Anchor',
            'at' => $this->at,
        ];
    }
}

readonly class CharacterClass implements Node
{
    /** @param ClassItem[] $members */
    public function __construct(
        public bool $negated,
        public array $members
    ) {}

    public function jsonSerialize(): mixed
    {
        return [
            'type' => 'CharacterClass',
            'negated' => $this->negated,
            'members' => $this->members,
        ];
    }
}

readonly class Range implements ClassItem
{
    public function __construct(
        public string $from,
        public string $to
    ) {}

    public function jsonSerialize(): mixed
    {
        return [
            'type' => 'Range',
            'from' => $this->from,
            'to' => $this->to,
        ];
    }
}

readonly class Escape implements ClassItem
{
    public function __construct(
        public string $kind
    ) {}

    public function jsonSerialize(): mixed
    {
        return [
            'type' => 'Escape',
            'kind' => $this->kind,
        ];
    }
}

readonly class UnicodeProperty implements ClassItem
{
    public function __construct(
        public string $value,
        public ?string $name = null,
        public bool $negated = false
    ) {}

    public function jsonSerialize(): mixed
    {
        $data = [
            'type' => 'UnicodeProperty',
            'value' => $this->value,
            'negated' => $this->negated,
        ];
        if ($this->name !== null) {
            $data['name'] = $this->name;
        }
        return $data;
    }
}

readonly class Quantifier implements Node
{
    public function __construct(
        public Node $target,
        public int $min,
        public string|int|null $max, // "inf" or int or null
        public bool $greedy,
        public bool $lazy,
        public bool $possessive
    ) {}

    public function jsonSerialize(): mixed
    {
        return [
            'type' => 'Quantifier',
            'target' => $this->target,
            'min' => $this->min,
            'max' => $this->max,
            'greedy' => $this->greedy,
            'lazy' => $this->lazy,
            'possessive' => $this->possessive,
        ];
    }
}

readonly class Group implements Node
{
    public function __construct(
        public bool $capturing,
        public Node $body,
        public ?string $name = null,
        public ?bool $atomic = null,
        public ?int $number = null,
        public ?Node $expression = null
    ) {}

    public function jsonSerialize(): mixed
    {
        $data = [
            'type' => 'Group',
            'capturing' => $this->capturing,
            'body' => $this->body,
        ];
        if ($this->name !== null) $data['name'] = $this->name;
        if ($this->atomic !== null) $data['atomic'] = $this->atomic;
        if ($this->number !== null) $data['number'] = $this->number;
        if ($this->expression !== null) $data['expression'] = $this->expression;
        return $data;
    }
}

readonly class Backreference implements Node
{
    public function __construct(
        public ?int $index = null,
        public ?string $name = null
    ) {}

    public function jsonSerialize(): mixed
    {
        $data = ['type' => 'Backreference'];
        if ($this->index !== null) $data['index'] = $this->index;
        if ($this->name !== null) $data['name'] = $this->name;
        return $data;
    }
}

readonly class Lookahead implements Node
{
    public function __construct(
        public Node $body
    ) {}

    public function jsonSerialize(): mixed
    {
        return [
            'type' => 'Lookahead',
            'body' => $this->body,
        ];
    }
}

readonly class NegativeLookahead implements Node
{
    public function __construct(
        public Node $body
    ) {}

    public function jsonSerialize(): mixed
    {
        return [
            'type' => 'NegativeLookahead',
            'body' => $this->body,
        ];
    }
}

readonly class Lookbehind implements Node
{
    public function __construct(
        public Node $body
    ) {}

    public function jsonSerialize(): mixed
    {
        return [
            'type' => 'Lookbehind',
            'body' => $this->body,
        ];
    }
}

readonly class NegativeLookbehind implements Node
{
    public function __construct(
        public Node $body
    ) {}

    public function jsonSerialize(): mixed
    {
        return [
            'type' => 'NegativeLookbehind',
            'body' => $this->body,
        ];
    }
}
