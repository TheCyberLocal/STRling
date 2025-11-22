<?php

namespace STRling\Tests;

use PHPUnit\Framework\TestCase;
use PHPUnit\Framework\Attributes\DataProvider;
use STRling\Core\NodeFactory;
use STRling\Compiler;

class ConformanceTest extends TestCase
{
    #[DataProvider('provideSpecFiles')]
    public function testConformance(string $filename, array $spec): void
    {
        if (!isset($spec['input_ast']) || !isset($spec['expected_ir'])) {
            $this->markTestSkipped("Spec file $filename missing input_ast or expected_ir");
        }

        // 1. Hydrate AST
        try {
            $ast = NodeFactory::fromArray($spec['input_ast']);
        } catch (\Throwable $e) {
            $this->fail("Failed to hydrate AST in $filename: " . $e->getMessage());
        }

        // 2. Compile to IR
        $compiler = new Compiler();
        try {
            $ir = $compiler->compile($ast);
        } catch (\Throwable $e) {
            $this->fail("Failed to compile AST in $filename: " . $e->getMessage());
        }

        // 3. Serialize IR
        $serializedIr = json_decode(json_encode($ir), true);

        // 4. Assert Equality
        // We need to normalize expected_ir because sometimes order of keys might differ, 
        // but json_encode/decode usually handles assoc arrays consistently if keys match.
        // However, we might have extra null fields in our serialization that are not in expected_ir,
        // or vice versa.
        // My implementation of jsonSerialize filters nulls for some fields but not all.
        // Let's check strict equality first.
        
        $this->assertEquals($spec['expected_ir'], $serializedIr, "IR mismatch in $filename");
    }

    public static function provideSpecFiles(): \Generator
    {
        $specDir = __DIR__ . '/../../tests/spec';
        $files = glob($specDir . '/*.json');

        foreach ($files as $file) {
            $content = file_get_contents($file);
            $json = json_decode($content, true);
            
            if (json_last_error() !== JSON_ERROR_NONE) {
                continue;
            }

            yield basename($file) => [basename($file), $json];
        }
    }
}
