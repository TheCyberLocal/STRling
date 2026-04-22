<?php

declare(strict_types=1);

namespace STRling\Tests;

use PHPUnit\Framework\TestCase;
use STRling\Core\CompileResult;
use STRling\Core\STRlingCompilationError;
use STRling\Core\Nodes\{
    Node, Group, Literal, Lookahead, Lookbehind, NegativeLookahead, NegativeLookbehind, Quantifier
};
use STRling\Emitters\Pcre2Emitter;

/**
 * Emitter Edges Conformance — PHP bridge.
 *
 * Drives the global pathological-AST fixture
 * `tests/conformance/inputs/emitter_edges/pathological.json` through
 * the PHP {@see Pcre2Emitter} and asserts each safety guard fires:
 *   1. Variable-Length Lookbehind Rejection — STRlingCompilationError
 *   2. AST Depth Limit Exceeded             — STRlingCompilationError
 *   3. ReDoS Risk Warning (`(a+)+`)         — non-fatal STRlingWarning
 *
 * The local {@see astToNode} mirrors the TypeScript bridge so the test
 * targets the emitter without coupling to the parser/compiler stages.
 * Keep it minimal — supporting only node types currently appearing in
 * `pathological.json` — so adapter omissions cannot mask emitter bugs by
 * silently dropping nodes.
 */
final class EmitterEdgesConformanceTest extends TestCase
{
    private static function fixturePath(): string
    {
        $dir = __DIR__;
        for ($i = 0; $i < 12; $i++) {
            if (file_exists($dir . '/toolchain.json')) {
                return $dir . '/tests/conformance/inputs/emitter_edges/pathological.json';
            }
            $parent = dirname($dir);
            if ($parent === $dir) break;
            $dir = $parent;
        }
        throw new \RuntimeException("could not locate workspace root from " . __DIR__);
    }

    /**
     * @param array<string,mixed> $node
     */
    private function astToNode(array $node): Node
    {
        $type = (string)($node['type'] ?? '');
        switch ($type) {
            case 'Literal':
                return new Literal((string)($node['value'] ?? ''));
            case 'Group':
                return new Group(false, $this->astToNode($node['content']), null, false);
            case 'Quantifier':
                $child = $this->astToNode($node['content']);
                $min = (int)($node['min'] ?? 0);
                // null in the user-facing AST means unbounded → PHP's null sentinel.
                $rawMax = $node['max'] ?? null;
                $max = is_int($rawMax) ? $rawMax : null;
                return new Quantifier($child, $min, $max, true, false, false);
            case 'Lookbehind':
                return new Lookbehind($this->astToNode($node['content']));
            case 'NegativeLookbehind':
                return new NegativeLookbehind($this->astToNode($node['content']));
            case 'Lookahead':
                return new Lookahead($this->astToNode($node['content']));
            case 'NegativeLookahead':
                return new NegativeLookahead($this->astToNode($node['content']));
        }
        throw new \RuntimeException(
            "astToNode: unsupported pathological AST node type \"$type\". "
          . 'Extend the adapter when new pathological vectors are added.'
        );
    }

    private static function expectedSubstring(string $prefixed): string
    {
        if (str_starts_with($prefixed, 'STRlingCompilationError:')) {
            return ltrim(substr($prefixed, strlen('STRlingCompilationError:')));
        }
        if (str_starts_with($prefixed, 'STRlingWarning')) {
            $idx = strpos($prefixed, ']');
            if ($idx !== false) {
                return ltrim(substr($prefixed, $idx + 1), ': ');
            }
        }
        return $prefixed;
    }

    public function testPathologicalCases(): void
    {
        $raw = file_get_contents(self::fixturePath());
        $doc = json_decode($raw, true);
        $cases = $doc['tests'] ?? [];
        self::assertNotEmpty($cases, 'fixture is empty');

        foreach ($cases as $tc) {
            $name = $tc['name'] ?? '<unnamed>';
            $node = $this->astToNode($tc['ast']);
            $maxDepth = isset($tc['depth_override_for_test']) ? (int)$tc['depth_override_for_test'] : 0;

            if (isset($tc['expected_error'])) {
                $needle = self::expectedSubstring((string)$tc['expected_error']);
                $caught = null;
                try {
                    Pcre2Emitter::emitWithDiagnostics($node, null, $maxDepth);
                } catch (STRlingCompilationError $ex) {
                    $caught = $ex;
                }
                self::assertNotNull($caught, "[$name] expected STRlingCompilationError, got success");
                self::assertStringContainsString($needle, $caught->getMessage(), "[$name]");
                continue;
            }
            if (isset($tc['expected_warning'])) {
                $needle = self::expectedSubstring((string)$tc['expected_warning']);
                $result = Pcre2Emitter::emitWithDiagnostics($node, null, $maxDepth);
                self::assertInstanceOf(CompileResult::class, $result);
                // Warnings must NOT abort emission — the pattern is still produced.
                self::assertNotSame('', $result->pattern, "[$name] expected non-empty pattern when only a warning fires");
                $found = false;
                foreach ($result->warnings as $w) {
                    if ($w->code === 'REDOS_RISK' && str_contains($w->message, $needle)) {
                        $found = true;
                        break;
                    }
                }
                self::assertTrue($found, "[$name] missing REDOS_RISK warning containing \"$needle\"");
                continue;
            }
            self::fail("[$name] declares neither expected_error nor expected_warning");
        }
    }

    public function testNonPathologicalEmitsNoWarnings(): void
    {
        $result = Pcre2Emitter::emitWithDiagnostics(new Literal('abc'));
        self::assertSame('abc', $result->pattern);
        self::assertSame([], $result->warnings);
    }

    public function testDepthCapDoesNotFireUnderLimit(): void
    {
        $deep = new Group(false, new Group(false, new Literal('ok'), null, false), null, false);
        $result = Pcre2Emitter::emitWithDiagnostics($deep, null, 5);
        self::assertSame([], $result->warnings);
        self::assertStringContainsString('ok', $result->pattern);
    }
}
