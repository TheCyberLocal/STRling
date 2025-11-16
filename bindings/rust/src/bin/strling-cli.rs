#!/usr/bin/env rust
//! STRling CLI - Command-line interface for STRling parser diagnostics
//!
//! This binary provides a command-line interface for obtaining structured
//! diagnostics from the STRling parser. It serves as the binding-agnostic
//! communication layer between LSP servers and the Rust core logic.
//!
//! The CLI emits JSON-formatted diagnostics compatible with the LSP specification,
//! ensuring compatibility across language bindings.
//!
//! # Usage
//!
//! ```bash
//! strling-cli --diagnostics <filepath>
//! strling-cli --diagnostics-stdin
//! strling-cli --emit pcre2 <filepath>
//! ```
//!
//! # Output Format
//!
//! ```json
//! {
//!     "success": true/false,
//!     "diagnostics": [
//!         {
//!             "range": {
//!                 "start": {"line": 0, "character": 5},
//!                 "end": {"line": 0, "character": 6}
//!             },
//!             "severity": 1,
//!             "message": "Error message with hint",
//!             "source": "STRling",
//!             "code": "error_code"
//!         }
//!     ],
//!     "version": "3.0.0"
//! }
//! ```

use clap::{Parser, Subcommand};
use std::fs;
use std::io::{self, Read};
use std::path::PathBuf;

#[derive(Parser)]
#[command(author, version, about, long_about = None)]
struct Cli {
    #[command(subcommand)]
    command: Option<Commands>,
}

#[derive(Subcommand)]
enum Commands {
    /// Run diagnostics on a file or stdin
    Diagnostics {
        /// Input file path (omit for stdin)
        file: Option<PathBuf>,
        
        /// Read from stdin instead of a file
        #[arg(long)]
        stdin: bool,
    },
    
    /// Emit compiled output in target format
    Emit {
        /// Target format (e.g., pcre2)
        #[arg(long)]
        target: String,
        
        /// Input file path (omit for stdin)
        file: Option<PathBuf>,
        
        /// Read from stdin instead of a file
        #[arg(long)]
        stdin: bool,
    },
}

fn main() {
    let cli = Cli::parse();
    
    match &cli.command {
        Some(Commands::Diagnostics { file, stdin }) => {
            let content = if *stdin || file.is_none() {
                read_stdin()
            } else {
                read_file(file.as_ref().unwrap())
            };
            
            match content {
                Ok(text) => {
                    // TODO: Call parser and generate diagnostics
                    println!("{{");
                    println!("  \"success\": false,");
                    println!("  \"diagnostics\": [],");
                    println!("  \"version\": \"3.0.0\"");
                    println!("}}");
                }
                Err(e) => {
                    eprintln!("Error reading input: {}", e);
                    std::process::exit(1);
                }
            }
        }
        Some(Commands::Emit { target, file, stdin }) => {
            let content = if *stdin || file.is_none() {
                read_stdin()
            } else {
                read_file(file.as_ref().unwrap())
            };
            
            match content {
                Ok(text) => {
                    // TODO: Call parser, compiler, and emitter
                    eprintln!("Emit to {} not yet implemented", target);
                    std::process::exit(1);
                }
                Err(e) => {
                    eprintln!("Error reading input: {}", e);
                    std::process::exit(1);
                }
            }
        }
        None => {
            eprintln!("No command specified. Use --help for usage information.");
            std::process::exit(1);
        }
    }
}

fn read_stdin() -> io::Result<String> {
    let mut buffer = String::new();
    io::stdin().read_to_string(&mut buffer)?;
    Ok(buffer)
}

fn read_file(path: &PathBuf) -> io::Result<String> {
    fs::read_to_string(path)
}
