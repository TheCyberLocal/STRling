<?php

declare(strict_types=1);

namespace STRling;

final class NativeAdapterException extends \RuntimeException
{
    public function __construct(
        public readonly string $kind,
        string $message,
        public readonly ?int $status = null,
        ?\Throwable $previous = null,
    ) {
        parent::__construct(
            $status === null ? $message : sprintf('%s (status %d)', $message, $status),
            0,
            $previous,
        );
    }
}
