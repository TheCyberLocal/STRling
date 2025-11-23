<?php

namespace STRling\Core\IR;

use JsonSerializable;


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
