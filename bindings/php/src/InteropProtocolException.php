<?php

declare(strict_types=1);

namespace STRling;

final class InteropProtocolException extends \RuntimeException
{
    /** @param array<string, mixed> $response */
    public function __construct(
        public readonly array $response,
    ) {
        $error = $response['error'];
        $this->codeId = $error['code'];
        $this->path = $error['path'];
        $this->operation = isset($response['operation']) ? (string) $response['operation'] : null;
        parent::__construct(sprintf('%s at %s', $this->codeId, $this->path));
    }

    public readonly string $codeId;
    public readonly string $path;
    public readonly ?string $operation;
}
