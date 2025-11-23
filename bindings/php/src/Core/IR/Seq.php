<?php

namespace STRling\Core\IR;

use JsonSerializable;


readonly class Seq implements IRNode
{
    /** @param IRNode[] $parts */
    public function __construct(
        public array $parts
    ) {}

    public function jsonSerialize(): mixed
    {
        return [
            'ir' => 'Seq',
            'parts' => $this->parts,
        ];
    }
}
