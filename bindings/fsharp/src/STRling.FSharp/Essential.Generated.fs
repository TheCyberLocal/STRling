namespace STRling.FSharp

open System

/// Generated F# names for canonical lexical-shape helpers.
[<RequireQualifiedAccess>]
module Essential =
    let SourceSha256 = "db3d1fc6ddd1b0ef83cb7bfb4a9bd84c8bcc547d5a6649a6747cc4b94fb4edff"
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
