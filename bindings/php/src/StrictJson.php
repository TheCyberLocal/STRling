<?php

declare(strict_types=1);

namespace STRling;

/** Strict JSON codec with duplicate-property rejection. */
final class StrictJson
{
    /** @param mixed $value */
    public static function encode($value): string
    {
        return json_encode($value, JSON_THROW_ON_ERROR | JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES);
    }

    /** @return array<string, mixed> */
    public static function decodeObject(string $json): array
    {
        $offset = 0;
        self::scanValue($json, $offset);
        self::skipWhitespace($json, $offset);
        if ($offset !== strlen($json)) {
            throw new \JsonException('trailing JSON content');
        }
        $value = json_decode($json, true, 512, JSON_THROW_ON_ERROR | JSON_BIGINT_AS_STRING);
        if (!is_array($value) || array_is_list($value)) {
            throw new \JsonException('interop response must be an object');
        }
        return $value;
    }

    private static function scanValue(string $json, int &$offset): void
    {
        self::skipWhitespace($json, $offset);
        $char = $json[$offset] ?? '';
        if ($char === '{') {
            self::scanObject($json, $offset);
            return;
        }
        if ($char === '[') {
            self::scanArray($json, $offset);
            return;
        }
        if ($char === '"') {
            self::scanString($json, $offset);
            return;
        }
        $remaining = substr($json, $offset);
        if (preg_match('/\A(?:true|false|null)/', $remaining, $match) === 1) {
            $offset += strlen($match[0]);
            return;
        }
        if (preg_match('/\A-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?(?:[eE][+-]?[0-9]+)?/', $remaining, $match) === 1) {
            $offset += strlen($match[0]);
            return;
        }
        throw new \JsonException(sprintf('invalid JSON token at byte %d', $offset));
    }

    private static function scanObject(string $json, int &$offset): void
    {
        ++$offset;
        self::skipWhitespace($json, $offset);
        if (($json[$offset] ?? '') === '}') {
            ++$offset;
            return;
        }
        $keys = [];
        while (true) {
            self::skipWhitespace($json, $offset);
            $literal = self::scanString($json, $offset);
            $key = json_decode($literal, true, 2, JSON_THROW_ON_ERROR);
            $identity = "\0" . $key;
            if (isset($keys[$identity])) {
                throw new \JsonException(sprintf('duplicate property %s', $literal));
            }
            $keys[$identity] = true;
            self::skipWhitespace($json, $offset);
            if (($json[$offset] ?? '') !== ':') {
                throw new \JsonException(sprintf('expected colon at byte %d', $offset));
            }
            ++$offset;
            self::scanValue($json, $offset);
            self::skipWhitespace($json, $offset);
            $delimiter = $json[$offset] ?? '';
            if ($delimiter === '}') {
                ++$offset;
                return;
            }
            if ($delimiter !== ',') {
                throw new \JsonException(sprintf('expected object delimiter at byte %d', $offset));
            }
            ++$offset;
        }
    }

    private static function scanArray(string $json, int &$offset): void
    {
        ++$offset;
        self::skipWhitespace($json, $offset);
        if (($json[$offset] ?? '') === ']') {
            ++$offset;
            return;
        }
        while (true) {
            self::scanValue($json, $offset);
            self::skipWhitespace($json, $offset);
            $delimiter = $json[$offset] ?? '';
            if ($delimiter === ']') {
                ++$offset;
                return;
            }
            if ($delimiter !== ',') {
                throw new \JsonException(sprintf('expected array delimiter at byte %d', $offset));
            }
            ++$offset;
        }
    }

    private static function scanString(string $json, int &$offset): string
    {
        $start = $offset;
        if (($json[$offset] ?? '') !== '"') {
            throw new \JsonException(sprintf('expected string at byte %d', $offset));
        }
        ++$offset;
        $length = strlen($json);
        while ($offset < $length) {
            $char = $json[$offset++];
            if ($char === '"') {
                return substr($json, $start, $offset - $start);
            }
            if (ord($char) < 0x20) {
                throw new \JsonException('unescaped control character in string');
            }
            if ($char !== '\\') {
                continue;
            }
            $escape = $json[$offset++] ?? '';
            if ($escape === 'u') {
                $hex = substr($json, $offset, 4);
                if (strlen($hex) !== 4 || preg_match('/\A[0-9a-fA-F]{4}\z/', $hex) !== 1) {
                    throw new \JsonException('invalid Unicode escape');
                }
                $offset += 4;
            } elseif (!str_contains('"\\/bfnrt', $escape)) {
                throw new \JsonException('invalid string escape');
            }
        }
        throw new \JsonException('unterminated string');
    }

    private static function skipWhitespace(string $json, int &$offset): void
    {
        $length = strlen($json);
        while ($offset < $length && str_contains(" \t\r\n", $json[$offset])) {
            ++$offset;
        }
    }
}
