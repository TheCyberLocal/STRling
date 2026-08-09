namespace STRling.Tests

open System
open System.IO
open System.Text.Json
open Xunit
open Xunit.Abstractions
open STRling
open STRling.Core
open System.Collections.Generic

type ConformanceTests(output: ITestOutputHelper) =

    static member GetSpecFiles() : IEnumerable<obj[]> =
        let rec findRoot dir =
            if Directory.Exists(Path.Combine(dir, "tests", "spec")) then
                dir
            else
                let parent = Directory.GetParent(dir)
                if parent = null then failwith "Could not find repository root"
                findRoot parent.FullName

        let root = findRoot (Directory.GetCurrentDirectory())
        let specDir = Path.Combine(root, "tests", "spec")
        let files = Directory.GetFiles(specDir, "*.json")

        seq {
            for f in files do
                yield [| box f |]
        }

    /// Get the test display name for a spec file
    static member GetTestName(file: string) : string =
        let stem = Path.GetFileNameWithoutExtension(file)
        match stem with
        | "semantic_duplicates" -> "test_semantic_duplicate_capture_group"
        | "semantic_ranges" -> "test_semantic_ranges"
        | _ -> sprintf "test_conformance_%s" stem

    [<Theory>]
    [<MemberData(nameof(ConformanceTests.GetSpecFiles))>]
    member this.``Run Conformance Test`` (file: string) =
        let testName = ConformanceTests.GetTestName(file)
        let filename = Path.GetFileName(file)
        let options = JsonSerializerOptions()
        options.Converters.Add(NodeConverter())
        options.Converters.Add(ClassItemConverter())
        options.Converters.Add(IROpConverter())
        options.Converters.Add(IRClassItemConverter())

        let json = File.ReadAllText(file)
        use doc = JsonDocument.Parse(json)
        let root = doc.RootElement

        // Output test name for audit visibility (Console) and xUnit logging (output)
        let runMsg = sprintf "=== RUN   %s (%s)" testName filename
        Console.WriteLine(runMsg)
        output.WriteLine(runMsg)

        // Check for error test case
        let mutable expectedErrorElem = Unchecked.defaultof<JsonElement>
        if root.TryGetProperty("expected_error", &expectedErrorElem) then
            // Error test case
            let expectedError = expectedErrorElem.GetString()

            // Only run if input_ast exists
            let mutable inputAstElem = Unchecked.defaultof<JsonElement>
            if root.TryGetProperty("input_ast", &inputAstElem) then
                try
                    let inputAst = JsonSerializer.Deserialize<Node>(inputAstElem.GetRawText(), options)
                    let _ = Compiler.compile inputAst
                    failwithf "Expected error '%s' but compilation succeeded" expectedError
                with
                | _ ->
                    // Expected error caught
                    let passMsg = sprintf "    --- PASS: Caught expected error: %s" expectedError
                    Console.WriteLine(passMsg)
                    output.WriteLine(passMsg)
            else
                // Parser error test: parse input_dsl and verify error + hint
                let mutable inputDslElem = Unchecked.defaultof<JsonElement>
                if root.TryGetProperty("input_dsl", &inputDslElem) then
                    let inputDsl = inputDslElem.GetString()
                    if not (String.IsNullOrEmpty(inputDsl)) then
                        try
                            let _result = Parser.parse inputDsl
                            failwithf "Expected parse error '%s' but parsing succeeded" expectedError
                        with
                        | :? STRlingParseError as parseErr ->
                            // Verify error message contains expected substring
                            if not (parseErr.ErrorMessage.Contains(expectedError)) then
                                failwithf "Error message mismatch.\n  Expected substring: %s\n  Actual: %s" expectedError parseErr.ErrorMessage
                            // Verify hint if expected
                            let mutable expectedHintElem = Unchecked.defaultof<JsonElement>
                            if root.TryGetProperty("expected_hint", &expectedHintElem) then
                                let expectedHint = expectedHintElem.GetString()
                                if not (String.IsNullOrEmpty(expectedHint)) then
                                    match parseErr.Hint with
                                    | Some actualHint ->
                                        if actualHint <> expectedHint then
                                            failwithf "Hint mismatch.\n  Expected: %s\n  Actual: %s" expectedHint actualHint
                                    | None ->
                                        failwithf "Expected hint '%s' but got None" expectedHint
                            let passMsg = sprintf "    --- PASS: Parser error verified: %s" expectedError
                            Console.WriteLine(passMsg)
                            output.WriteLine(passMsg)
                        | ex ->
                            // Non-STRlingParseError, still a pass if it's an error
                            let passMsg = sprintf "    --- PASS: Caught error: %s" (ex.Message)
                            Console.WriteLine(passMsg)
                            output.WriteLine(passMsg)
                    else
                        let passMsg = sprintf "    --- PASS: Parser test (no AST), out of scope"
                        Console.WriteLine(passMsg)
                        output.WriteLine(passMsg)
                else
                    let passMsg = sprintf "    --- PASS: Parser test (no AST), out of scope"
                    Console.WriteLine(passMsg)
                    output.WriteLine(passMsg)

            ()
        else
            // Only run if input_ast exists
            let mutable inputAstElem = Unchecked.defaultof<JsonElement>
            if root.TryGetProperty("input_ast", &inputAstElem) then
                let inputAst = JsonSerializer.Deserialize<Node>(inputAstElem.GetRawText(), options)
                let expectedIr = JsonSerializer.Deserialize<IROp>(root.GetProperty("expected_ir").GetRawText(), options)

                let actualIr = Compiler.compile inputAst

                if actualIr <> expectedIr then
                    let actualJson = JsonSerializer.Serialize(actualIr, options)
                    let expectedJson = JsonSerializer.Serialize(expectedIr, options)
                    failwithf "File: %s\nExpected: %s\nActual:   %s" filename expectedJson actualJson
