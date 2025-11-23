<?php

namespace STRling\Core\Nodes;

use JsonSerializable;


readonly class Lookbehind implements Node
{
    public function __construct(
        public Node $body
    ) {}

    public function jsonSerialize(): mixed
    {
        return [
            'type' => 'Lookbehind',
            'body' => $this->body,
        ];
    }
}
