package com.strling.jvm;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

import com.sun.jna.Memory;
import com.sun.jna.Pointer;
import java.nio.charset.StandardCharsets;
import java.util.Collections;
import java.util.Map;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicInteger;
import org.junit.jupiter.api.Test;

final class NativeClientTest {
    @Test
    void releasesTheSameDescriptorAfterSuccess() {
        FakeLibrary library = new FakeLibrary(completed("describe", "{}"));
        NativeClient client = new NativeClient(library);

        assertEquals(Collections.emptyMap(), client.describe());
        assertEquals(1, library.executeCalls.get());
        assertEquals(1, library.freeCalls.get());
        assertEquals(library.executedDescriptor, library.freedDescriptor);
    }

    @Test
    void releasesAfterMalformedUtf8() {
        FakeLibrary library = new FakeLibrary(new byte[] {(byte) 0xc3, (byte) 0x28});
        NativeClient client = new NativeClient(library);

        assertThrows(TransportException.class,
                () -> client.execute(Collections.singletonMap("x", "y")));
        assertEquals(1, library.freeCalls.get());
        assertEquals(library.executedDescriptor, library.freedDescriptor);
    }

    @Test
    void rejectsDuplicateJsonKeysAndStillReleases() {
        String response = "{\"interop_protocol_version\":\"1.0.0\","
                + "\"status\":\"completed\",\"status\":\"completed\","
                + "\"result\":{}}";
        FakeLibrary library = new FakeLibrary(response.getBytes(StandardCharsets.UTF_8));
        NativeClient client = new NativeClient(library);

        assertThrows(TransportException.class, client::describe);
        assertEquals(1, library.freeCalls.get());
        assertEquals(library.executedDescriptor, library.freedDescriptor);
    }

    @Test
    void rejectsOversizedNativeResponseBeforeReadingIt() {
        FakeLibrary library = new FakeLibrary(
                completed("describe", "{}"), NativeClient.MAX_INTEROP_RESPONSE_BYTES + 1L);
        NativeClient client = new NativeClient(library);

        assertThrows(TransportException.class, client::describe);
        assertEquals(1, library.freeCalls.get());
        assertEquals(library.executedDescriptor, library.freedDescriptor);
    }

    @Test
    void distinguishesStableProtocolErrors() {
        String response = "{\"interop_protocol_version\":\"1.0.0\","
                + "\"operation\":\"compile\",\"status\":\"error\","
                + "\"error\":{\"code\":\"STRL-INTEROP-0004\",\"path\":\"$.payload\"}}";
        NativeClient client = new NativeClient(
                new FakeLibrary(response.getBytes(StandardCharsets.UTF_8)));

        ProtocolException error = assertThrows(ProtocolException.class,
                () -> client.compile(Collections.emptyMap()));
        assertEquals("STRL-INTEROP-0004", error.getCode());
        assertEquals("$.payload", error.getPath());
        assertEquals("compile", error.getOperation());
    }

    @Test
    void rejectsNonFiniteRequestsBeforeNativeExecution() {
        FakeLibrary library = new FakeLibrary(completed("describe", "{}"));
        NativeClient client = new NativeClient(library);

        assertThrows(TransportException.class,
                () -> client.execute(Collections.singletonMap("value", Double.NaN)));
        assertEquals(0, library.executeCalls.get());
    }

    @Test
    void closeIsIdempotentAndPreventsFutureCalls() {
        NativeClient client = new NativeClient(new FakeLibrary(completed("describe", "{}")));

        client.close();
        client.close();

        assertTrue(client.isClosed());
        assertThrows(ClosedClientException.class, client::describe);
    }

    @Test
    void sharedClientSupportsConcurrentCalls() throws Exception {
        int count = 32;
        FakeLibrary library = new FakeLibrary(completed("describe", "{}"));
        NativeClient client = new NativeClient(library);
        ExecutorService executor = Executors.newFixedThreadPool(count);
        CountDownLatch ready = new CountDownLatch(count);
        CountDownLatch start = new CountDownLatch(1);
        CountDownLatch done = new CountDownLatch(count);
        try {
            for (int index = 0; index < count; index += 1) {
                executor.execute(() -> {
                    ready.countDown();
                    try {
                        start.await();
                        client.describe();
                    } catch (InterruptedException exception) {
                        Thread.currentThread().interrupt();
                    } finally {
                        done.countDown();
                    }
                });
            }
            assertTrue(ready.await(10, TimeUnit.SECONDS));
            start.countDown();
            assertTrue(done.await(10, TimeUnit.SECONDS));
        } finally {
            executor.shutdownNow();
        }
        assertEquals(count, library.executeCalls.get());
        assertEquals(count, library.freeCalls.get());
    }

    @Test
    void requiresAnAbsoluteExistingLibraryPath() {
        assertThrows(NativeLoadException.class,
                () -> NativeClient.load(java.nio.file.Paths.get("relative-library")));
    }

    @Test
    void rejectsAbiVersionMismatchBeforeExecution() {
        FakeLibrary library = new FakeLibrary(completed("describe", "{}"), 2, null);

        AbiMismatchException error = assertThrows(
                AbiMismatchException.class, () -> new NativeClient(library));
        assertEquals(NativeClient.NATIVE_ABI_VERSION, error.getExpectedVersion());
        assertEquals(2L, error.getActualVersion());
        assertEquals(0, library.executeCalls.get());
    }

    private static byte[] completed(String operation, String result) {
        return ("{\"interop_protocol_version\":\"1.0.0\",\"operation\":\""
                + operation + "\",\"status\":\"completed\",\"result\":"
                + result + "}").getBytes(StandardCharsets.UTF_8);
    }

    private static final class FakeLibrary implements InteropLibrary {
        private final byte[] response;
        private final AtomicInteger executeCalls = new AtomicInteger();
        private final AtomicInteger freeCalls = new AtomicInteger();
        private volatile OwnedBytes executedDescriptor;
        private volatile OwnedBytes freedDescriptor;
        private final ThreadLocal<Memory> allocations = new ThreadLocal<>();
        private final int abiVersion;
        private final Long reportedLength;

        private FakeLibrary(byte[] response) {
            this(response, 1, null);
        }

        private FakeLibrary(byte[] response, long reportedLength) {
            this(response, 1, Long.valueOf(reportedLength));
        }

        private FakeLibrary(byte[] response, int abiVersion, Long reportedLength) {
            this.response = response.clone();
            this.abiVersion = abiVersion;
            this.reportedLength = reportedLength;
        }

        @Override
        public int strling_interop_abi_version_v1() {
            return abiVersion;
        }

        @Override
        public int strling_interop_execute_v1(
                Pointer input, SizeT inputLength, OwnedBytes output) {
            executeCalls.incrementAndGet();
            Memory allocation = new Memory(response.length);
            allocation.write(0L, response, 0, response.length);
            allocations.set(allocation);
            output.data = allocation;
            output.len = new SizeT(reportedLength == null ? response.length : reportedLength);
            output.write();
            executedDescriptor = output;
            return 0;
        }

        @Override
        public int strling_interop_owned_bytes_free_v1(OwnedBytes output) {
            freeCalls.incrementAndGet();
            freedDescriptor = output;
            allocations.remove();
            output.data = Pointer.NULL;
            output.len = new SizeT();
            output.write();
            return 0;
        }
    }
}
