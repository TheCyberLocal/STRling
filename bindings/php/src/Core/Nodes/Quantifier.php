<?php

namespace STRling\Core\Nodes;

use JsonSerializable;


readonly class Quantifier implements Node
{
    public function __construct(
        public Node $target,
        public int $min,
        public string|int|null $max, // "inf" or int or null
        public bool $greedy,
        public bool $lazy,
        public bool $possessive
    ) {}

    public function jsonSerialize(): mixed
    {
        return [
            'type' => 'Quantifier',
            'target' => $this->target,
            'min' => $this->min,
            'max' => $this->max,
            'greedy' => $this->greedy,
            'lazy' => $this->lazy,
            'possessive' => $this->possessive,
        ];
    }
}
