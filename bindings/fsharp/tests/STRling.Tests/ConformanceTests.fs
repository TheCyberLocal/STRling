namespace STRling.Tests

open System
open System.IO
open System.Text.Json
open Xunit
open STRling
open System.Collections.Generic

type ConformanceTests() =

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

    [<Theory>]
    [<MemberData(nameof(ConformanceTests.GetSpecFiles))>]
    member this.``Run Conformance Test`` (file: string) =
        let options = JsonSerializerOptions()
        options.Converters.Add(NodeConverter())
        options.Converters.Add(ClassItemConverter())
        options.Converters.Add(IROpConverter())
        options.Converters.Add(IRClassItemConverter())
        
        let json = File.ReadAllText(file)
        use doc = JsonDocument.Parse(json)
        let root = doc.RootElement
        
        // Only run if input_ast exists
        let mutable inputAstElem = Unchecked.defaultof<JsonElement>
        if root.TryGetProperty("input_ast", &inputAstElem) then
            let inputAst = JsonSerializer.Deserialize<Node>(inputAstElem.GetRawText(), options)
            let expectedIr = JsonSerializer.Deserialize<IROp>(root.GetProperty("expected_ir").GetRawText(), options)
            
            let actualIr = Compiler.compile inputAst
            
            if actualIr <> expectedIr then
                let actualJson = JsonSerializer.Serialize(actualIr, options)
                let expectedJson = JsonSerializer.Serialize(expectedIr, options)
                failwithf "File: %s\nExpected: %s\nActual:   %s" (Path.GetFileName(file)) expectedJson actualJson
