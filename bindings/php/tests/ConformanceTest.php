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
        $specDir = __DIR__ . '/../../../tests/spec';
        $files = glob($specDir . '/*.json');

        if (empty($files)) {
            fwrite(STDERR, "DEBUG: No files found in $specDir. __DIR__ is " . __DIR__ . "\n");
            // Try to list the directory to see what's there
            if (is_dir($specDir)) {
                fwrite(STDERR, "DEBUG: Directory exists.\n");
            } else {
                fwrite(STDERR, "DEBUG: Directory does not exist.\n");
            }
        }

        foreach ($files as $file) {
            $content = file_get_contents($file);
            $json = json_decode($content, true);
            
            if (json_last_error() !== JSON_ERROR_NONE) {
                continue;
            }

            if (!isset($json['input_ast']) || !isset($json['expected_ir'])) {
                continue;
            }

            yield basename($file) => [basename($file), $json];
        }
    }
}
