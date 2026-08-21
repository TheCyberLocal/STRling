<?php

declare(strict_types=1);

namespace STRling;

// Generated from the canonical standard-library registry. Do not edit.
// These lexical helpers record Simply recipes; they do not validate semantics.
final class Stdlib
{
    public const SURFACE_SOURCE_SHA256 = '36779a57c8016a0ff4a1ba00e9c6cb198246bf8e170edb1e0d627c0ed91f19a0';
    public const REGISTRY_VERSION = '1.0.0';
    public const HELPER_IDS = ['stdlib.date_time', 'stdlib.email', 'stdlib.ip', 'stdlib.url', 'stdlib.uuid'];

    /** @return array<string, mixed> */
    public static function dateTime(string $stepId): array
    {
        return Requests::stdlibHelper($stepId, 'stdlib.date_time');
    }

    /** @return array<string, mixed> */
    public static function email(string $stepId): array
    {
        return Requests::stdlibHelper($stepId, 'stdlib.email');
    }

    /** @return array<string, mixed> */
    public static function ip(string $stepId, ?int $version = null): array
    {
        return Requests::stdlibHelper($stepId, 'stdlib.ip', ['version' => $version]);
    }

    /** @return array<string, mixed> */
    public static function url(string $stepId): array
    {
        return Requests::stdlibHelper($stepId, 'stdlib.url');
    }

    /** @return array<string, mixed> */
    public static function uuid(string $stepId, ?int $version = null): array
    {
        return Requests::stdlibHelper($stepId, 'stdlib.uuid', ['version' => $version]);
    }

}
