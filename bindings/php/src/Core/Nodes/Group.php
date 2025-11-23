<?php

namespace STRling\Core\Nodes;

use JsonSerializable;


readonly class Group implements Node
{
    public function __construct(
        public bool $capturing,
        public Node $body,
        public ?string $name = null,
        public ?bool $atomic = null,
        public ?int $number = null,
        public ?Node $expression = null
    ) {}

    public function jsonSerialize(): mixed
    {
        $data = [
            'type' => 'Group',
            'capturing' => $this->capturing,
            'body' => $this->body,
        ];
        if ($this->name !== null) $data['name'] = $this->name;
        if ($this->atomic !== null) $data['atomic'] = $this->atomic;
        if ($this->number !== null) $data['number'] = $this->number;
        if ($this->expression !== null) $data['expression'] = $this->expression;
        return $data;
    }
}
