//! STRling Core Library
//!
//! This is the Rust implementation of the STRling DSL compiler and parser.
//! STRling is a next-generation string pattern DSL designed as a user interface
//! for writing powerful regular expressions with an object-oriented approach
//! and instructional error handling.
//!
//! # Modules
//!
//! - `core`: Core data structures including AST nodes, IR nodes, and error types

pub mod core;

// Re-export commonly used types for convenience
pub use core::errors::STRlingParseError;
pub use core::ir::IROp;
pub use core::nodes::{Flags, Node};
