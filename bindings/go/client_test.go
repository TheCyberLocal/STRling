package strling

import (
	"encoding/json"
	"errors"
	"os"
	"path/filepath"
	"reflect"
	"sync"
	"testing"
)

func TestSourceCompileRequestIsCanonicalData(t *testing.T) {
	request := SourceCompileRequest("'hello'", nil)
	if request["contract_version"] != "1.0.0" {
		t.Fatal("unexpected contract version")
	}
	document := request["input"].(map[string]any)["document"].(map[string]any)
	if document["source_id"] != "src:go.adapter" {
		t.Fatal("unexpected source identity")
	}
}

func TestStdlibHelperRecordsIdentityWithoutSemantics(t *testing.T) {
	step := Email("root")
	want := SimplyStep{
		"step_id":   "root",
		"operation": "stdlib_helper",
		"arguments": map[string]any{
			"helper_id":  "stdlib.email",
			"parameters": map[string]any{},
		},
	}
	if !reflect.DeepEqual(step, want) {
		t.Fatalf("unexpected helper step: %#v", step)
	}
}

func TestRelativeNativePathFailsClosed(t *testing.T) {
	_, err := LoadNative(filepath.Join("relative", "strling"))
	var nativeErr *NativeError
	if !errors.As(err, &nativeErr) || nativeErr.Kind != ErrorLoad {
		t.Fatalf("expected native load error, got %v", err)
	}
}

func TestStrictResponseRejectsDuplicateProperties(t *testing.T) {
	_, err := decodeInteropResponse([]byte(`{"interop_protocol_version":"1.0.0","status":"completed","result":{},"result":{}}`))
	if err == nil {
		t.Fatal("duplicate response property was accepted")
	}
}

func TestStrictResponseRejectsInvalidUTF8(t *testing.T) {
	_, err := decodeInteropResponse([]byte{'{', '"', 'x', '"', ':', '"', 0xff, '"', '}'})
	if err == nil {
		t.Fatal("invalid UTF-8 response was accepted")
	}
}

func TestNativeAdapterCanonicalOperationsAndLifecycle(t *testing.T) {
	libraryPath := os.Getenv("STRLING_NATIVE_LIBRARY")
	if libraryPath == "" {
		t.Skip("STRLING_NATIVE_LIBRARY is required for governed integration execution")
	}
	client, err := LoadNative(libraryPath)
	if err != nil {
		t.Fatal(err)
	}

	describe, err := client.Describe()
	if err != nil {
		t.Fatal(err)
	}
	compileRequest := SourceCompileRequest("literal \"héllo\x00世界\"", &SourceOptions{
		SourceID: "src:adapter.parity",
	})
	compile, err := client.Compile(compileRequest, nil)
	if err != nil {
		t.Fatal(err)
	}
	targetProfile := readTargetProfile(t)
	inspected, err := client.InspectTargetProfile(targetProfile)
	if err != nil {
		t.Fatal(err)
	}
	builder := SimplyBuilderRequest([]SimplyStep{Email("parity-root")}, "parity-root")
	builder["identity_namespace"] = "adapter-parity"
	simply, err := client.SimplyCompile(builder, nil)
	if err != nil {
		t.Fatal(err)
	}

	var wait sync.WaitGroup
	errorsFound := make(chan error, 32)
	for index := 0; index < cap(errorsFound); index++ {
		wait.Add(1)
		go func() {
			defer wait.Done()
			_, callErr := client.Describe()
			if callErr != nil {
				errorsFound <- callErr
			}
		}()
	}
	wait.Wait()
	close(errorsFound)
	for callErr := range errorsFound {
		t.Errorf("concurrent describe failed: %v", callErr)
	}

	writeAdapterEvidence(t, map[string]any{
		"describe":       describe,
		"compile":        compile,
		"target_profile": inspected,
		"simply":         simply,
	})
	if err := client.Close(); err != nil {
		t.Fatal(err)
	}
	if err := client.Close(); err != nil {
		t.Fatal(err)
	}
	_, err = client.Describe()
	var nativeErr *NativeError
	if !errors.As(err, &nativeErr) || nativeErr.Kind != ErrorClosed {
		t.Fatalf("expected closed-client error, got %v", err)
	}
}

func TestNativeReleaseProbeRequiresSameDescriptorFree(t *testing.T) {
	libraryPath := os.Getenv("STRLING_GDS_RELEASE_PROBE")
	if libraryPath == "" {
		t.Skip("STRLING_GDS_RELEASE_PROBE is required for governed lifecycle execution")
	}
	client, err := LoadNative(libraryPath)
	if err != nil {
		t.Fatal(err)
	}
	defer client.Close()
	for index := 0; index < 2; index++ {
		if _, err := client.Describe(); err != nil {
			t.Fatalf("release probe call %d failed: %v", index+1, err)
		}
	}
}

func TestNativeABIMismatchFailsBeforeExecution(t *testing.T) {
	libraryPath := os.Getenv("STRLING_GDS_ABI_PROBE")
	if libraryPath == "" {
		t.Skip("STRLING_GDS_ABI_PROBE is required for governed ABI execution")
	}
	_, err := LoadNative(libraryPath)
	var nativeErr *NativeError
	if !errors.As(err, &nativeErr) || nativeErr.Kind != ErrorABI || nativeErr.Status != 2 {
		t.Fatalf("expected ABI version 2 refusal, got %v", err)
	}
}

func TestNativeOversizedResponseFailsClosed(t *testing.T) {
	libraryPath := os.Getenv("STRLING_GDS_OVERSIZE_PROBE")
	if libraryPath == "" {
		t.Skip("STRLING_GDS_OVERSIZE_PROBE is required for governed bounds execution")
	}
	client, err := LoadNative(libraryPath)
	if err != nil {
		t.Fatal(err)
	}
	defer client.Close()
	_, err = client.Describe()
	var nativeErr *NativeError
	if !errors.As(err, &nativeErr) || nativeErr.Kind != ErrorTransport {
		t.Fatalf("expected oversized-response transport refusal, got %v", err)
	}
}

func TestNativeDuplicateResponseFailsClosed(t *testing.T) {
	assertProbeTransportFailure(t, "STRLING_GDS_DUPLICATE_PROBE")
}

func TestNativeInvalidUTF8ResponseFailsClosed(t *testing.T) {
	assertProbeTransportFailure(t, "STRLING_GDS_INVALID_UTF8_PROBE")
}

func assertProbeTransportFailure(t *testing.T, environmentName string) {
	t.Helper()
	libraryPath := os.Getenv(environmentName)
	if libraryPath == "" {
		t.Skip(environmentName + " is required for governed transport execution")
	}
	client, err := LoadNative(libraryPath)
	if err != nil {
		t.Fatal(err)
	}
	defer client.Close()
	_, err = client.Describe()
	var nativeErr *NativeError
	if !errors.As(err, &nativeErr) || nativeErr.Kind != ErrorTransport {
		t.Fatalf("expected transport refusal from %s, got %v", environmentName, err)
	}
}

func readTargetProfile(t *testing.T) map[string]any {
	t.Helper()
	encoded, err := os.ReadFile(filepath.Join("..", "..", "spec", "targets", "profiles", "pcre2-10.43.json"))
	if err != nil {
		t.Fatal(err)
	}
	var value map[string]any
	if err := json.Unmarshal(encoded, &value); err != nil {
		t.Fatal(err)
	}
	return value
}

func writeAdapterEvidence(t *testing.T, observations map[string]any) {
	t.Helper()
	root := os.Getenv("STRLING_GDS_EVIDENCE_DIR")
	if root == "" {
		return
	}
	directory := filepath.Join(root, "go")
	if err := os.MkdirAll(directory, 0o755); err != nil {
		t.Fatal(err)
	}
	for operation, observation := range observations {
		encoded, err := json.Marshal(observation)
		if err != nil {
			t.Fatal(err)
		}
		if err := os.WriteFile(filepath.Join(directory, operation+".json"), encoded, 0o644); err != nil {
			t.Fatal(err)
		}
	}
}
