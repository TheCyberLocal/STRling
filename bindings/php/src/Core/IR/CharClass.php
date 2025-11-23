<?php

namespace STRling\Core\IR;

use JsonSerializable;


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
