<?php

namespace STRling\Core;

use JsonSerializable;

interface IRNode extends JsonSerializable {}

readonly class Lit implements IRNode
{
    public function __construct(
        public string $value
    ) {}

    public function jsonSerialize(): mixed
    {
        return [
            'ir' => 'Lit',
            'value' => $this->value,
        ];
    }
}

readonly class Seq implements IRNode
{
    /** @param IRNode[] $parts */
    public function __construct(
        public array $parts
    ) {}

    public function jsonSerialize(): mixed
    {
        return [
            'ir' => 'Seq',
            'parts' => $this->parts,
        ];
    }
}

readonly class Quant implements IRNode
{
    public function __construct(
        public IRNode $child,
        public int $min,
        public string|int $max, // "Inf" or int
        public string $mode // "Greedy", "Lazy", "Possessive"
    ) {}

    public function jsonSerialize(): mixed
    {
        return [
            'ir' => 'Quant',
            'child' => $this->child,
            'min' => $this->min,
            'max' => $this->max,
            'mode' => $this->mode,
        ];
    }
}

readonly class CharClass implements IRNode
{
    /** @param IRNode[] $items */
    public function __construct(
        public bool $negated,
        public array $items
    ) {}

    public function jsonSerialize(): mixed
    {
        return [
            'ir' => 'CharClass',
            'negated' => $this->negated,
            'items' => $this->items,
        ];
    }
}

readonly class Char implements IRNode
{
    public function __construct(
        public string $char
    ) {}

    public function jsonSerialize(): mixed
    {
        return [
            'ir' => 'Char',
            'char' => $this->char,
        ];
    }
}

readonly class Esc implements IRNode
{
    public function __construct(
        public string $type,
        public ?string $property = null
    ) {}

    public function jsonSerialize(): mixed
    {
        $data = [
            'ir' => 'Esc',
            'type' => $this->type,
        ];
        if ($this->property !== null) {
            $data['property'] = $this->property;
        }
        return $data;
    }
}

readonly class Group implements IRNode
{
    public function __construct(
        public IRNode $child,
        public bool $capturing,
        public ?string $name = null,
        public ?int $number = null
    ) {}

    public function jsonSerialize(): mixed
    {
        $data = [
            'ir' => 'Group',
            'child' => $this->child,
            'capturing' => $this->capturing,
        ];
        if ($this->name !== null) $data['name'] = $this->name;
        if ($this->number !== null) $data['number'] = $this->number;
        return $data;
    }
}

readonly class Alt implements IRNode
{
    /** @param IRNode[] $alternatives */
    public function __construct(
        public array $alternatives
    ) {}

    public function jsonSerialize(): mixed
    {
        return [
            'ir' => 'Alt',
            'alternatives' => $this->alternatives,
        ];
    }
}

readonly class Anchor implements IRNode
{
    public function __construct(
        public string $type
    ) {}

    public function jsonSerialize(): mixed
    {
        return [
            'ir' => 'Anchor',
            'type' => $this->type,
        ];
    }
}

readonly class Range implements IRNode
{
    public function __construct(
        public string $from,
        public string $to
    ) {}

    public function jsonSerialize(): mixed
    {
        return [
            'ir' => 'Range',
            'from' => $this->from,
            'to' => $this->to,
        ];
    }
}

readonly class BackRef implements IRNode
{
    public function __construct(
        public ?int $index = null,
        public ?string $name = null
    ) {}

    public function jsonSerialize(): mixed
    {
        $data = ['ir' => 'BackRef'];
        if ($this->index !== null) $data['index'] = $this->index;
        if ($this->name !== null) $data['name'] = $this->name;
        return $data;
    }
}

readonly class LookAround implements IRNode
{
    public function __construct(
        public string $type, // "Lookahead", "Lookbehind"
        public bool $negated,
        public IRNode $child
    ) {}

    public function jsonSerialize(): mixed
    {
        return [
            'ir' => 'LookAround',
            'type' => $this->type,
            'negated' => $this->negated,
            'child' => $this->child,
        ];
    }
}
