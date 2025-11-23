<?php

namespace STRling\Core\Nodes;

use JsonSerializable;


readonly class NegativeLookahead implements Node
{
    public function __construct(
        public Node $body
    ) {}

    public function jsonSerialize(): mixed
    {
        return [
            'type' => 'NegativeLookahead',
            'body' => $this->body,
        ];
    }
}
