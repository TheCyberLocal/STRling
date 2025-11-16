# STRling Ruby Binding

Next-generation string pattern DSL & compiler for Ruby.

## Status

**Version:** 3.0.0-alpha

This is the Ruby binding for STRling. Currently in development.

### What's Implemented

- ✅ Core AST Node definitions (`Strling::Core::*`)
  - Alt, Seq, Lit, Dot, Anchor
  - CharClass with ClassLiteral, ClassRange, ClassEscape
  - Quant, Group, Backref, Look
  - Flags container

- ✅ Intermediate Representation (IR) nodes (`Strling::Core::IR*`)
  - IRAlt, IRSeq, IRLit, IRDot, IRAnchor
  - IRCharClass with IRClassLiteral, IRClassRange, IRClassEscape
  - IRQuant, IRGroup, IRBackref, IRLook

- ✅ Error handling (`Strling::Core::STRlingParseError`)
  - Position tracking
  - Formatted error messages with hints
  - LSP Diagnostic support

### Coming Soon

- Parser implementation
- Compiler implementation
- Validator implementation
- RSpec test suite
- Simply API (fluent pattern building interface)
- CLI tools
- Complete documentation

## Installation

This gem is not yet published. To use it in development:

```bash
cd bindings/ruby
bundle install
```

## Usage

```ruby
require 'strling'

# Currently only core data structures are available
# Full parser and compiler API coming in future releases
```

## Development

Run tests (when implemented):

```bash
bundle exec rake spec
```

## License

MIT License - see LICENSE file in the repository root.
