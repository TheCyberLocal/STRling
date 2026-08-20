namespace STRling.FSharp

open System
open System.Text.Json
open Strling
open Strling.Native

/// Idiomatic F# projection of a canonical compile result.
type CompileOutcome =
    | Succeeded of JsonElement
    | Failed of JsonElement

/// Deterministic source-request options; no target is selected implicitly.
type SourceOptions =
    { SourceId: string
      FrontendId: string
      FrontendVersion: string
      MediaType: string
      SpecificationVersion: string
      RequestedOutputs: string list option
      CompilerOptions: JsonElement
      TargetProfileReference: JsonElement option
      TargetProfile: JsonElement option }

[<RequireQualifiedAccess>]
module Api =
    let private defaultCompilerOptions () =
        JsonSerializer.SerializeToElement(
            {| partial_semantics = "forbid"
               diagnostic_policy = {| minimum_severity = "hint" |} |})

    let defaultOptions () =
        { SourceId = "src:fsharp.adapter"
          FrontendId = "semantic_strling"
          FrontendVersion = "1.0-draft.1"
          MediaType = "text/strling"
          SpecificationVersion = "1.0-draft.1"
          RequestedOutputs = None
          CompilerOptions = defaultCompilerOptions ()
          TargetProfileReference = None
          TargetProfile = None }

    let private toCSharpOptions (options: SourceOptions) =
        let requestedOutputs =
            match options.RequestedOutputs with
            | Some values -> values :> Collections.Generic.IReadOnlyList<string>
            | None -> Unchecked.defaultof<Collections.Generic.IReadOnlyList<string>>
        let targetProfileReference =
            match options.TargetProfileReference with
            | Some value -> Nullable value
            | None -> Nullable()
        let targetProfile =
            match options.TargetProfile with
            | Some value -> Nullable value
            | None -> Nullable()
        SourceCompileOptions(
            SourceId = options.SourceId,
            FrontendId = options.FrontendId,
            FrontendVersion = options.FrontendVersion,
            MediaType = options.MediaType,
            SpecificationVersion = options.SpecificationVersion,
            RequestedOutputs = requestedOutputs,
            CompilerOptions = options.CompilerOptions,
            TargetProfileReference = targetProfileReference,
            TargetProfile = targetProfile)

    let loadClient (absoluteLibraryPath: string) = NativeClient.Load absoluteLibraryPath
    let createCompiler (client: NativeClient) = Compiler client

    let project (result: JsonElement) =
        match result.GetProperty("outcome").GetString() with
        | "succeeded" -> Succeeded(result.Clone())
        | "failed" -> Failed(result.Clone())
        | value -> invalidOp $"canonical compile result has unsupported outcome {value}"

    let compile (compiler: Compiler) (request: JsonElement) (targetProfile: JsonElement option) =
        match targetProfile with
        | Some target -> compiler.Compile(request, Nullable target) |> project
        | None -> compiler.Compile(request) |> project

    let check compiler request targetProfile = compile compiler request targetProfile

    let parse (compiler: Compiler) (source: string) (options: SourceOptions option) =
        let selected = defaultArg options (defaultOptions ())
        compiler.Parse(source, toCSharpOptions selected) |> project

    let parseToArtifact (compiler: Compiler) (source: string) (options: SourceOptions) =
        compiler.ParseToArtifact(source, toCSharpOptions options) |> project

    let describe (compiler: Compiler) = compiler.Describe()
    let inspectTargetProfile (compiler: Compiler) (profile: JsonElement) = compiler.InspectTargetProfile profile

    let sourceCompileRequest (source: string) (options: SourceOptions option) (fallbackOutputs: string list) =
        let selected = defaultArg options (defaultOptions ())
        Compiler.SourceCompileRequest(source, toCSharpOptions selected, fallbackOutputs)
