<?php

namespace STRling\Core\IR;

use JsonSerializable;


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
