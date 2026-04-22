<?php

declare(strict_types=1);

namespace STRling\Core;

/**
 * Result of an emit pass: the produced PCRE2 pattern plus any non-fatal
 * diagnostics collected during emission.
 */
final class CompileResult
{
    /**
     * @param list<STRlingWarning> $warnings
     */
    public function __construct(
        public readonly string $pattern,
        public readonly array $warnings,
    ) {
    }
}
