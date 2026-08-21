//go:build !cgo

package strling

type nativeState struct{}

func loadNativeState(string) (*nativeState, error) { return nil, ErrCgoUnavailable }

func (*nativeState) execute([]byte) ([]byte, error) { return nil, ErrCgoUnavailable }

func (*nativeState) close() error { return nil }
