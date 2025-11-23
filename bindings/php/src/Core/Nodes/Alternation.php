<?php

namespace STRling\Core\Nodes;

use JsonSerializable;


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
