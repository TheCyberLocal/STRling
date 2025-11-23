<?php

namespace STRling\Core\IR;

use JsonSerializable;


readonly class LookAround implements IRNode
{
    public function __construct(
        public string $type, // "Lookahead", "Lookbehind"
        public bool $negated,
        public IRNode $child
    ) {}

    public function jsonSerialize(): mixed
    {
        $dir = match($this->type) {
            'Lookahead' => 'Ahead',
            'Lookbehind' => 'Behind',
            default => $this->type
        };
        return [
            'ir' => 'Look',
            'dir' => $dir,
            'neg' => $this->negated,
            'body' => $this->child,
        ];
    }
}
