namespace STRling.Tests

open System
open System.IO
open System.Text.Json
open System.Text.RegularExpressions
open Xunit
open STRling.Simply

module Essential5Tests =

    let private findSpec () =
        let rec findRoot (dir: string) =
            let candidate = Path.Combine(dir, "spec", "stdlib", "essential_5.json")
            if File.Exists candidate then candidate
            else
                let parent = Directory.GetParent(dir)
                if parent = null then failwith "essential_5.json not found"
                else findRoot parent.FullName
        findRoot (Directory.GetCurrentDirectory())

    let private spec : JsonElement =
        use fs = File.OpenRead(findSpec ())
        JsonDocument.Parse(fs).RootElement.Clone()

    let private strings (pattern: string) (field: string) =
        let arr =
            spec.GetProperty("patterns").GetProperty(pattern)
                .GetProperty("fixtures").GetProperty(field)
        [ for el in arr.EnumerateArray() -> el.GetString() ]

    let private fullMatch (p: Pattern) =
        Regex("^(?:" + p.ToPcre2() + ")$")

    [<Fact>]
    let ``email accepts all valid fixtures`` () =
        let re = fullMatch (email ())
        for v in strings "email" "valid" do
            Assert.True(re.IsMatch v, sprintf "expected match for %s" v)

    [<Fact>]
    let ``email rejects all invalid fixtures`` () =
        let re = fullMatch (email ())
        for v in strings "email" "invalid" do
            Assert.False(re.IsMatch v, sprintf "expected NO match for %s" v)

    [<Fact>]
    let ``url accepts all valid fixtures`` () =
        let re = fullMatch (url ())
        for v in strings "url" "valid" do
            Assert.True(re.IsMatch v, sprintf "expected match for %s" v)

    [<Fact>]
    let ``url rejects all invalid fixtures`` () =
        let re = fullMatch (url ())
        for v in strings "url" "invalid" do
            Assert.False(re.IsMatch v, sprintf "expected NO match for %s" v)

    [<Fact>]
    let ``uuid accepts all valid default fixtures`` () =
        let re = fullMatch (uuidAny ())
        for v in strings "uuid" "valid_default" do
            Assert.True(re.IsMatch v, sprintf "expected match for %s" v)

    [<Fact>]
    let ``uuid rejects all invalid default fixtures`` () =
        let re = fullMatch (uuidAny ())
        for v in strings "uuid" "invalid_default" do
            Assert.False(re.IsMatch v, sprintf "expected NO match for %s" v)

    [<Fact>]
    let ``uuid v4 accepts all valid v4 fixtures`` () =
        let re = fullMatch (uuid 4)
        for v in strings "uuid" "valid_v4" do
            Assert.True(re.IsMatch v, sprintf "expected match for %s" v)

    [<Fact>]
    let ``uuid v4 rejects all invalid v4 fixtures`` () =
        let re = fullMatch (uuid 4)
        for v in strings "uuid" "invalid_v4" do
            Assert.False(re.IsMatch v, sprintf "expected NO match for %s" v)

    [<Fact>]
    let ``ip v4 accepts all valid v4 fixtures`` () =
        let re = fullMatch (ip 4)
        for v in strings "ip" "valid_v4" do
            Assert.True(re.IsMatch v, sprintf "expected match for %s" v)

    [<Fact>]
    let ``ip v4 rejects all invalid v4 fixtures`` () =
        let re = fullMatch (ip 4)
        for v in strings "ip" "invalid_v4" do
            Assert.False(re.IsMatch v, sprintf "expected NO match for %s" v)

    [<Fact>]
    let ``ip v6 accepts all valid v6 fixtures`` () =
        let re = fullMatch (ip 6)
        for v in strings "ip" "valid_v6" do
            Assert.True(re.IsMatch v, sprintf "expected match for %s" v)

    [<Fact>]
    let ``ip v6 rejects all invalid v6 fixtures`` () =
        let re = fullMatch (ip 6)
        for v in strings "ip" "invalid_v6" do
            Assert.False(re.IsMatch v, sprintf "expected NO match for %s" v)

    [<Fact>]
    let ``ip default accepts both families`` () =
        let re = fullMatch (ipAny ())
        for v in strings "ip" "valid_v4" @ strings "ip" "valid_v6" do
            Assert.True(re.IsMatch v, sprintf "expected match for %s" v)

    [<Fact>]
    let ``dateTime accepts all valid fixtures`` () =
        let re = fullMatch (dateTime ())
        for v in strings "dateTime" "valid" do
            Assert.True(re.IsMatch v, sprintf "expected match for %s" v)

    [<Fact>]
    let ``dateTime rejects all invalid fixtures`` () =
        let re = fullMatch (dateTime ())
        for v in strings "dateTime" "invalid" do
            Assert.False(re.IsMatch v, sprintf "expected NO match for %s" v)
