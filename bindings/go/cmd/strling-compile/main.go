package main

import (
"fmt"
"os"

"github.com/thecyberlocal/strling/bindings/go/core"
"github.com/thecyberlocal/strling/bindings/go/emitters"
)

func main() {
if len(os.Args) < 2 {
fmt.Println("Usage: strling-compile <pattern>")
os.Exit(1)
}

pattern := os.Args[1]

// Parse
flags, ast, err := core.Parse(pattern)
if err != nil {
fmt.Fprintf(os.Stderr, "Parse error: %v\n", err)
os.Exit(1)
}

// Compile
compiler := core.NewCompiler()
ir := compiler.Compile(ast)

// Emit
pcre2Pattern := emitters.Emit(ir, flags)

fmt.Println(pcre2Pattern)
}
