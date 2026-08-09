namespace STRling.Core

/// Container for regex flags/modifiers.
type Flags = {
    IgnoreCase: bool
    Multiline: bool
    DotAll: bool
    Unicode: bool
    Extended: bool
}

module Flags =
    /// Default flags with all options disabled.
    let defaultFlags = {
        IgnoreCase = false
        Multiline = false
        DotAll = false
        Unicode = false
        Extended = false
    }

    /// Creates Flags from a string of flag letters (e.g., "imsu").
    let fromLetters (letters: string) =
        let cleaned = letters.Replace(",", "").Replace(" ", "").ToLower()
        let mutable ignoreCase = false
        let mutable multiline = false
        let mutable dotAll = false
        let mutable unicode = false
        let mutable extended = false

        for ch in cleaned do
            match ch with
            | 'i' -> ignoreCase <- true
            | 'm' -> multiline <- true
            | 's' -> dotAll <- true
            | 'u' -> unicode <- true
            | 'x' -> extended <- true
            | _ -> ()

        { IgnoreCase = ignoreCase
          Multiline = multiline
          DotAll = dotAll
          Unicode = unicode
          Extended = extended }

    /// Convert flags to a dictionary for serialization.
    let toDict (flags: Flags) =
        dict [
            "ignoreCase", flags.IgnoreCase
            "multiline", flags.Multiline
            "dotAll", flags.DotAll
            "unicode", flags.Unicode
            "extended", flags.Extended
        ]
