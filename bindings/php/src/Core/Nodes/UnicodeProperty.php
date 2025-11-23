<?php

namespace STRling\Core\Nodes;

use JsonSerializable;


readonly class UnicodeProperty implements ClassItem
{
    public function __construct(
        public string $value,
        public ?string $name = null,
        public bool $negated = false
    ) {}

    public function jsonSerialize(): mixed
    {
        $data = [
            'type' => 'UnicodeProperty',
            'value' => $this->value,
            'negated' => $this->negated,
        ];
        if ($this->name !== null) {
            $data['name'] = $this->name;
        }
        return $data;
    }
}
