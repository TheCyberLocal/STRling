<?php

declare(strict_types=1);

namespace STRling\Core;

/**
 * Fatal emitter-stage failure raised by an IR safety guard.
 *
 * Mirrors the `STRlingCompilationError` type in the TypeScript reference
 * and the matching types in every other binding. Carries a stable
 * `code` (`VLB_NOT_SUPPORTED`, `MAX_DEPTH`) and the offending `engine`
 * so cross-binding parity tests can match on shared substrings without
 * coupling to a specific message wording.
 */
class STRlingCompilationError extends \Exception
{
    public readonly string $errorCode;
    public readonly string $engine;

    public function __construct(
        string $message,
        string $code,
        string $engine = 'pcre2',
    ) {
        parent::__construct($message);
        // Property is named `errorCode` (not `code`) to avoid colliding
        // with `\Exception::$code`, which is `int` and not readonly.
        $this->errorCode = $code;
        $this->engine = $engine;
    }
}
