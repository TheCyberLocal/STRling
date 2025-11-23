<?php

namespace STRling\Core\Nodes;

use JsonSerializable;


readonly class NegativeLookbehind implements Node
{
    public function __construct(
        public Node $body
    ) {}

    public function jsonSerialize(): mixed
    {
        return [
            'type' => 'NegativeLookbehind',
            'body' => $this->body,
        ];
    }
}
