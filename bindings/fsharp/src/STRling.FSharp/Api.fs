namespace STRling.FSharp

module Api =
    open System
    open Strling

    /// A light wrapper type alias for the underlying C# Parser.
    type ParserHandle = Parser

    /// Create a new Parser instance from the C# binding.
    let createParser () : ParserHandle =
        Parser()

    /// Parse input using the provided parser.
    ///
    /// NOTE: The C# `Parser` implementation is intentionally minimal in this repository;
    /// this wrapper returns an informative `Error` until the C# parser exposes a parsing API.
    let parse (parser: ParserHandle) (input: string) : Result<string, string> =
        Error "parse not implemented in C# Parser"
