module ExampleTests

open Xunit
open STRling.FSharp.Api

[<Fact>]
let ``create parser returns non-null`` () =
    let p = createParser()
    Assert.NotNull(p)

[<Fact>]
let ``parse returns not implemented error`` () =
    let p = createParser()
    match parse p "abc" with
    | Error msg -> Assert.Equal("parse not implemented in C# Parser", msg)
    | Ok _ -> failwith "Expected parse to be unimplemented"
