<?php

namespace STRling\Core\Nodes;

use JsonSerializable;


// ---- Flags ----

class Flags implements JsonSerializable
{
    public function __construct(
        public bool $ignoreCase = false,
        public bool $multiline = false,
        public bool $dotAll = false,
        public bool $unicode = false,
        public bool $extended = false,
    ) {}

    public static function fromLetters(string $letters): self
    {
        $f = new self();
        $cleaned = str_replace([',', ' '], '', $letters);
        
        foreach (str_split($cleaned) as $ch) {
            match ($ch) {
                'i' => $f->ignoreCase = true,
                'm' => $f->multiline = true,
                's' => $f->dotAll = true,
                'u' => $f->unicode = true,
                'x' => $f->extended = true,
                default => null,
            };
        }
        
        return $f;
    }

    public function jsonSerialize(): mixed
    {
        return [
            'ignoreCase' => $this->ignoreCase,
            'multiline' => $this->multiline,
            'dotAll' => $this->dotAll,
            'unicode' => $this->unicode,
            'extended' => $this->extended,
        ];
    }
}
