<?php

namespace STRling\Core\Nodes;

use JsonSerializable;


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
