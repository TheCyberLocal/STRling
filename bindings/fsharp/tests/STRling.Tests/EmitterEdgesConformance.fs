module STRling.Tests.EmitterEdgesConformance

// Emitter Edges Conformance — F# bridge.
//
// Drives the global pathological-AST fixture
// `tests/conformance/inputs/emitter_edges/pathological.json` through the
// F# `Pcre2` emitter and asserts each Phase 3a safety guard fires:
//   1. Variable-Length Lookbehind Rejection — STRlingCompilationError
//   2. AST Depth Limit Exceeded             — STRlingCompilationError
//   3. ReDoS Risk Warning (`(a+)+`)         — non-fatal STRlingWarning
//
// The local `astToIR` mirrors the TypeScript bridge so the test targets
// the emitter without coupling to the parser/compiler stages. Keep it
// minimal — supporting only node types currently appearing in
// `pathological.json` — so adapter omissions cannot mask emitter bugs by
// silently dropping nodes.

open System
open System.IO
open System.Text.Json
open Xunit
open STRling
open STRling.Core
open STRling.Emitters

/// Climb from the test bin directory to the workspace root (marked by
/// `toolchain.json`) and resolve the global pathological fixture path.
let private fixturePath () : string =
    let mutable dir = AppContext.BaseDirectory
    let mutable found = None
    let mutable steps = 0
    while found.IsNone && steps < 12 && not (isNull dir) do
        if File.Exists(Path.Combine(dir, "toolchain.json")) then
            found <- Some dir
        else
            dir <- Path.GetDirectoryName(dir)
        steps <- steps + 1
    match found with
    | Some root ->
        Path.Combine(root, "tests", "conformance", "inputs", "emitter_edges", "pathological.json")
    | None ->
        failwithf "Could not locate workspace root (toolchain.json) from %s" AppContext.BaseDirectory

/// User-facing AST -> IR adapter. Extend only as new node types appear
/// in `pathological.json`.
let rec private astToIR (node: JsonElement) : IROp =
    let typ = node.GetProperty("type").GetString()
    match typ with
    | "Literal" ->
        let value =
            let mutable v = Unchecked.defaultof<JsonElement>
            if node.TryGetProperty("value", &v) then v.GetString() else ""
        IRLit value
    | "Group" ->
        IRGroup (false, astToIR (node.GetProperty("content")), None, false)
    | "Quantifier" ->
        let child = astToIR (node.GetProperty("content"))
        let minv =
            let mutable v = Unchecked.defaultof<JsonElement>
            if node.TryGetProperty("min", &v) then v.GetInt32() else 0
        let maxv =
            let mutable v = Unchecked.defaultof<JsonElement>
            if node.TryGetProperty("max", &v) && v.ValueKind <> JsonValueKind.Null then
                string (v.GetInt32())
            else
                // null in the user-facing AST means unbounded → IR sentinel "Inf".
                "Inf"
        let mode =
            let mutable v = Unchecked.defaultof<JsonElement>
            if node.TryGetProperty("mode", &v) then v.GetString() else "Greedy"
        IRQuant (child, minv, maxv, mode)
    | "Lookbehind" ->
        IRLook ("Behind", false, astToIR (node.GetProperty("content")))
    | "NegativeLookbehind" ->
        IRLook ("Behind", true, astToIR (node.GetProperty("content")))
    | "Lookahead" ->
        IRLook ("Ahead", false, astToIR (node.GetProperty("content")))
    | "NegativeLookahead" ->
        IRLook ("Ahead", true, astToIR (node.GetProperty("content")))
    | other ->
        failwithf "astToIR: unsupported pathological AST node type \"%s\". Extend the adapter when new pathological vectors are added." other

let private expectedSubstring (prefixed: string) : string =
    if prefixed.StartsWith("STRlingCompilationError:") then
        prefixed.Substring("STRlingCompilationError:".Length).TrimStart()
    elif prefixed.StartsWith("STRlingWarning") then
        let idx = prefixed.IndexOf(']')
        if idx >= 0 then prefixed.Substring(idx + 1).TrimStart(':', ' ')
        else prefixed
    else prefixed

let private loadCases () : obj[] seq =
    let json = File.ReadAllText(fixturePath ())
    let doc = JsonDocument.Parse(json)
    seq {
        for tc in doc.RootElement.GetProperty("tests").EnumerateArray() do
            yield [| box (tc.GetProperty("name").GetString()); box (tc.GetRawText()) |]
    }

/// xUnit `MemberData` requires a public static member on a discoverable
/// type. F# modules expose `let` bindings as static members on a class
/// named after the module — wrap the case loader in a dedicated type so
/// the attribute can resolve `PathologicalCases` via reflection.
type PathologicalCasesProvider() =
    static member PathologicalCases : obj[] seq = loadCases () |> Seq.toList |> List.toSeq

[<Theory>]
[<MemberData("PathologicalCases", MemberType = typeof<PathologicalCasesProvider>)>]
let ``run pathological case`` (name: string) (rawJson: string) =
    use doc = JsonDocument.Parse(rawJson)
    let tc = doc.RootElement
    let ir = astToIR (tc.GetProperty("ast"))
    let maxDepth =
        let mutable v = Unchecked.defaultof<JsonElement>
        if tc.TryGetProperty("depth_override_for_test", &v) then v.GetInt32() else 0

    let mutable errEl = Unchecked.defaultof<JsonElement>
    let mutable warnEl = Unchecked.defaultof<JsonElement>
    if tc.TryGetProperty("expected_error", &errEl) then
        let needle = expectedSubstring (errEl.GetString())
        let ex =
            Assert.Throws<STRlingCompilationError>(fun () ->
                Pcre2.emitWithDiagnostics ir None maxDepth |> ignore)
        Assert.Contains(needle, ex.Message)
    elif tc.TryGetProperty("expected_warning", &warnEl) then
        let needle = expectedSubstring (warnEl.GetString())
        let result = Pcre2.emitWithDiagnostics ir None maxDepth
        // Warnings must NOT abort emission — the pattern is still produced.
        Assert.False(String.IsNullOrEmpty(result.Pattern),
                     "expected non-empty pattern when only a warning fires")
        Assert.Contains(result.Warnings,
                        fun w -> w.Code = "REDOS_RISK" && w.Message.Contains(needle))
    else
        Assert.Fail(sprintf "Test case \"%s\" declares neither expected_error nor expected_warning." name)

// --- Negative controls -------------------------------------------------

[<Fact>]
let ``non-pathological pattern emits no warnings`` () =
    let result = Pcre2.emitWithDiagnostics (IRLit "abc") None 0
    Assert.Equal("abc", result.Pattern)
    Assert.Empty(result.Warnings)

[<Fact>]
let ``depth cap does not fire under limit`` () =
    let deep =
        IRGroup (false, IRGroup (false, IRLit "ok", None, false), None, false)
    let result = Pcre2.emitWithDiagnostics deep None 5
    Assert.Empty(result.Warnings)
    Assert.Contains("ok", result.Pattern)
