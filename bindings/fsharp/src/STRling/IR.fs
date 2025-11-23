namespace STRling

open System
open System.Text.Json
open System.Text.Json.Serialization

// Recursive definition of Types and Converters to handle circular dependencies and attributes

type IRClassItemConverter() =
    inherit JsonConverter<IRClassItem>()
    override this.Read(reader: byref<Utf8JsonReader>, typeToConvert: Type, options: JsonSerializerOptions) =
        use doc = JsonDocument.ParseValue(&reader)
        let root = doc.RootElement
        let typeProp = root.GetProperty("ir").GetString()
        match typeProp with
        | "Range" ->
            let f = root.GetProperty("from").GetString()
            let t = root.GetProperty("to").GetString()
            IRClassRange(f, t)
        | "Char" ->
            let c = root.GetProperty("char").GetString()
            IRClassLiteral c
        | "Esc" ->
            let t = root.GetProperty("type").GetString()
            let mutable pElem = Unchecked.defaultof<JsonElement>
            let p = if root.TryGetProperty("property", &pElem) && pElem.ValueKind <> JsonValueKind.Null then Some(pElem.GetString()) else None
            IRClassEscape(t, p)
        | _ -> failwithf "Unknown IRClassItem type: %s" typeProp

    override this.Write(writer: Utf8JsonWriter, value: IRClassItem, options: JsonSerializerOptions) =
        writer.WriteStartObject()
        match value with
        | IRClassRange(f, t) ->
            writer.WriteString("ir", "Range")
            writer.WriteString("from", f)
            writer.WriteString("to", t)
        | IRClassLiteral c ->
            writer.WriteString("ir", "Char")
            writer.WriteString("char", c)
        | IRClassEscape(t, p) ->
            writer.WriteString("ir", "Esc")
            writer.WriteString("type", t)
            match p with Some prop -> writer.WriteString("property", prop) | None -> ()
        writer.WriteEndObject()

and IROpConverter() =
    inherit JsonConverter<IROp>()

    override this.Read(reader: byref<Utf8JsonReader>, typeToConvert: Type, options: JsonSerializerOptions) =
        use doc = JsonDocument.ParseValue(&reader)
        let root = doc.RootElement
        let typeProp = root.GetProperty("ir").GetString()
        
        match typeProp with
        | "Alt" ->
            let branches = JsonSerializer.Deserialize<IROp list>(root.GetProperty("branches"), options)
            IRAlt branches
        | "Seq" ->
            let parts = JsonSerializer.Deserialize<IROp list>(root.GetProperty("parts"), options)
            IRSeq parts
        | "Lit" ->
            let value = root.GetProperty("value").GetString()
            IRLit value
        | "Dot" -> IRDot
        | "Anchor" ->
            let at = root.GetProperty("at").GetString()
            IRAnchor at
        | "CharClass" ->
            let negated = root.GetProperty("negated").GetBoolean()
            let itemsJson = root.GetProperty("items")
            let items = 
                [ for item in itemsJson.EnumerateArray() do
                    yield JsonSerializer.Deserialize<IRClassItem>(item.GetRawText(), options) ]
            IRCharClass(negated, items)
        | "Quant" ->
            let child = JsonSerializer.Deserialize<IROp>(root.GetProperty("child"), options)
            let min = root.GetProperty("min").GetInt32()
            let maxElem = root.GetProperty("max")
            let max = if maxElem.ValueKind = JsonValueKind.String then maxElem.GetString() else maxElem.GetInt32().ToString()
            let mode = root.GetProperty("mode").GetString()
            IRQuant(child, min, max, mode)
        | "Group" ->
            let capturing = root.GetProperty("capturing").GetBoolean()
            let body = JsonSerializer.Deserialize<IROp>(root.GetProperty("body"), options)
            let mutable nameElem = Unchecked.defaultof<JsonElement>
            let name = if root.TryGetProperty("name", &nameElem) && nameElem.ValueKind <> JsonValueKind.Null then Some(nameElem.GetString()) else None
            let mutable atomicElem = Unchecked.defaultof<JsonElement>
            let atomic = if root.TryGetProperty("atomic", &atomicElem) then atomicElem.GetBoolean() else false
            IRGroup(capturing, body, name, atomic)
        | "Backref" ->
            let mutable idxElem = Unchecked.defaultof<JsonElement>
            let index = if root.TryGetProperty("byIndex", &idxElem) && idxElem.ValueKind <> JsonValueKind.Null then Some(idxElem.GetInt32()) else None
            let mutable nameElem = Unchecked.defaultof<JsonElement>
            let name = if root.TryGetProperty("byName", &nameElem) && nameElem.ValueKind <> JsonValueKind.Null then Some(nameElem.GetString()) else None
            IRBackref(index, name)
        | "Look" ->
            let dir = root.GetProperty("dir").GetString()
            let neg = root.GetProperty("neg").GetBoolean()
            let body = JsonSerializer.Deserialize<IROp>(root.GetProperty("body"), options)
            IRLook(dir, neg, body)
        | _ -> failwithf "Unknown IR type: %s" typeProp

    override this.Write(writer: Utf8JsonWriter, value: IROp, options: JsonSerializerOptions) =
        writer.WriteStartObject()
        match value with
        | IRAlt branches ->
            writer.WriteString("ir", "Alt")
            writer.WritePropertyName("branches")
            JsonSerializer.Serialize(writer, branches, options)
        | IRSeq parts ->
            writer.WriteString("ir", "Seq")
            writer.WritePropertyName("parts")
            JsonSerializer.Serialize(writer, parts, options)
        | IRLit v ->
            writer.WriteString("ir", "Lit")
            writer.WriteString("value", v)
        | IRDot -> writer.WriteString("ir", "Dot")
        | IRAnchor at ->
            writer.WriteString("ir", "Anchor")
            writer.WriteString("at", at)
        | IRCharClass(negated, items) ->
            writer.WriteString("ir", "CharClass")
            writer.WriteBoolean("negated", negated)
            writer.WritePropertyName("items")
            JsonSerializer.Serialize(writer, items, options)
        | IRQuant(child, min, max, mode) ->
            writer.WriteString("ir", "Quant")
            writer.WritePropertyName("child")
            JsonSerializer.Serialize(writer, child, options)
            writer.WriteNumber("min", min)
            if max = "Inf" then writer.WriteString("max", "Inf") else writer.WriteNumber("max", int max)
            writer.WriteString("mode", mode)
        | IRGroup(capturing, body, name, atomic) ->
            writer.WriteString("ir", "Group")
            writer.WriteBoolean("capturing", capturing)
            writer.WritePropertyName("body")
            JsonSerializer.Serialize(writer, body, options)
            match name with Some n -> writer.WriteString("name", n) | None -> ()
            if atomic then writer.WriteBoolean("atomic", true)
        | IRBackref(index, name) ->
            writer.WriteString("ir", "Backref")
            match index with Some i -> writer.WriteNumber("byIndex", i) | None -> ()
            match name with Some n -> writer.WriteString("byName", n) | None -> ()
        | IRLook(dir, neg, body) ->
            writer.WriteString("ir", "Look")
            writer.WriteString("dir", dir)
            writer.WriteBoolean("neg", neg)
            writer.WritePropertyName("body")
            JsonSerializer.Serialize(writer, body, options)
        writer.WriteEndObject()

and [<JsonConverter(typeof<IRClassItemConverter>)>] IRClassItem =
    | IRClassRange of fromCh: string * toCh: string
    | IRClassLiteral of ch: string
    | IRClassEscape of type_: string * property: string option

and [<JsonConverter(typeof<IROpConverter>)>] IROp =
    | IRAlt of branches: IROp list
    | IRSeq of parts: IROp list
    | IRLit of value: string
    | IRDot
    | IRAnchor of at: string
    | IRCharClass of negated: bool * items: IRClassItem list
    | IRQuant of child: IROp * min: int * max: string * mode: string
    | IRGroup of capturing: bool * body: IROp * name: string option * atomic: bool
    | IRBackref of byIndex: int option * byName: string option
    | IRLook of dir: string * neg: bool * body: IROp
