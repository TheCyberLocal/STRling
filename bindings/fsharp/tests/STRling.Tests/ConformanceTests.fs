module STRling.Tests.ConformanceTests

open System
open System.IO
open System.Text.Json
open Xunit
open STRling

// Helper to get all json files
let getSpecFiles () =
    // Navigate up from bin/Debug/net8.0/ to root
    // bin/Debug/net8.0/ -> STRling.Tests/ -> tests/ -> fsharp/ -> bindings/ -> STRling/ (root)
    // That is 5 levels up?
    // Let's try to find the root by looking for "tests/spec"
    let rec findRoot dir =
        if Directory.Exists(Path.Combine(dir, "tests", "spec")) then
            dir
        else
            let parent = Directory.GetParent(dir)
            if parent = null then failwith "Could not find repository root"
            findRoot parent.FullName
            
    let root = findRoot (Directory.GetCurrentDirectory())
    let specDir = Path.Combine(root, "tests", "spec")
    Directory.GetFiles(specDir, "*.json")

[<Fact>]
let ``Run Conformance Tests`` () =
    let files = getSpecFiles ()
    let options = JsonSerializerOptions()
    options.Converters.Add(NodeConverter())
    options.Converters.Add(ClassItemConverter())
    options.Converters.Add(IROpConverter())
    options.Converters.Add(IRClassItemConverter())
    
    let mutable passed = 0
    let mutable failed = 0
    let failures = ResizeArray<string>()

    for file in files do
        try
            let json = File.ReadAllText(file)
            use doc = JsonDocument.Parse(json)
            let root = doc.RootElement
            
            // Only run if input_ast exists
            let mutable inputAstElem = Unchecked.defaultof<JsonElement>
            if root.TryGetProperty("input_ast", &inputAstElem) then
                let inputAst = JsonSerializer.Deserialize<Node>(inputAstElem.GetRawText(), options)
                let expectedIr = JsonSerializer.Deserialize<IROp>(root.GetProperty("expected_ir").GetRawText(), options)
                
                let actualIr = Compiler.compile inputAst
                
                if actualIr = expectedIr then
                    passed <- passed + 1
                else
                    let actualJson = JsonSerializer.Serialize(actualIr, options)
                    let expectedJson = JsonSerializer.Serialize(expectedIr, options)
                    failures.Add(sprintf "File: %s\nExpected: %s\nActual:   %s" (Path.GetFileName(file)) expectedJson actualJson)
                    failed <- failed + 1
        with ex ->
            failures.Add(sprintf "File: %s\nException: %s" (Path.GetFileName(file)) ex.Message)
            failed <- failed + 1

    if failed > 0 then
        failwithf "Failed %d tests out of %d.\nFailures:\n%s" failed (passed + failed) (String.Join("\n\n", failures))
    
    // If we get here, all passed
    Assert.True(true)
