<?php

namespace STRling\Core\Nodes;

use JsonSerializable;


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
