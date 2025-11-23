<?php

namespace STRling\Core\IR;

use JsonSerializable;


readonly class Anchor implements IRNode
{
    public function __construct(
        public string $type
    ) {}

    public function jsonSerialize(): mixed
    {
        return [
            'ir' => 'Anchor',
            'at' => $this->type,
        ];
    }
}
