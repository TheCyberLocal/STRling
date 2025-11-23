<?php

namespace STRling\Core\IR;

use JsonSerializable;


readonly class Group implements IRNode
{
    public function __construct(
        public IRNode $child,
        public bool $capturing,
        public ?string $name = null,
        public ?int $number = null,
        public bool $atomic = false
    ) {}

    public function jsonSerialize(): mixed
    {
        $data = [
            'ir' => 'Group',
            'body' => $this->child,
            'capturing' => $this->capturing,
        ];
        if ($this->name !== null) $data['name'] = $this->name;
        if ($this->number !== null) $data['number'] = $this->number;
        if ($this->atomic) $data['atomic'] = true;
        return $data;
    }
}
