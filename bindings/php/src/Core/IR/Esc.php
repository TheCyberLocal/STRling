<?php

namespace STRling\Core\IR;

use JsonSerializable;


readonly class Esc implements IRNode
{
    public function __construct(
        public string $type,
        public ?string $property = null
    ) {}

    public function jsonSerialize(): mixed
    {
        $data = [
            'ir' => 'Esc',
            'type' => $this->type,
        ];
        if ($this->property !== null) {
            $data['property'] = $this->property;
        }
        return $data;
    }
}
