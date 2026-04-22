package simply

import (
	"encoding/json"
	"os"
	"path/filepath"
	"regexp"
	"testing"
)

type fixtureSet struct {
	Valid           []string `json:"valid"`
	Invalid         []string `json:"invalid"`
	ValidDefault    []string `json:"valid_default"`
	InvalidDefault  []string `json:"invalid_default"`
	ValidV4         []string `json:"valid_v4"`
	InvalidV4       []string `json:"invalid_v4"`
	ValidV6         []string `json:"valid_v6"`
	InvalidV6       []string `json:"invalid_v6"`
}

type patternEntry struct {
	Fixtures fixtureSet `json:"fixtures"`
}

type stdlibSpec struct {
	Patterns map[string]patternEntry `json:"patterns"`
}

func loadSpec(t *testing.T) stdlibSpec {
	t.Helper()
	cwd, err := os.Getwd()
	if err != nil {
		t.Fatalf("getwd: %v", err)
	}
	specPath := filepath.Join(cwd, "..", "..", "..", "spec", "stdlib", "essential_5.json")
	raw, err := os.ReadFile(specPath)
	if err != nil {
		t.Fatalf("read spec: %v", err)
	}
	var spec stdlibSpec
	if err := json.Unmarshal(raw, &spec); err != nil {
		t.Fatalf("unmarshal spec: %v", err)
	}
	return spec
}

func runCases(t *testing.T, name string, regex string, valid, invalid []string) {
	t.Helper()
	re, err := regexp.Compile("^(?:" + regex + ")$")
	if err != nil {
		t.Fatalf("%s: compile: %v", name, err)
	}
	for _, v := range valid {
		if !re.MatchString(v) {
			t.Errorf("%s: expected match for %q", name, v)
		}
	}
	for _, i := range invalid {
		if re.MatchString(i) {
			t.Errorf("%s: expected NO match for %q", name, i)
		}
	}
}

func TestEssential5_Email(t *testing.T) {
	spec := loadSpec(t)
	f := spec.Patterns["email"].Fixtures
	runCases(t, "Email", Email().ToRegex(), f.Valid, f.Invalid)
}

func TestEssential5_URL(t *testing.T) {
	spec := loadSpec(t)
	f := spec.Patterns["url"].Fixtures
	runCases(t, "URL", URL().ToRegex(), f.Valid, f.Invalid)
}

func TestEssential5_UUID(t *testing.T) {
	spec := loadSpec(t)
	f := spec.Patterns["uuid"].Fixtures
	runCases(t, "UUID", UUID().ToRegex(), f.ValidDefault, f.InvalidDefault)
	runCases(t, "UUIDv4", UUID(4).ToRegex(), f.ValidV4, f.InvalidV4)
}

func TestEssential5_IP(t *testing.T) {
	spec := loadSpec(t)
	f := spec.Patterns["ip"].Fixtures
	runCases(t, "IPv4", IP(4).ToRegex(), f.ValidV4, f.InvalidV4)
	runCases(t, "IPv6", IP(6).ToRegex(), f.ValidV6, f.InvalidV6)
	combined := append([]string{}, f.ValidV4...)
	combined = append(combined, f.ValidV6...)
	runCases(t, "IP", IP().ToRegex(), combined, nil)
}

func TestEssential5_DateTime(t *testing.T) {
	spec := loadSpec(t)
	f := spec.Patterns["dateTime"].Fixtures
	runCases(t, "DateTime", DateTime().ToRegex(), f.Valid, f.Invalid)
}
