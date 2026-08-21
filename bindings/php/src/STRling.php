<?php

declare(strict_types=1);

namespace STRling;

final class STRling
{
    public const VERSION = '3.0.0';
    public const INTEROP_PROTOCOL_VERSION = '1.0.0';
    public const NATIVE_ABI_VERSION = 1;
    public const MAX_INTEROP_REQUEST_BYTES = 10_485_760;
    public const MAX_INTEROP_RESPONSE_BYTES = 33_554_432;

    public static function loadNative(string $libraryPath): NativeClient
    {
        return NativeClient::load($libraryPath);
    }
}
