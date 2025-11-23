<?php

namespace STRling\Core\IR;

use JsonSerializable;


readonly class BackRef implements IRNode
{
    public function __construct(
        public ?int $index = null,
        public ?string $name = null
    ) {}

    public function jsonSerialize(): mixed
    {
        $data = ['ir' => 'Backref'];
        if ($this->index !== null) $data['byIndex'] = $this->index;
        if ($this->name !== null) $data['byName'] = $this->name;
        return $data;
    }
}
