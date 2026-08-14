# STRling interoperability contracts

This directory owns the versioned, host-neutral boundaries used to invoke the
canonical STRling compiler from native and WebAssembly adapters. It defines
transport bytes, ABI-visible data, ownership, and version negotiation. It does
not define language semantics, frontend syntax, target behavior, or an
idiomatic API for any host language.

The current contract is [`strling.interop` 1.0.0](1.0/README.md). Its embedded
compiler, target-profile, diagnostic, and Simply values remain governed by
their own versioned contracts.
