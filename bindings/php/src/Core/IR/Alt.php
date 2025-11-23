<?php

namespace STRling\Core\IR;

use JsonSerializable;


readonly class Alt implements IRNode
{
    /** @param IRNode[] $alternatives */
    public function __construct(
        public array $alternatives
    ) {}

    public function jsonSerialize(): mixed
    {
        return [
            'ir' => 'Alt',
            'branches' => $this->alternatives,
        ];
    }
}
