<?php

namespace STRling\Core\IR;

use JsonSerializable;


readonly class Quant implements IRNode
{
    public function __construct(
        public IRNode $child,
        public int $min,
        public string|int $max, // "Inf" or int
        public string $mode // "Greedy", "Lazy", "Possessive"
    ) {}

    public function jsonSerialize(): mixed
    {
        return [
            'ir' => 'Quant',
            'child' => $this->child,
            'min' => $this->min,
            'max' => $this->max,
            'mode' => $this->mode,
        ];
    }
}
