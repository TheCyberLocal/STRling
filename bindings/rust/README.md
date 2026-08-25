# STRling for Rust

This package is the curated Rust facade over STRling's canonical compiler
implementation. The publishable `strling` crate is rooted at the repository
root and compiles the governed `core/src` files directly through
`core/src/lib_public.rs`. It exposes versioned request, result, diagnostic,
source, target, Simply, and standard-library contracts without copying or
creating a second parser, compiler, IR, validator, or regex emitter.

```rust
use strling::{compile, CompileRequest};

let request: CompileRequest = serde_json::from_str(canonical_request_json)?;
let result = compile(&request, None)?;
```

Target-aware requests require the exact `TargetProfile` named by the request:

```rust
use strling::{compile, CompileRequest, TargetProfile};

let request: CompileRequest = serde_json::from_str(canonical_request_json)?;
let profile: TargetProfile = serde_json::from_str(canonical_profile_json)?;
let result = compile(&request, Some(&profile))?;
```

`check` executes the same canonical boundary and does not rewrite
`requested_outputs`. Standard helpers under `strling::stdlib` preserve their
registered validation level; current helpers are lexical shapes, not semantic
validators.

The package version, compiler version, contract version, semantic
specification, Simply protocol, and target-profile versions are independent.
The internal `core/internal/Cargo.toml` package remains unpublished for repository CLI,
interop, fuzz, and performance consumers; it compiles the same source files and
is not a second distribution artifact. Selecting the next public package
version and publishing the crate remain outside this task.

See [`docs/api_reference.md`](docs/api_reference.md) for the facade layout.
