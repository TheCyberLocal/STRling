<?php

namespace STRling\Core\Nodes;

use JsonSerializable;


readonly class Lookahead implements Node
{
    public function __construct(
        public Node $body
    ) {}

    public function jsonSerialize(): mixed
    {
        return [
            'type' => 'Lookahead',
            'body' => $this->body,
        ];
    }
}
