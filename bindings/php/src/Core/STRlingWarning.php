<?php

declare(strict_types=1);

namespace STRling\Core;

/**
 * Non-fatal diagnostic emitted alongside a compiled pattern. Currently
 * used for `REDOS_RISK` (nested unbounded quantifiers).
 *
 * The `__toString` form matches the SSOT `STRlingWarning [CODE]: message`
 * format so the global pathological fixture's `expected_warning`
 * substring compares 1:1 across bindings.
 */
final class STRlingWarning
{
    public function __construct(
        public readonly string $code,
        public readonly string $message,
    ) {
    }

    public function __toString(): string
    {
        return "STRlingWarning [{$this->code}]: {$this->message}";
    }
}
