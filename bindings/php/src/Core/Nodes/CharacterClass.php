<?php

namespace STRling\Core\Nodes;

use JsonSerializable;


readonly class CharacterClass implements Node
{
    /** @param ClassItem[] $members */
    public function __construct(
        public bool $negated,
        public array $members
    ) {}

    public function jsonSerialize(): mixed
    {
        return [
            'type' => 'CharacterClass',
            'negated' => $this->negated,
            'members' => $this->members,
        ];
    }
}
