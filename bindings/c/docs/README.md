# STRling C binding

This directory contains the scaffold for the C binding for STRling. It
includes the public header in `include/`, core data structures in `src/core/`,
and a simple `Makefile` for building a static library.

This binding currently ports only the core, non-executable data structures
(AST nodes, IR nodes, and ParseError). Parser/Compiler logic and tests will
be implemented in follow-up tasks.
