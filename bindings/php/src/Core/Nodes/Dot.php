<?php

namespace STRling\Core\Nodes;

use JsonSerializable;


readonly class Dot implements Node
{
    public function jsonSerialize(): mixed
    {
        return ['type' => 'Dot'];
    }
}
