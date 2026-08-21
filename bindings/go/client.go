package strling

import (
	"bytes"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"os"
	"path/filepath"
	"sync"
	"unicode/utf8"
)

const (
	InteropProtocolVersion   = "1.0.0"
	NativeABIVersion         = 1
	MaxInteropRequestBytes   = 10_485_760
	MaxInteropResponseBytes  = 33_554_432
	defaultSpecification     = "1.0-draft.1"
	defaultSemanticFrontend  = "semantic_strling"
	defaultSourceMediaType   = "text/strling"
	defaultSourceIdentity    = "src:go.adapter"
	defaultSimplyNamespace   = "go.adapter"
	defaultSimplyProtocol    = "1.1.0"
	defaultContractVersion   = "1.0.0"
)

var ErrCgoUnavailable = errors.New("strling native adapter requires cgo")

type ErrorKind string

const (
	ErrorLoad      ErrorKind = "native_load"
	ErrorABI       ErrorKind = "native_abi"
	ErrorClosed    ErrorKind = "closed_client"
	ErrorTransport ErrorKind = "transport"
)

type NativeError struct {
	Kind   ErrorKind
	Status uint32
	Detail string
}

func (e *NativeError) Error() string {
	if e.Status != 0 {
		return fmt.Sprintf("%s: %s (status %d)", e.Kind, e.Detail, e.Status)
	}
	return fmt.Sprintf("%s: %s", e.Kind, e.Detail)
}

type ProtocolError struct {
	Code      string
	Path      string
	Operation string
}

func (e *ProtocolError) Error() string {
	return fmt.Sprintf("%s at %s", e.Code, e.Path)
}

type NativeClient struct {
	mu          sync.Mutex
	condition   *sync.Cond
	state       *nativeState
	libraryPath string
	activeCalls int
	closed      bool
}

func LoadNative(libraryPath string) (*NativeClient, error) {
	if libraryPath == "" || !filepath.IsAbs(libraryPath) {
		return nil, &NativeError{Kind: ErrorLoad, Detail: "native STRling library path must be absolute"}
	}
	normalized := filepath.Clean(libraryPath)
	info, err := os.Stat(normalized)
	if err != nil || !info.Mode().IsRegular() {
		return nil, &NativeError{Kind: ErrorLoad, Detail: "native STRling library not found: " + normalized}
	}
	state, err := loadNativeState(normalized)
	if err != nil {
		return nil, err
	}
	client := &NativeClient{state: state, libraryPath: normalized}
	client.condition = sync.NewCond(&client.mu)
	return client, nil
}

func (c *NativeClient) LibraryPath() string { return c.libraryPath }

func (c *NativeClient) IsClosed() bool {
	c.mu.Lock()
	defer c.mu.Unlock()
	return c.closed
}

func (c *NativeClient) Execute(request any) (map[string]any, error) {
	encoded, err := json.Marshal(request)
	if err != nil {
		return nil, &NativeError{Kind: ErrorTransport, Detail: "interop request is not strict JSON: " + err.Error()}
	}
	if len(encoded) > MaxInteropRequestBytes {
		return nil, &NativeError{Kind: ErrorTransport, Detail: fmt.Sprintf("interop request exceeds %d bytes", MaxInteropRequestBytes)}
	}
	state, err := c.beginCall()
	if err != nil {
		return nil, err
	}
	raw, executeErr := state.execute(encoded)
	c.endCall()
	if executeErr != nil {
		return nil, executeErr
	}
	return decodeInteropResponse(raw)
}

func (c *NativeClient) Describe() (any, error) {
	return c.completedResult(envelope("describe", map[string]any{}))
}

func (c *NativeClient) Compile(compileRequest map[string]any, targetProfile map[string]any) (any, error) {
	payload := map[string]any{"compile_request": compileRequest}
	if targetProfile != nil {
		payload["target_profile"] = targetProfile
	}
	return c.completedResult(envelope("compile", payload))
}

func (c *NativeClient) InspectTargetProfile(targetProfile map[string]any) (any, error) {
	return c.completedResult(envelope("target_profile.inspect", map[string]any{"target_profile": targetProfile}))
}

func (c *NativeClient) SimplyCompile(builderRequest map[string]any, targetProfile map[string]any) (any, error) {
	payload := map[string]any{"builder_request": builderRequest}
	if targetProfile != nil {
		payload["target_profile"] = targetProfile
	}
	return c.completedResult(envelope("simply.compile", payload))
}

func (c *NativeClient) Close() error {
	c.mu.Lock()
	if c.closed {
		c.mu.Unlock()
		return nil
	}
	c.closed = true
	for c.activeCalls != 0 {
		c.condition.Wait()
	}
	state := c.state
	c.state = nil
	c.mu.Unlock()
	return state.close()
}

func (c *NativeClient) beginCall() (*nativeState, error) {
	c.mu.Lock()
	defer c.mu.Unlock()
	if c.closed || c.state == nil {
		return nil, &NativeError{Kind: ErrorClosed, Detail: "native STRling client is closed"}
	}
	c.activeCalls++
	return c.state, nil
}

func (c *NativeClient) endCall() {
	c.mu.Lock()
	c.activeCalls--
	if c.activeCalls == 0 {
		c.condition.Broadcast()
	}
	c.mu.Unlock()
}

func (c *NativeClient) completedResult(request map[string]any) (any, error) {
	response, err := c.Execute(request)
	if err != nil {
		return nil, err
	}
	if response["status"] == "error" {
		body := response["error"].(map[string]any)
		operation, _ := response["operation"].(string)
		return nil, &ProtocolError{Code: body["code"].(string), Path: body["path"].(string), Operation: operation}
	}
	return response["result"], nil
}

func envelope(operation string, payload map[string]any) map[string]any {
	return map[string]any{
		"interop_protocol_version": InteropProtocolVersion,
		"operation":                operation,
		"payload":                  payload,
	}
}

func decodeInteropResponse(raw []byte) (map[string]any, error) {
	if len(raw) == 0 || len(raw) > MaxInteropResponseBytes {
		return nil, &NativeError{Kind: ErrorTransport, Detail: "native STRling returned an empty or oversized response"}
	}
	if !utf8.Valid(raw) {
		return nil, &NativeError{Kind: ErrorTransport, Detail: "native STRling response is not strict UTF-8"}
	}
	decoder := json.NewDecoder(bytes.NewReader(raw))
	decoder.UseNumber()
	value, err := decodeJSONValue(decoder, "$")
	if err != nil {
		return nil, &NativeError{Kind: ErrorTransport, Detail: "native STRling response is not strict JSON: " + err.Error()}
	}
	if _, err := decoder.Token(); !errors.Is(err, io.EOF) {
		return nil, &NativeError{Kind: ErrorTransport, Detail: "native STRling response has trailing JSON content"}
	}
	response, ok := value.(map[string]any)
	if !ok || response["interop_protocol_version"] != InteropProtocolVersion {
		return nil, &NativeError{Kind: ErrorTransport, Detail: "interop response has an unsupported version"}
	}
	status, ok := response["status"].(string)
	if !ok || (status != "completed" && status != "error") {
		return nil, &NativeError{Kind: ErrorTransport, Detail: "interop response has an unsupported status"}
	}
	if status == "completed" {
		if _, exists := response["result"]; !exists {
			return nil, &NativeError{Kind: ErrorTransport, Detail: "completed interop response has no result"}
		}
		return response, nil
	}
	body, ok := response["error"].(map[string]any)
	if !ok {
		return nil, &NativeError{Kind: ErrorTransport, Detail: "failed interop response has no error object"}
	}
	if _, ok := body["code"].(string); !ok {
		return nil, &NativeError{Kind: ErrorTransport, Detail: "failed interop response has no stable code"}
	}
	if _, ok := body["path"].(string); !ok {
		return nil, &NativeError{Kind: ErrorTransport, Detail: "failed interop response has no stable path"}
	}
	return response, nil
}

func decodeJSONValue(decoder *json.Decoder, path string) (any, error) {
	token, err := decoder.Token()
	if err != nil {
		return nil, err
	}
	delimiter, isDelimiter := token.(json.Delim)
	if !isDelimiter {
		return token, nil
	}
	switch delimiter {
	case '{':
		object := map[string]any{}
		for decoder.More() {
			nameToken, err := decoder.Token()
			if err != nil {
				return nil, err
			}
			name, ok := nameToken.(string)
			if !ok {
				return nil, fmt.Errorf("object name at %s is not a string", path)
			}
			if _, exists := object[name]; exists {
				return nil, fmt.Errorf("duplicate property at %s.%s", path, name)
			}
			value, err := decodeJSONValue(decoder, path+"."+name)
			if err != nil {
				return nil, err
			}
			object[name] = value
		}
		_, err = decoder.Token()
		return object, err
	case '[':
		array := []any{}
		for index := 0; decoder.More(); index++ {
			value, err := decodeJSONValue(decoder, fmt.Sprintf("%s[%d]", path, index))
			if err != nil {
				return nil, err
			}
			array = append(array, value)
		}
		_, err = decoder.Token()
		return array, err
	default:
		return nil, fmt.Errorf("unexpected delimiter %q at %s", delimiter, path)
	}
}
