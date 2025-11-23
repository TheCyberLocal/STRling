<?php

namespace STRling\Core\Nodes;

use JsonSerializable;


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
