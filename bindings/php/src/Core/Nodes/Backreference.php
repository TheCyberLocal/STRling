<?php

namespace STRling\Core\Nodes;

use JsonSerializable;


readonly class Backreference implements Node
{
    public function __construct(
        public ?int $index = null,
        public ?string $name = null
    ) {}

    public function jsonSerialize(): mixed
    {
        $data = ['type' => 'Backreference'];
        if ($this->index !== null) $data['index'] = $this->index;
        if ($this->name !== null) $data['name'] = $this->name;
        return $data;
    }
}
