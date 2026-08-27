module CanonicalAdapterTests

open System
open System.IO
open System.Text.Json
open Xunit
open STRling.FSharp

let private compatibilityProjection () =
    let rec findProjection (current: DirectoryInfo) =
        let candidate = Path.Combine(current.FullName, "spec", "stdlib", "essential_5.json")
        if File.Exists(candidate) then
            use document = JsonDocument.Parse(File.ReadAllText(candidate))
            document.RootElement.Clone()
        else
            match current.Parent with
            | null ->
                raise (FileNotFoundException("spec/stdlib/essential_5.json was not found from the test output path"))
            | parent -> findProjection parent
    findProjection (DirectoryInfo(AppContext.BaseDirectory))

[<Fact>]
let ``source request is canonical and targetless by default`` () =
    let request = Api.sourceCompileRequest "literal \"hello\"" None [ "semantic" ]
    Assert.Equal("1.0.0", request.GetProperty("contract_version").GetString())
    let mutable ignored = Unchecked.defaultof<JsonElement>
    Assert.False(request.TryGetProperty("target_profile", &ignored))

[<Fact>]
let ``canonical outcomes are projected without diagnostic synthesis`` () =
    let succeeded = JsonDocument.Parse("{\"outcome\":\"succeeded\",\"diagnostics\":[]}").RootElement.Clone()
    let failed = JsonDocument.Parse("{\"outcome\":\"failed\",\"diagnostics\":[{\"code\":\"X\"}]}").RootElement.Clone()
    match Api.project succeeded, Api.project failed with
    | Succeeded success, Failed rejection ->
        Assert.Equal("succeeded", success.GetProperty("outcome").GetString())
        Assert.Equal("X", rejection.GetProperty("diagnostics").[0].GetProperty("code").GetString())
    | _ -> failwith "canonical outcomes were not preserved"

[<Fact>]
let ``FSharp exposes five lexical helpers and eight exact variants`` () =
    Assert.Equal(5, Essential.HelperIds.Length)
    let variants =
        [ Essential.DateTime(); Essential.Email(); Essential.Ip None; Essential.Ip (Some 4)
          Essential.Ip (Some 6); Essential.Url(); Essential.Uuid None; Essential.Uuid (Some 4) ]
    Assert.Equal(8, variants.Length)

[<Fact>]
let ``compatibility projection covers every canonical helper`` () =
    let names =
        (compatibilityProjection ()).GetProperty("patterns").EnumerateObject()
        |> Seq.map _.Name
        |> Seq.sort
        |> Seq.toArray
    Assert.Equal<string array>([| "dateTime"; "email"; "ip"; "url"; "uuid" |], names)
    Assert.Equal(names.Length, Essential.HelperIds.Length)
