<?php

declare(strict_types=1);

namespace STRling\Tests;

use PHPUnit\Framework\TestCase;
use STRling\NativeAdapterException;
use STRling\Requests;
use STRling\Stdlib;
use STRling\STRling;

final class AdapterTest extends TestCase
{
    public function testCanonicalRequestAndLexicalHelperShapes(): void
    {
        $request = Requests::sourceCompileRequest('literal "hello"');
        self::assertSame('1.0.0', $request['contract_version']);
        self::assertSame('semantic_strling', $request['input']['document']['frontend']['id']);
        self::assertSame('stdlib.email', Stdlib::email('root')['arguments']['helper_id']);
        self::assertNull(Stdlib::uuid('root')['arguments']['parameters']['version']);
    }

    public function testStdlibHelpersConsumeCanonicalEssentialFixture(): void
    {
        $path = dirname(__DIR__, 3) . '/spec/stdlib/essential_5.json';
        $encoded = file_get_contents($path);
        self::assertNotFalse($encoded);
        $fixture = json_decode($encoded, true, 512, JSON_THROW_ON_ERROR);
        $steps = [
            'dateTime' => Stdlib::dateTime('date-time'),
            'email' => Stdlib::email('email'),
            'ip' => Stdlib::ip('ip'),
            'url' => Stdlib::url('url'),
            'uuid' => Stdlib::uuid('uuid'),
        ];
        $fixtureNames = array_keys($fixture['patterns']);
        $helperNames = array_keys($steps);
        sort($fixtureNames);
        sort($helperNames);
        self::assertSame($fixtureNames, $helperNames);
        foreach ($steps as $name => $step) {
            $helperId = $name === 'dateTime' ? 'date_time' : $name;
            self::assertSame('stdlib.' . $helperId, $step['arguments']['helper_id']);
        }
    }

    public function testRelativePathFailsClosed(): void
    {
        $this->expectException(NativeAdapterException::class);
        STRling::loadNative('libstrling_interop.so');
    }

    public function testNullBytePathFailsClosed(): void
    {
        $this->expectException(NativeAdapterException::class);
        STRling::loadNative("/tmp/strling\0invalid");
    }

    public function testLiveNativeTransportWhenCertificationProbeIsSupplied(): void
    {
        $path = getenv('STRLING_DYNAMIC_PROBE');
        if ($path === false) {
            self::markTestSkipped('certification probe unavailable');
        }
        $client = STRling::loadNative($path);
        $expected = ['unicode' => '雪'];
        $results = [
            'describe' => $client->describe(),
            'compile' => $client->compile(Requests::sourceCompileRequest('literal "雪"')),
            'target_profile.inspect' => $client->inspectTargetProfile(['contract_version' => '1.0.0']),
            'simply.compile' => $client->simplyCompile(Requests::simplyBuilderRequest([Stdlib::email('root')], 'root')),
        ];
        foreach ($results as $result) {
            self::assertSame($expected, $result);
        }
        $evidenceDir = getenv('STRLING_DYNAMIC_EVIDENCE_DIR');
        if ($evidenceDir !== false) {
            file_put_contents(
                $evidenceDir . '/php.json',
                json_encode($results, JSON_THROW_ON_ERROR | JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES),
            );
        }
        $client->close();
        self::assertTrue($client->isClosed());
        $client->close();
        $this->expectException(NativeAdapterException::class);
        $client->describe();
    }

    public function testTransportProbesFailClosed(): void
    {
        $executed = 0;
        foreach (['STRLING_DYNAMIC_ABI_PROBE', 'STRLING_DYNAMIC_OVERSIZE_PROBE', 'STRLING_DYNAMIC_DUPLICATE_PROBE', 'STRLING_DYNAMIC_INVALID_UTF8_PROBE', 'STRLING_DYNAMIC_RELEASE_FAILURE_PROBE'] as $name) {
            $path = getenv($name);
            if ($path === false) {
                continue;
            }
            $executed++;
            try {
                STRling::loadNative($path)->describe();
                self::fail(sprintf('%s was accepted', $name));
            } catch (NativeAdapterException) {
                self::addToAssertionCount(1);
            }
        }
        if ($executed === 0) {
            self::markTestSkipped('Certification probes are not available in this focused run.');
        }
    }
}
