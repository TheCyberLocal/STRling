<?php

declare(strict_types=1);

namespace STRling;

final class NativeClient
{
    private const CDEF = <<<'CDEF'
        typedef unsigned char uint8_t;
        typedef unsigned int uint32_t;
        typedef struct strling_interop_owned_bytes_v1 {
            uint8_t *data;
            size_t len;
        } strling_interop_owned_bytes_v1;
        uint32_t strling_interop_abi_version_v1(void);
        uint32_t strling_interop_execute_v1(const uint8_t *, size_t, strling_interop_owned_bytes_v1 *);
        uint32_t strling_interop_owned_bytes_free_v1(strling_interop_owned_bytes_v1 *);
        CDEF;

    private bool $closed = false;
    private int $activeCalls = 0;

    private function __construct(
        public readonly string $libraryPath,
        private ?\FFI $ffi,
    ) {
    }

    public static function load(string $libraryPath): self
    {
        if (!self::isAbsolute($libraryPath)) {
            throw new NativeAdapterException('native_load', 'native STRling library path must be absolute');
        }
        try {
            $normalized = realpath($libraryPath);
        } catch (\ValueError $error) {
            throw new NativeAdapterException('native_load', 'native STRling library path is invalid', null, $error);
        }
        if ($normalized === false || !is_file($normalized)) {
            throw new NativeAdapterException('native_load', sprintf('native STRling library not found: %s', $libraryPath));
        }
        if (!extension_loaded('ffi')) {
            throw new NativeAdapterException('native_load', 'PHP FFI extension is required');
        }
        try {
            $ffi = \FFI::cdef(self::CDEF, $normalized);
            $actual = $ffi->strling_interop_abi_version_v1();
        } catch (\Throwable $error) {
            throw new NativeAdapterException('native_load', 'cannot load the complete strling.c-abi v1', null, $error);
        }
        if ($actual !== STRling::NATIVE_ABI_VERSION) {
            throw new NativeAdapterException('native_abi', sprintf('expected strling.c-abi %d', STRling::NATIVE_ABI_VERSION), $actual);
        }
        return new self($normalized, $ffi);
    }

    public function isClosed(): bool
    {
        return $this->closed;
    }

    /** @param mixed $request
     *  @return array<string, mixed>
     */
    public function execute($request): array
    {
        try {
            $encoded = StrictJson::encode($request);
        } catch (\JsonException $error) {
            throw new NativeAdapterException('transport', 'interop request is not strict JSON', null, $error);
        }
        if (strlen($encoded) > STRling::MAX_INTEROP_REQUEST_BYTES) {
            throw new NativeAdapterException('transport', sprintf('interop request exceeds %d bytes', STRling::MAX_INTEROP_REQUEST_BYTES));
        }
        $ffi = $this->beginCall();
        try {
            return $this->executeBytes($ffi, $encoded);
        } finally {
            --$this->activeCalls;
        }
    }

    /** @return mixed */
    public function describe()
    {
        return $this->completedResult($this->envelope('describe', new \stdClass()));
    }

    /** @param array<string, mixed> $compileRequest
     *  @param ?array<string, mixed> $targetProfile
     *  @return mixed
     */
    public function compile(array $compileRequest, ?array $targetProfile = null)
    {
        $payload = ['compile_request' => $compileRequest];
        if ($targetProfile !== null) {
            $payload['target_profile'] = $targetProfile;
        }
        return $this->completedResult($this->envelope('compile', $payload));
    }

    /** @param array<string, mixed> $targetProfile
     *  @return mixed
     */
    public function inspectTargetProfile(array $targetProfile)
    {
        return $this->completedResult($this->envelope('target_profile.inspect', ['target_profile' => $targetProfile]));
    }

    /** @param array<string, mixed> $builderRequest
     *  @param ?array<string, mixed> $targetProfile
     *  @return mixed
     */
    public function simplyCompile(array $builderRequest, ?array $targetProfile = null)
    {
        $payload = ['builder_request' => $builderRequest];
        if ($targetProfile !== null) {
            $payload['target_profile'] = $targetProfile;
        }
        return $this->completedResult($this->envelope('simply.compile', $payload));
    }

    public function close(): void
    {
        if ($this->closed) {
            return;
        }
        if ($this->activeCalls !== 0) {
            throw new NativeAdapterException('closed_client', 'cannot close native STRling client during an active call');
        }
        $this->closed = true;
        $this->ffi = null;
    }

    private function beginCall(): \FFI
    {
        if ($this->closed || $this->ffi === null) {
            throw new NativeAdapterException('closed_client', 'native STRling client is closed');
        }
        ++$this->activeCalls;
        return $this->ffi;
    }

    /** @return array<string, mixed> */
    private function executeBytes(\FFI $ffi, string $encoded): array
    {
        $length = strlen($encoded);
        $input = $ffi->new(sprintf('uint8_t[%d]', max(1, $length)));
        if ($length !== 0) {
            \FFI::memcpy($input, $encoded, $length);
        }
        $output = $ffi->new('strling_interop_owned_bytes_v1');
        $primaryError = null;
        try {
            $status = $ffi->strling_interop_execute_v1($input, $length, \FFI::addr($output));
            if ($status !== 0) {
                throw new NativeAdapterException('native_abi', 'native STRling execution failed', $status);
            }
            $responseLength = (int) $output->len;
            if (\FFI::isNull($output->data) || $responseLength === 0 || $responseLength > STRling::MAX_INTEROP_RESPONSE_BYTES) {
                throw new NativeAdapterException('transport', 'native STRling returned an invalid or oversized response');
            }
            return $this->decodeResponse(\FFI::string($output->data, $responseLength));
        } catch (\Throwable $error) {
            $primaryError = $error;
            throw $error;
        } finally {
            $releaseStatus = $ffi->strling_interop_owned_bytes_free_v1(\FFI::addr($output));
            if ($primaryError === null && $releaseStatus !== 0) {
                throw new NativeAdapterException('native_abi', 'native STRling response release failed', $releaseStatus);
            }
        }
    }

    /** @return array<string, mixed> */
    private function decodeResponse(string $raw): array
    {
        try {
            $value = StrictJson::decodeObject($raw);
        } catch (\JsonException $error) {
            throw new NativeAdapterException('transport', 'native STRling response is not strict UTF-8 JSON', null, $error);
        }
        if (($value['interop_protocol_version'] ?? null) !== STRling::INTEROP_PROTOCOL_VERSION) {
            throw new NativeAdapterException('transport', 'interop response has an unsupported version');
        }
        $status = $value['status'] ?? null;
        if ($status !== 'completed' && $status !== 'error') {
            throw new NativeAdapterException('transport', 'interop response has an unsupported status');
        }
        if ($status === 'completed' && !array_key_exists('result', $value)) {
            throw new NativeAdapterException('transport', 'completed interop response has no result');
        }
        if ($status === 'error') {
            $error = $value['error'] ?? null;
            if (!is_array($error) || !is_string($error['code'] ?? null) || !is_string($error['path'] ?? null)) {
                throw new NativeAdapterException('transport', 'failed interop response has no stable code and path');
            }
        }
        return $value;
    }

    /** @param array<string, mixed> $payload
     *  @return array<string, mixed>
     */
    private function envelope(string $operation, mixed $payload): array
    {
        return [
            'interop_protocol_version' => STRling::INTEROP_PROTOCOL_VERSION,
            'operation' => $operation,
            'payload' => $payload,
        ];
    }

    /** @param array<string, mixed> $request
     *  @return mixed
     */
    private function completedResult(array $request)
    {
        $response = $this->execute($request);
        if ($response['status'] === 'error') {
            throw new InteropProtocolException($response);
        }
        return $response['result'];
    }

    private static function isAbsolute(string $path): bool
    {
        return str_starts_with($path, '/') || preg_match('/\A(?:[A-Za-z]:[\\\\\/]|\\\\\\\\)/', $path) === 1;
    }
}
