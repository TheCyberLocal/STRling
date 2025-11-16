# README: STRling Pattern Examples

This directory contains example STRling pattern files that demonstrate:

## Files

### valid_patterns.strl
Examples of valid STRling patterns that should parse successfully without errors.
Use this file to verify the LSP server is working correctly - it should show no diagnostics.

### invalid_patterns.strl
Examples of common STRling pattern errors.
**Note**: The parser follows a "first error wins" policy, so only the first error will be reported. This file is useful for understanding error types, but you'll only see diagnostics for the first error.

### Individual Error Examples
The `errors/` subdirectory contains individual files, each demonstrating a single error type.
These are useful for:
- Testing the LSP server with specific error types
- Understanding error messages in isolation
- Verifying error hints are helpful

## Using These Examples

### With the CLI Server
```bash
# Check a file for errors
python -m STRling.cli_server --diagnostics examples/valid_patterns.strl

# Check via stdin
cat examples/valid_patterns.strl | python -m STRling.cli_server --diagnostics-stdin
```

### With the LSP Server
1. Open VS Code (or your editor) with the LSP configured
2. Open any `.strl` file from this directory
3. Observe real-time diagnostics as you edit

### Expected Behavior

#### valid_patterns.strl
- **No errors** - Green checkmark or no diagnostics shown
- Verifies the LSP is working

#### invalid_patterns.strl
- **One error** - "Unterminated group" on line with "(hello world"
- Demonstrates "first error wins" behavior

#### errors/unterminated_group.strl
- **One error** - "Unterminated group"
- Shows instructional hint about adding ')'

## Testing Workflow

1. **Verify LSP is working**: Open `valid_patterns.strl` - should show no errors
2. **Test error detection**: Open any file in `errors/` - should show specific error
3. **Test real-time updates**: Edit a file and fix the error - diagnostic should clear
4. **Test multi-line**: Add patterns across multiple lines - positions should be accurate

## Creating Your Own Tests

Create a new `.strl` file and start typing. The LSP will provide real-time feedback:

```strl
# Start typing a pattern...
(test
```

As soon as you type this, you'll see:
```
Error: Unterminated group

Hint: This group was opened with '(' but never closed. 
Add a matching ')' to close the group.
```

Fix it:
```strl
(test)
```

The error clears instantly!
