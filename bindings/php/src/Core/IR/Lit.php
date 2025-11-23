<?php

namespace STRling\Core\IR;

use JsonSerializable;

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
