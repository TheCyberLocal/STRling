namespace STRling

open System
open System.Text.Json
open System.Text.Json.Serialization
open System.Collections.Generic

// Forward declarations
type Node =
    | Lit of value: string
    | Seq of parts: Node list
    | Alt of alternatives: Node list
    | Dot
    | Anchor of at: string
    | CharClass of negated: bool * members: ClassItem list
    | Quant of target: Node * min: int * max: int option * greedy: bool * lazy_: bool * possessive: bool
    | Group of capturing: bool * name: string option * atomic: bool * body: Node
    | Backref of index: int option * name: string option
    | Lookahead of body: Node
    | NegativeLookahead of body: Node
    | Lookbehind of body: Node
    | NegativeLookbehind of body: Node

and ClassItem =
    | ClassRange of fromCh: string * toCh: string
    | ClassLiteral of value: string
    | ClassEscape of kind: string
    | ClassUnicodeProperty of name: string option * value: string * negated: bool

type ClassItemConverter() =
    inherit JsonConverter<ClassItem>()
    override this.Read(reader: byref<Utf8JsonReader>, typeToConvert: Type, options: JsonSerializerOptions) =
        use doc = JsonDocument.ParseValue(&reader)
        let root = doc.RootElement
        let typeProp = root.GetProperty("type").GetString()
        match typeProp with
        | "Range" ->
            let f = root.GetProperty("from").GetString()
            let t = root.GetProperty("to").GetString()
            ClassRange(f, t)
        | "Literal" ->
            let v = root.GetProperty("value").GetString()
            ClassLiteral v
        | "Escape" ->
            let k = root.GetProperty("kind").GetString()
            ClassEscape k
        | "UnicodeProperty" ->
            let nElem = root.GetProperty("name")
            let n = if nElem.ValueKind = JsonValueKind.Null then None else Some(nElem.GetString())
            let v = root.GetProperty("value").GetString()
            let neg = root.GetProperty("negated").GetBoolean()
            ClassUnicodeProperty(n, v, neg)
        | _ -> failwithf "Unknown ClassItem type: %s" typeProp

    override this.Write(writer: Utf8JsonWriter, value: ClassItem, options: JsonSerializerOptions) =
        writer.WriteStartObject()
        match value with
        | ClassRange(f, t) ->
            writer.WriteString("type", "Range")
            writer.WriteString("from", f)
            writer.WriteString("to", t)
        | ClassLiteral v ->
            writer.WriteString("type", "Literal")
            writer.WriteString("value", v)
        | ClassEscape k ->
            writer.WriteString("type", "Escape")
            writer.WriteString("kind", k)
        | ClassUnicodeProperty(n, v, neg) ->
            writer.WriteString("type", "UnicodeProperty")
            match n with Some name -> writer.WriteString("name", name) | None -> writer.WriteNull("name")
            writer.WriteString("value", v)
            writer.WriteBoolean("negated", neg)
        writer.WriteEndObject()

type NodeConverter() =
    inherit JsonConverter<Node>()

    override this.Read(reader: byref<Utf8JsonReader>, typeToConvert: Type, options: JsonSerializerOptions) =
        use doc = JsonDocument.ParseValue(&reader)
        let root = doc.RootElement
        let typeProp = root.GetProperty("type").GetString()
        
        match typeProp with
        | "Literal" -> 
            let value = root.GetProperty("value").GetString()
            Lit value
        | "Sequence" ->
            let parts = JsonSerializer.Deserialize<Node list>(root.GetProperty("parts"), options)
            Seq parts
        | "Alternation" ->
            let alts = JsonSerializer.Deserialize<Node list>(root.GetProperty("alternatives"), options)
            Alt alts
        | "Dot" -> Dot
        | "Anchor" ->
            let at = root.GetProperty("at").GetString()
            Anchor at
        | "CharacterClass" ->
            let negated = root.GetProperty("negated").GetBoolean()
            // We need to use ClassItemConverter for members
            let membersJson = root.GetProperty("members")
            let members = 
                [ for item in membersJson.EnumerateArray() do
                    yield JsonSerializer.Deserialize<ClassItem>(item.GetRawText(), options) ]
            CharClass(negated, members)
        | "Quantifier" ->
            let min = root.GetProperty("min").GetInt32()
            let maxElem = root.GetProperty("max")
            let max = if maxElem.ValueKind = JsonValueKind.Null then None else Some(maxElem.GetInt32())
            let greedy = root.GetProperty("greedy").GetBoolean()
            let lazy_ = root.GetProperty("lazy").GetBoolean()
            let possessive = root.GetProperty("possessive").GetBoolean()
            let target = JsonSerializer.Deserialize<Node>(root.GetProperty("target"), options)
            Quant(target, min, max, greedy, lazy_, possessive)
        | "Group" ->
            let capturing = root.GetProperty("capturing").GetBoolean()
            let nameElem = root.GetProperty("name")
            let name = if nameElem.ValueKind = JsonValueKind.Null then None else Some(nameElem.GetString())
            let atomic = root.GetProperty("atomic").GetBoolean()
            let body = JsonSerializer.Deserialize<Node>(root.GetProperty("body"), options)
            Group(capturing, name, atomic, body)
        | "Backreference" ->
            let indexElem = root.GetProperty("index")
            let index = if indexElem.ValueKind = JsonValueKind.Null then None else Some(indexElem.GetInt32())
            let nameElem = root.GetProperty("name")
            let name = if nameElem.ValueKind = JsonValueKind.Null then None else Some(nameElem.GetString())
            Backref(index, name)
        | "Lookahead" ->
            let body = JsonSerializer.Deserialize<Node>(root.GetProperty("body"), options)
            Lookahead body
        | "NegativeLookahead" ->
            let body = JsonSerializer.Deserialize<Node>(root.GetProperty("body"), options)
            NegativeLookahead body
        | "Lookbehind" ->
            let body = JsonSerializer.Deserialize<Node>(root.GetProperty("body"), options)
            Lookbehind body
        | "NegativeLookbehind" ->
            let body = JsonSerializer.Deserialize<Node>(root.GetProperty("body"), options)
            NegativeLookbehind body
        | _ -> failwithf "Unknown node type: %s" typeProp

    override this.Write(writer: Utf8JsonWriter, value: Node, options: JsonSerializerOptions) =
        writer.WriteStartObject()
        match value with
        | Lit v -> 
            writer.WriteString("type", "Literal")
            writer.WriteString("value", v)
        | Seq parts ->
            writer.WriteString("type", "Sequence")
            writer.WritePropertyName("parts")
            JsonSerializer.Serialize(writer, parts, options)
        | Alt alts ->
            writer.WriteString("type", "Alternation")
            writer.WritePropertyName("alternatives")
            JsonSerializer.Serialize(writer, alts, options)
        | Dot -> writer.WriteString("type", "Dot")
        | Anchor at ->
            writer.WriteString("type", "Anchor")
            writer.WriteString("at", at)
        | CharClass(negated, members) ->
            writer.WriteString("type", "CharacterClass")
            writer.WriteBoolean("negated", negated)
            writer.WritePropertyName("members")
            JsonSerializer.Serialize(writer, members, options)
        | Quant(target, min, max, greedy, lazy_, possessive) ->
            writer.WriteString("type", "Quantifier")
            writer.WritePropertyName("target")
            JsonSerializer.Serialize(writer, target, options)
            writer.WriteNumber("min", min)
            match max with Some m -> writer.WriteNumber("max", m) | None -> writer.WriteNull("max")
            writer.WriteBoolean("greedy", greedy)
            writer.WriteBoolean("lazy", lazy_)
            writer.WriteBoolean("possessive", possessive)
        | Group(capturing, name, atomic, body) ->
            writer.WriteString("type", "Group")
            writer.WriteBoolean("capturing", capturing)
            match name with Some n -> writer.WriteString("name", n) | None -> writer.WriteNull("name")
            writer.WriteBoolean("atomic", atomic)
            writer.WritePropertyName("body")
            JsonSerializer.Serialize(writer, body, options)
        | Backref(index, name) ->
            writer.WriteString("type", "Backreference")
            match index with Some i -> writer.WriteNumber("index", i) | None -> writer.WriteNull("index")
            match name with Some n -> writer.WriteString("name", n) | None -> writer.WriteNull("name")
        | Lookahead body ->
            writer.WriteString("type", "Lookahead")
            writer.WritePropertyName("body")
            JsonSerializer.Serialize(writer, body, options)
        | NegativeLookahead body ->
            writer.WriteString("type", "NegativeLookahead")
            writer.WritePropertyName("body")
            JsonSerializer.Serialize(writer, body, options)
        | Lookbehind body ->
            writer.WriteString("type", "Lookbehind")
            writer.WritePropertyName("body")
            JsonSerializer.Serialize(writer, body, options)
        | NegativeLookbehind body ->
            writer.WriteString("type", "NegativeLookbehind")
            writer.WritePropertyName("body")
            JsonSerializer.Serialize(writer, body, options)
        writer.WriteEndObject()
