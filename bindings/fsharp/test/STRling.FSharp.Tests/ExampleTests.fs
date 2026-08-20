module CanonicalAdapterTests

open System.Text.Json
open Xunit
open STRling.FSharp

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
