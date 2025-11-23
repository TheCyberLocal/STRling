<?php

namespace STRling\Core\Nodes;

use JsonSerializable;


readonly class Range implements ClassItem
{
    public function __construct(
        public string $from,
        public string $to
    ) {}

    public function jsonSerialize(): mixed
    {
        return [
            'type' => 'Range',
            'from' => $this->from,
            'to' => $this->to,
        ];
    }
}
