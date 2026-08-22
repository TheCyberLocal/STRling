# Releasing STRling

[← Back to Developer Hub](index.md)

This document outlines the process for releasing new versions of STRling and its bindings.

## Release Workflow

STRling follows a "Single Source of Truth" (SSOT) model for versioning. The version is defined in `bindings/python/pyproject.toml` and propagated to all other bindings using the `tooling/sync_versions.py` script.

### 0. Product certification

Before bumping any version, run the governed Full profile and derive the
machine-readable product-certification artifact and its human view from that
same structured evidence:

```bash
python3 tooling/product_certification.py --run-profile \
  --artifact target/certification/product-certification.json \
  --report target/certification/product-certification.md
```

Do not proceed unless the command exits successfully, the artifact aggregate is
`passed` or governed `waived`, and every waiver reference is approved. The
historical `./strling audit` command is only a compatibility alias for this
structured authority; it no longer scans runner output or updates the archived
Final Audit Report.

The delivery workflow applies the same derivation to its canonical Release
profile artifact. Release and Full memberships must remain identical for product
certification; either profile fingerprint drifting from the producer manifest
fails closed. Product derivation also runs for a nonpassing Release aggregate so
the retained product view preserves the source status instead of disappearing.

### 1. Update Version

1.  Edit `bindings/python/pyproject.toml` and update the `version` field.
2.  Run the sync script to propagate the version to all bindings:
    ```bash
    python3 tooling/sync_versions.py --write
    ```
3.  Commit the changes:
    ```bash
    git add .
    git commit -m "chore: bump version to X.Y.Z"
    ```

### 2. Tag and Push

Create a git tag for the release. The tag **must** start with `v`.

```bash
git tag vX.Y.Z
git push origin vX.Y.Z
```

### 3. CI/CD Deployment

Pushing the tag will trigger the GitHub Actions workflow defined in `.github/workflows/ci.yml`. The workflow will:

1.  Run all test suites (`test-*` jobs).
2.  If tests pass, trigger the deployment jobs (`deploy-*`).

## Deployment Jobs & Registries

| Language       | Registry  | Job Name            | Command                           |
| :------------- | :-------- | :------------------ | :-------------------------------- |
| **Python**     | PyPI      | `deploy-python`     | `python -m build && twine upload` |
| **TypeScript** | NPM       | `deploy-typescript` | `npm publish`                     |
| **Rust**       | Crates.io | `deploy-rust`       | `cargo publish`                   |
| **C#**         | NuGet     | `deploy-csharp`     | `dotnet nuget push`               |
| **Ruby**       | RubyGems  | `deploy-ruby`       | `gem push`                        |
| **Dart**       | Pub.dev   | `deploy-dart`       | `dart pub publish`                |
| **Lua**        | LuaRocks  | `deploy-lua`        | `luarocks upload`                 |

## Required Secrets

The following secrets must be configured in the GitHub Repository Settings (Settings > Secrets and variables > Actions).

| Secret Name    | Description          | Used By             |
| :------------- | :------------------- | :------------------ |
| `NPM_TOKEN`    | NPM Automation Token | `deploy-typescript` |
| `CARGO_TOKEN`  | Crates.io API Token  | `deploy-rust`       |
| `NUGET_KEY`    | NuGet API Key        | `deploy-csharp`     |
| `RUBYGEMS_KEY` | RubyGems API Key     | `deploy-ruby`       |
| `LUA_API_KEY`  | LuaRocks API Key     | `deploy-lua`        |

**Note:**

-   **Python (PyPI)** uses Trusted Publishing (OIDC), so no long-lived token is required.
-   **Dart (Pub.dev)** uses OIDC. Ensure `id-token: write` permission is enabled in the workflow.

## Manual Steps

-   **PHP**: Packagist updates are triggered via Webhook when the tag is pushed. Ensure the Packagist webhook is configured in the GitHub repository settings.
