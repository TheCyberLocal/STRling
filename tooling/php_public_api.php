<?php

declare(strict_types=1);

/** Non-executing token_get_all public API extractor for the STRling PHP package. */

function fail(string $message): never
{
    fwrite(STDERR, $message . PHP_EOL);
    exit(2);
}

/** @return array{id: ?int, text: string} */
function token_record(array|string $token): array
{
    return is_array($token)
        ? ['id' => $token[0], 'text' => $token[1]]
        : ['id' => null, 'text' => $token];
}

/** @param list<array{id: ?int, text: string}> $tokens */
function normalized(array $tokens): string
{
    $text = implode(' ', array_map(static fn(array $token): string => $token['text'], $tokens));
    $text = preg_replace('/\s+/', ' ', trim($text)) ?? '';
    $text = preg_replace('/\s*([(),;:{}\[\]])\s*/', '$1', $text) ?? '';
    $text = preg_replace('/\s*(\?|\||&|=|::|->)\s*/', '$1', $text) ?? '';
    return $text;
}

/** @param list<array{id: ?int, text: string}> $tokens */
function next_identifier(array $tokens, int $start): ?array
{
    for ($index = $start; $index < count($tokens); ++$index) {
        if ($tokens[$index]['id'] === T_STRING) {
            return [$index, $tokens[$index]['text']];
        }
        if (!in_array($tokens[$index]['id'], [T_WHITESPACE, T_FINAL, T_ABSTRACT, T_READONLY], true)) {
            return null;
        }
    }
    return null;
}

$paths = [];
foreach (array_slice($argv, 1) as $location) {
    $matches = glob($location, GLOB_BRACE) ?: [];
    if ($matches === [] && is_file($location)) {
        $matches = [$location];
    }
    foreach ($matches as $path) {
        if (is_file($path) && pathinfo($path, PATHINFO_EXTENSION) === 'php') {
            $paths[$path] = true;
        }
    }
}
if ($paths === []) {
    fail('PHP public extractor matched no source files');
}

$symbols = [];
foreach (array_keys($paths) as $path) {
    $source = file_get_contents($path);
    if ($source === false) {
        fail(sprintf('cannot read PHP public source %s', $path));
    }
    try {
        $rawTokens = token_get_all($source, TOKEN_PARSE);
    } catch (ParseError $error) {
        fail(sprintf('cannot parse PHP public source %s: %s', $path, $error->getMessage()));
    }
    $tokens = [];
    foreach ($rawTokens as $rawToken) {
        $token = token_record($rawToken);
        if (in_array($token['id'], [T_WHITESPACE, T_COMMENT, T_DOC_COMMENT, T_OPEN_TAG, T_CLOSE_TAG], true)) {
            continue;
        }
        $tokens[] = $token;
    }

    $namespace = '';
    $class = null;
    $classDepth = null;
    $pendingClass = null;
    $depth = 0;
    for ($index = 0; $index < count($tokens); ++$index) {
        $token = $tokens[$index];
        if ($token['id'] === T_NAMESPACE) {
            $parts = [];
            for (++$index; $index < count($tokens) && !in_array($tokens[$index]['text'], [';', '{'], true); ++$index) {
                $parts[] = $tokens[$index];
            }
            $namespace = normalized($parts);
            continue;
        }
        if (in_array($token['id'], [T_CLASS, T_INTERFACE, T_TRAIT, defined('T_ENUM') ? T_ENUM : -1], true)) {
            $identifier = next_identifier($tokens, $index + 1);
            if ($identifier === null) {
                fail(sprintf('unsupported anonymous PHP type in %s', $path));
            }
            [$nameIndex, $name] = $identifier;
            $declaration = [$token, $tokens[$nameIndex]];
            $cursor = $nameIndex + 1;
            while ($cursor < count($tokens) && $tokens[$cursor]['text'] !== '{') {
                $declaration[] = $tokens[$cursor];
                ++$cursor;
            }
            if ($cursor >= count($tokens)) {
                fail(sprintf('unterminated PHP type %s in %s', $name, $path));
            }
            $qualified = $namespace === '' ? $name : $namespace . '\\' . $name;
            $symbols['type:' . $qualified] = normalized($declaration);
            $pendingClass = $qualified;
            $index = $cursor - 1;
            continue;
        }
        if ($token['text'] === '{') {
            ++$depth;
            if ($pendingClass !== null) {
                $class = $pendingClass;
                $classDepth = $depth;
                $pendingClass = null;
            }
            continue;
        }
        if ($token['text'] === '}') {
            if ($classDepth !== null && $depth === $classDepth) {
                $class = null;
                $classDepth = null;
            }
            --$depth;
            continue;
        }
        if ($class === null || $classDepth !== $depth) {
            continue;
        }

        $declarationIds = [
            T_PUBLIC, T_PROTECTED, T_PRIVATE, T_STATIC, T_ABSTRACT, T_FINAL,
            T_READONLY, T_FUNCTION, T_CONST, T_VAR, T_VARIABLE,
        ];
        if (!in_array($token['id'], $declarationIds, true)) {
            continue;
        }
        $declaration = [];
        $parentheses = 0;
        $brackets = 0;
        $cursor = $index;
        $terminator = null;
        for (; $cursor < count($tokens); ++$cursor) {
            $current = $tokens[$cursor];
            if ($current['text'] === '(') {
                ++$parentheses;
            } elseif ($current['text'] === ')') {
                --$parentheses;
            } elseif ($current['text'] === '[') {
                ++$brackets;
            } elseif ($current['text'] === ']') {
                --$brackets;
            }
            if ($parentheses === 0 && $brackets === 0 && in_array($current['text'], [';', '{'], true)) {
                $terminator = $current['text'];
                break;
            }
            $declaration[] = $current;
        }
        if ($terminator === null) {
            fail(sprintf('unterminated PHP member in %s', $path));
        }
        $ids = array_column($declaration, 'id');
        $visibility = in_array(T_PRIVATE, $ids, true) ? 'private' : (in_array(T_PROTECTED, $ids, true) ? 'protected' : 'public');
        if ($visibility !== 'private') {
            if (in_array(T_FUNCTION, $ids, true)) {
                $functionIndex = array_search(T_FUNCTION, $ids, true);
                $identifier = next_identifier($declaration, (int) $functionIndex + 1);
                if ($identifier === null) {
                    fail(sprintf('unsupported anonymous PHP public function in %s', $path));
                }
                $symbols['method:' . $class . '::' . $identifier[1]] = normalized($declaration);
            } elseif (in_array(T_CONST, $ids, true)) {
                $constIndex = array_search(T_CONST, $ids, true);
                $identifier = next_identifier($declaration, (int) $constIndex + 1);
                if ($identifier === null) {
                    fail(sprintf('unsupported PHP public constant in %s', $path));
                }
                $symbols['constant:' . $class . '::' . $identifier[1]] = normalized($declaration);
            } else {
                foreach ($declaration as $memberToken) {
                    if ($memberToken['id'] === T_VARIABLE) {
                        $symbols['property:' . $class . '::' . $memberToken['text']] = normalized($declaration);
                    }
                }
            }
        }
        $index = $cursor - ($terminator === '{' ? 1 : 0);
    }
}

if ($symbols === []) {
    fail('PHP public extractor returned no symbols');
}
ksort($symbols, SORT_STRING);
echo json_encode($symbols, JSON_THROW_ON_ERROR | JSON_UNESCAPED_SLASHES) . PHP_EOL;
