<?php

namespace STRling\Core\IR;

use JsonSerializable;

readonly class Dot implements IRNode
{
    public function jsonSerialize(): mixed
    {
        return ['ir' => 'Dot'];
    }
}
