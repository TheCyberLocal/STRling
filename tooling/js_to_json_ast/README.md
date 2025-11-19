# JS -> JSON AST generator

This tooling generates JSON AST artifacts for the C binding tests by using
the JavaScript STRling parser as the canonical DSL parser.

Usage (from repository root):

1. Build the JavaScript binding so the parser is compiled to `dist`:

```bash
cd bindings/javascript
npm install
npm run build
```

2. Run the generator:

```bash
cd tooling/js_to_json_ast
node generate_json_ast.js
```

Generated JSON files are written to `tooling/js_to_json_ast/out/`.

Notes:

-   The script looks for `bindings/javascript/dist/STRling/core/parser.js`.
-   If `dist` is missing, build the JS binding first.
