<?php

namespace STRling\Core\Nodes;

use JsonSerializable;


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
