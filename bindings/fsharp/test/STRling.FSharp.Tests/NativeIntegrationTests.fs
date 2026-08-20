module NativeIntegrationTests

open System
open System.IO
open System.Text.Json
open Xunit
open STRling.FSharp

let private projection () =
    JsonSerializer.SerializeToElement(
        {| requested_outputs = [| "semantic" |]
           compiler_options =
            {| partial_semantics = "forbid"
               diagnostic_policy = {| minimum_severity = "hint" |} |} |})

let private writeEvidence (describe: JsonElement) (compile: JsonElement) (simply: JsonElement) =
    match Environment.GetEnvironmentVariable("STRLING_DOTNET_EVIDENCE_DIR") with
    | null | "" -> ()
    | root ->
        let directory = Directory.CreateDirectory(Path.Combine(root, "fsharp")).FullName
        File.WriteAllText(Path.Combine(directory, "describe.json"), describe.GetRawText())
        File.WriteAllText(Path.Combine(directory, "compile.json"), compile.GetRawText())
        File.WriteAllText(Path.Combine(directory, "simply.json"), simply.GetRawText())

[<Fact>]
let ``FSharp delegates canonical operations through the CSharp client`` () =
    match Environment.GetEnvironmentVariable("STRLING_NATIVE_LIBRARY") with
    | null | "" -> ()
    | nativePath ->
        use client = Api.loadClient (Path.GetFullPath nativePath)
        let compiler = Api.createCompiler client
        let options = { Api.defaultOptions () with SourceId = "src:dotnet.parity" }
        let compile =
            match Api.parse compiler "literal \"hello\"" (Some options) with
            | Succeeded value | Failed value -> value
        let describe = Api.describe compiler
        let request = (Essential.Ip None).BuildRequest(projection (), "dotnet-parity")
        let simply = client.SimplyCompile request
        Assert.Contains(compile.GetProperty("outcome").GetString(), [| "succeeded"; "failed" |])
        Assert.Equal(JsonValueKind.Object, simply.ValueKind)
        writeEvidence describe compile simply
