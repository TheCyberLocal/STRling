namespace STRling

module Compiler =

    let rec compile (node: Node) : IROp =
        match node with
        | Lit value -> IRLit value
        | Seq parts -> 
            let compiledParts = parts |> List.map compile
            createSeq compiledParts
        | Alt alts -> IRAlt (alts |> List.map compile)
        | Dot -> IRDot
        | Anchor at -> IRAnchor (mapAnchor at)
        | CharClass (negated, members) -> 
            IRCharClass (negated, members |> List.map compileClassItem)
        | Quant (target, min, max, greedy, lazy_, possessive) ->
            let mode = 
                if possessive then "Possessive"
                elif lazy_ then "Lazy"
                else "Greedy"
            let maxStr = match max with Some m -> string m | None -> "Inf"
            IRQuant (compile target, min, maxStr, mode)
        | Group (capturing, name, atomic, body) ->
            IRGroup (capturing, compile body, name, atomic)
        | Backref (index, name) ->
            IRBackref (index, name)
        | Lookahead body -> IRLook ("Ahead", false, compile body)
        | NegativeLookahead body -> IRLook ("Ahead", true, compile body)
        | Lookbehind body -> IRLook ("Behind", false, compile body)
        | NegativeLookbehind body -> IRLook ("Behind", true, compile body)

    and compileClassItem (item: ClassItem) : IRClassItem =
        match item with
        | ClassRange (f, t) -> IRClassRange (f, t)
        | ClassLiteral c -> IRClassLiteral c
        | ClassEscape k -> 
            let type_ = mapEscapeKind k
            IRClassEscape (type_, None)
        | ClassUnicodeProperty (_, value, negated) -> 
            let type_ = if negated then "P" else "p"
            IRClassEscape (type_, Some value)

    and mapEscapeKind (kind: string) =
        match kind with
        | "digit" -> "d"
        | "not-digit" -> "D"
        | "space" -> "s"
        | "not-space" -> "S"
        | "word" -> "w"
        | "not-word" -> "W"
        | _ -> kind

    and mapAnchor (at: string) =
        match at with
        | "NonWordBoundary" -> "NotWordBoundary"
        | _ -> at

    and createSeq (parts: IROp list) : IROp =
        // Flatten sequences
        let flattened = 
            parts |> List.collect (function
                | IRSeq subParts -> subParts
                | other -> [other])
        
        // Merge adjacent literals
        let merged = 
            flattened |> List.fold (fun acc op ->
                match acc, op with
                | (IRLit lastVal) :: rest, IRLit newVal -> 
                    (IRLit (lastVal + newVal)) :: rest
                | _, _ -> op :: acc
            ) []
            |> List.rev

        match merged with
        | [single] -> single
        | _ -> IRSeq merged
