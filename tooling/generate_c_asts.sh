#!/usr/bin/env bash
set -euo pipefail

# Build JS binding (if not already built) and run the AST generator.
ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
JS_DIR="$ROOT_DIR/bindings/javascript"
TOOL_DIR="$ROOT_DIR/tooling/js_to_json_ast"

echo "Building JavaScript binding (if needed)..."
if [ ! -d "$JS_DIR/node_modules" ]; then
  cd "$JS_DIR"
  npm install
else
  echo "node_modules exists; skipping npm install"
fi

cd "$JS_DIR"
npm run build

echo "Running AST generator..."
cd "$TOOL_DIR"
node generate_json_ast.js

echo "Done. Generated artifacts are in $TOOL_DIR/out"
