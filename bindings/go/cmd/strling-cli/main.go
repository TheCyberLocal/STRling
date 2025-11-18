// STRling CLI Server - JSON-RPC Interface for Parser Diagnostics
//
// This module provides a command-line interface for obtaining structured
// diagnostics from the STRling parser. It serves as the binding-agnostic
// communication layer between the LSP server and the Go core logic.
//
// The CLI emits JSON-formatted diagnostics that can be consumed by any LSP
// implementation, ensuring compatibility with the future Rust core and
// multi-language roadmap.
//
// Usage:
//     strling-cli --diagnostics <filepath>
//     strling-cli --diagnostics-stdin
//
// Output Format:
//     {
//         "success": true/false,
//         "diagnostics": [
//             {
//                 "range": {
//                     "start": {"line": 0, "character": 5},
//                     "end": {"line": 0, "character": 6}
//                 },
//                 "severity": 1,
//                 "message": "Error message with hint",
//                 "source": "STRling",
//                 "code": "error_code"
//             }
//         ],
//         "version": "1.0.0"
//     }
package main

import (
	"encoding/json"
	"flag"
	"fmt"
	"io"
	"os"
	
	"github.com/thecyberlocal/strling/bindings/go/core"
)

// DiagnosticResult represents the JSON output structure.
type DiagnosticResult struct {
	Success     bool                   `json:"success"`
	Diagnostics []core.LSPDiagnostic   `json:"diagnostics"`
	Version     string                 `json:"version"`
}

// VersionInfo represents version information output.
type VersionInfo struct {
	Version  string `json:"version"`
	Name     string `json:"name"`
	Protocol string `json:"protocol"`
}

// diagnoseFile analyzes a STRling pattern file and returns structured diagnostics.
func diagnoseFile(filepath string) DiagnosticResult {
	data, err := os.ReadFile(filepath)
	if err != nil {
		return DiagnosticResult{
			Success: false,
			Diagnostics: []core.LSPDiagnostic{
				{
					Range: core.LSPRange{
						Start: core.LSPPosition{Line: 0, Character: 0},
						End:   core.LSPPosition{Line: 0, Character: 0},
					},
					Severity: 1,
					Message:  fmt.Sprintf("Error reading file: %v", err),
					Source:   "STRling",
					Code:     "read_error",
				},
			},
			Version: "1.0.0",
		}
	}
	
	return diagnoseContent(string(data))
}

// diagnoseContent analyzes STRling pattern content and returns structured diagnostics.
func diagnoseContent(content string) DiagnosticResult {
	_, _, err := core.Parse(content)
	
	if err != nil {
		// Convert parse error to LSP diagnostic
		if parseErr, ok := err.(*core.STRlingParseError); ok {
			return DiagnosticResult{
				Success: false,
				Diagnostics: []core.LSPDiagnostic{
					parseErr.ToLSPDiagnostic(),
				},
				Version: "1.0.0",
			}
		}
		
		// Handle unexpected errors
		return DiagnosticResult{
			Success: false,
			Diagnostics: []core.LSPDiagnostic{
				{
					Range: core.LSPRange{
						Start: core.LSPPosition{Line: 0, Character: 0},
						End:   core.LSPPosition{Line: 0, Character: 0},
					},
					Severity: 1,
					Message:  fmt.Sprintf("Unexpected error: %v", err),
					Source:   "STRling",
					Code:     "internal_error",
				},
			},
			Version: "1.0.0",
		}
	}
	
	// Success - no diagnostics
	return DiagnosticResult{
		Success:     true,
		Diagnostics: []core.LSPDiagnostic{},
		Version:     "1.0.0",
	}
}

func main() {
	diagnosticsFile := flag.String("diagnostics", "", "Analyze a STRling pattern file and output JSON diagnostics")
	diagnosticsStdin := flag.Bool("diagnostics-stdin", false, "Read pattern from stdin and output JSON diagnostics")
	versionFlag := flag.Bool("version", false, "Print version information")
	
	flag.Parse()
	
	if *versionFlag {
		versionInfo := VersionInfo{
			Version:  "1.0.0",
			Name:     "STRling CLI Server",
			Protocol: "json-rpc",
		}
		output, _ := json.MarshalIndent(versionInfo, "", "  ")
		fmt.Println(string(output))
		os.Exit(0)
	}
	
	var result DiagnosticResult
	
	if *diagnosticsFile != "" {
		result = diagnoseFile(*diagnosticsFile)
	} else if *diagnosticsStdin {
		content, err := io.ReadAll(os.Stdin)
		if err != nil {
			result = DiagnosticResult{
				Success: false,
				Diagnostics: []core.LSPDiagnostic{
					{
						Range: core.LSPRange{
							Start: core.LSPPosition{Line: 0, Character: 0},
							End:   core.LSPPosition{Line: 0, Character: 0},
						},
						Severity: 1,
						Message:  fmt.Sprintf("Error reading stdin: %v", err),
						Source:   "STRling",
						Code:     "stdin_error",
					},
				},
				Version: "1.0.0",
			}
		} else {
			result = diagnoseContent(string(content))
		}
	} else {
		flag.Usage()
		os.Exit(1)
	}
	
	// Output JSON result
	output, _ := json.MarshalIndent(result, "", "  ")
	fmt.Println(string(output))
	
	// Exit with appropriate code
	if result.Success {
		os.Exit(0)
	} else {
		os.Exit(1)
	}
}
