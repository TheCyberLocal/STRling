# STRling for PHP

[![PHP Version](https://img.shields.io/badge/php-%3E%3D8.1-8892BF.svg)](https://www.php.net/)

A next-generation production-grade syntax for writing powerful regular expressions with an object-oriented approach and instructional error handling.

## Overview

STRling for PHP provides a clean, readable, and powerful interface for working with regular expressions. This binding is designed to integrate seamlessly with modern PHP applications (PHP 8.1+) and follows PSR-4 autoloading standards.

## Installation

```bash
composer require strling/strling
```

## Project Structure

```
bindings/php/
├── src/
│   ├── STRling.php           # Main public API
│   └── Core/
│       ├── Nodes.php          # AST node definitions
│       ├── IR.php             # Intermediate representation
│       └── Errors.php         # Error handling
├── tests/
│   └── STRlingTest.php        # PHPUnit test suite
├── docs/                       # Documentation
├── composer.json               # Composer package configuration
└── phpunit.xml                # PHPUnit configuration
```

## Requirements

- PHP 8.1 or higher
- Composer for dependency management

## Development

### Installing Dependencies

```bash
composer install
```

### Running Tests

```bash
vendor/bin/phpunit
```

Or with verbose output:

```bash
vendor/bin/phpunit --testdox
```

## Architecture

This PHP binding is structured in three main layers:

1. **AST (Abstract Syntax Tree)** - Defined in `src/Core/Nodes.php`, represents the parsed structure of STRling patterns
2. **IR (Intermediate Representation)** - Defined in `src/Core/IR.php`, provides a language-agnostic representation
3. **Error Handling** - Defined in `src/Core/Errors.php`, provides rich, instructional error messages

## Current Status

**Task 1 Complete**: Architecture, scaffolding, and core data structures are implemented.

- ✅ Directory structure created
- ✅ Composer package configured with PSR-4 autoloading
- ✅ Core data structures ported from Python
- ✅ Basic test infrastructure set up

**Coming in Task 2**: Parser, Compiler, and Validator implementation with functional tests.

## Documentation

For detailed documentation on STRling syntax and usage, see the [main documentation](../../docs/index.md).

## License

MIT License - See the main repository LICENSE file for details.

## Contributing

Contributions are welcome! Please see the [contribution guidelines](../../docs/CONTRIBUTING.md) in the main repository.
