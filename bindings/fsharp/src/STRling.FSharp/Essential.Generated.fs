namespace STRling.FSharp

open System

/// Generated F# names for canonical lexical-shape helpers.
[<RequireQualifiedAccess>]
module Essential =
    let SourceSha256 = "3539cc50744c492ee617f9c836c83e040ad3af2f32dd8fe3b1e329c5b14bc719"
    let RegistryVersion = "1.0.0"
    let HelperIds = [ "stdlib.date_time"; "stdlib.email"; "stdlib.ip"; "stdlib.url"; "stdlib.uuid" ]

    let DateTime () = Strling.Simply.Essential.DateTime()
    let Email () = Strling.Simply.Essential.Email()
    let Ip (version: int option) =
        match version with
        | Some value -> Strling.Simply.Essential.Ip(Nullable value)
        | None -> Strling.Simply.Essential.Ip()
    let Url () = Strling.Simply.Essential.Url()
    let Uuid (version: int option) =
        match version with
        | Some value -> Strling.Simply.Essential.Uuid(Nullable value)
        | None -> Strling.Simply.Essential.Uuid()
