//! Core module containing fundamental data structures and error types.
//!
//! This module provides:
//! - AST node definitions (`nodes`)
//! - IR node definitions (`ir`)
//! - Error types (`errors`)
//! - Parser (`parser`)
//! - Compiler (`compiler`)
//! - Validator (`validator`)
//! - Hint Engine (`hint_engine`)

pub mod errors;
pub mod ir;
pub mod nodes;
pub mod parser;
pub mod compiler;
pub mod validator;
pub mod hint_engine;
