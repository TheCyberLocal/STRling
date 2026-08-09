# CI/CD Pipeline Setup Guide

[← Back to Developer Hub](index.md)

## Overview

The STRling project uses an automated CI/CD pipeline defined in `.github/workflows/ci.yml` that handles both continuous integration (testing) and continuous deployment (publishing to PyPI and NPM).

## Pipeline Architecture

STRling employs a **Matrix-Driven CI/CD Strategy** that validates all 17 language bindings in parallel before any deployment occurs.

### CI Strategy: The Test Matrix

The `test-matrix` job is the core validation engine that runs on every push and pull request to `main`, `dev`, and `feature/**` branches.

**Matrix Configuration:**

-   **Languages Tested:** All 17 bindings run in parallel:
    -   C, C++, C#, Python, Ruby, Go, Rust, Java, Kotlin, Dart, Lua, Perl, PHP, R, Swift, TypeScript, F#
-   **Parallel Execution:** Each language runs independently on its own Ubuntu runner
-   **Fail-Fast Disabled:** All languages complete testing even if one fails, ensuring complete visibility

**Workflow Per Language:**

1. **🔧 Universal Setup:** Makes `./strling` executable
2. **📦 Install Dependencies:** Runs `./strling setup <lang>` to configure language-specific toolchain
3. **🔨 Compile (Build):** Runs `./strling build <lang>` if the language requires compilation
4. **🧪 Execute Tests:** Runs `./strling test <lang>` to validate all functionality

**Key Benefits:**

-   **Rapid Feedback:** Parallel execution completes in ~5-10 minutes instead of sequential hours
-   **Full Coverage:** Every binding is tested on every commit
-   **Isolation:** Language-specific failures don't block other languages from completing

### Certification: The Omega Audit

The `audit_omega.py` script is the **final certification harness** for the entire STRling ecosystem.

-   **Purpose:** Validates conformance test coverage across all 17 language bindings
-   **Script:** `python3 tooling/audit_omega.py`
-   **Output:** Generates `FINAL_AUDIT_REPORT.md` with detailed certification status
-   **Requirements:**
    -   All bindings must achieve `🟢 CERTIFIED` status
    -   Zero test skips (no `SKIPPED` or `ignored` tests)
    -   Zero warnings in build/test output
    -   Semantic verification tests must pass (duplicate groups, invalid ranges)
    -   Test counts must be explicit integers (not "Unknown")

**Usage:** Run the Omega Audit locally before submitting PRs to ensure full compliance:

```bash
python3 tooling/audit_omega.py
```

### CD Strategy: All-or-Nothing Deployment

Deployment jobs execute **only** when all quality gates pass:

**Trigger Conditions:**

1. A git tag matching `v*` pattern is pushed (e.g., `v3.0.0`)
2. The `test-matrix` job completes successfully for all 17 bindings

**Deployment Jobs:** Each binding has its own deployment job that:

-   Verifies version consistency between the git tag and binding manifest
-   Checks if the version already exists in the target registry (idempotency)
-   Publishes to the appropriate package registry if version is new

**Target Registries by Language:**

-   **Python:** PyPI (via `pypa/gh-action-pypi-publish`)
-   **TypeScript:** NPM (package: `@strling-lang/strling`)
-   **Rust:** Crates.io (package: `strling_core`)
-   **C#:** NuGet (package: `STRling`)
-   **F#:** NuGet (package: `STRling.FSharp`)
-   **Ruby:** RubyGems (package: `strling`)
-   **Dart:** Pub.dev (package: `strling`)
-   **Kotlin:** Maven Central
-   **Lua:** LuaRocks (package: `strling`)
-   **Go, Swift, C, C++, PHP, R:** Tag validation only (distributed via git)
-   **Java, Perl:** Deployment not yet implemented

**Idempotency Protection:**

-   Before publishing, the `check_version_exists.py` script (located in `tooling/`) validates if the version already exists
-   If the version exists, the deployment step is skipped with a success status
-   This prevents CI failures when re-running deployments or creating tags on already-published versions

**Version Management:**

-   **SSOT:** `bindings/python/pyproject.toml` is the single source of truth for versioning
-   **Propagation:** The `sync_versions.py` script propagates the Python version to all other bindings
-   **Rule:** Never manually edit version numbers in `package.json`, `Cargo.toml`, or other manifests

## Required GitHub Secrets

For deployment to package registries, configure these secrets in your repository at **Settings** > **Secrets and variables** > **Actions**:

### Python: PYPI_API_TOKEN

**How to create:**

1. Log in to [PyPI](https://pypi.org)
2. Go to Account Settings > API tokens
3. Click "Add API token"
4. Set scope to "Entire account" or limit to "STRling"
5. Copy the token (starts with `pypi-`)

**GitHub Configuration:**

-   Name: `PYPI_API_TOKEN`
-   Value: Your PyPI token

### TypeScript: NPM_TOKEN

**How to create:**

1. Log in to [NPM](https://www.npmjs.com)
2. Go to Account Settings > Access Tokens
3. Click "Generate New Token" > "Automation"
4. Copy the token

**GitHub Configuration:**

-   Name: `NPM_TOKEN`
-   Value: Your NPM automation token

### C#/F#: NUGET_KEY

**How to create:**

1. Log in to [NuGet.org](https://www.nuget.org)
2. Go to API Keys
3. Create a new API key with push permissions
4. Copy the key

**GitHub Configuration:**

-   Name: `NUGET_KEY`
-   Value: Your NuGet API key

### Ruby: RUBYGEMS_KEY

**How to create:**

1. Log in to [RubyGems.org](https://rubygems.org)
2. Go to Settings > API Keys
3. Create a new API key
4. Copy the key

**GitHub Configuration:**

-   Name: `RUBYGEMS_KEY`
-   Value: Your RubyGems API key

### Rust: CARGO_TOKEN

**How to create:**

1. Log in to [Crates.io](https://crates.io)
2. Go to Account Settings > API Tokens
3. Create a new token
4. Copy the token

**GitHub Configuration:**

-   Name: `CARGO_TOKEN`
-   Value: Your Crates.io token

### Kotlin: Maven Central Credentials

**Required Secrets:**

-   `MAVEN_USERNAME`: Your Sonatype OSSRH username
-   `MAVEN_PASSWORD`: Your Sonatype OSSRH password
-   `GPG_KEY`: Your GPG private key for signing artifacts

**How to create:** Follow the [Maven Central publishing guide](https://central.sonatype.org/publish/publish-guide/)

### Lua: LUA_API_KEY

**How to create:**

1. Log in to [LuaRocks.org](https://luarocks.org)
2. Go to Settings > API Keys
3. Create a new API key
4. Copy the key

**GitHub Configuration:**

-   Name: `LUA_API_KEY`
-   Value: Your LuaRocks API key

### Perl: PAUSE Credentials

**Required Secrets:**

-   `PAUSE_USERNAME`: Your PAUSE (CPAN) username
-   `PAUSE_PASSWORD`: Your PAUSE password

**How to obtain:** Register at [PAUSE](https://pause.perl.org/)

### Dart: No Secret Required

Dart publishing uses OpenID Connect (OIDC) authentication. Ensure the repository has `id-token: write` permission (already configured in the workflow).

### Languages Without Registry Deployment

The following bindings are distributed via git tags only and don't require secrets:

-   **C**, **C++**, **Go**, **Swift**, **PHP**, **R**

These deployments perform tag validation only.

## Workflow Triggers

The pipeline is triggered by:

### Push Events

-   **Branches:** `main`, `dev`, `feature/**`
-   **Tags:** `v*` (triggers deployment)
-   **Path filters:** Only runs when these paths change:
    -   `bindings/**`
    -   `spec/**`
    -   `tests/**`
    -   `tooling/**`
    -   `.github/workflows/**`

### Pull Request Events

-   Same path filters as push events
-   Runs CI jobs only (no deployment)

## Branching Strategy

This workflow enforces the following branching model:

1. **`feature/**` branches\*\*: Development work happens here

    - CI runs on every push (test-matrix)
    - No deployment occurs

2. **`dev` branch**: Integration and pre-release testing

    - CI runs on every push (test-matrix)
    - No deployment occurs

3. **`main` branch**: Production-ready code
    - CI runs on every push (test-matrix)
    - No automatic deployment on push
    - **Deployment occurs only when a tag is pushed** (e.g., `git tag v3.0.0 && git push --tags`)

## Testing the Pipeline

### Test CI Only

To test the CI jobs without triggering deployment:

1. Push to a `feature/*` or `dev` branch
2. Or create a pull request to any branch
3. Monitor the Actions tab to see test-matrix running all 17 bindings in parallel

### Test Full CI/CD

To test the complete pipeline including deployment:

1. Ensure all required secrets are configured (see Required GitHub Secrets section)
2. Ensure version is updated in `bindings/python/pyproject.toml` (SSOT)
3. Run `python3 tooling/sync_versions.py --write` to propagate versions
4. Commit and merge to `main`
5. Create and push a tag: `git tag v3.0.0 && git push --tags`
6. Monitor the workflow run in the Actions tab

## Deployment Checklist

Before creating a release tag (which triggers deployment):

-   [ ] All tests pass locally: `./strling test all`
-   [ ] Omega audit passes: `python3 tooling/audit_omega.py` shows `🟢 CERTIFIED` for all 17 bindings
-   [ ] Version number updated in `bindings/python/pyproject.toml` (SSOT)
-   [ ] Run version propagation: `python3 tooling/sync_versions.py --write`
-   [ ] Changelog updated (if applicable)
-   [ ] Documentation updated
-   [ ] All required secrets configured (see below)
-   [ ] Create git tag: `git tag vX.Y.Z` (match the version in pyproject.toml)
-   [ ] Push tag: `git push --tags`

## Troubleshooting

### Deployment Fails: "Invalid credentials"

-   **Python:** Verify `PYPI_API_TOKEN` is set correctly and has upload permissions
-   **TypeScript:** Verify `NPM_TOKEN` is set correctly and has publish permissions
-   **C#/F#:** Verify `NUGET_KEY` is set correctly
-   **Dart:** Verify repository has `id-token: write` permission (OIDC authentication)
-   **Ruby:** Verify `RUBYGEMS_KEY` is set correctly
-   **Rust:** Verify `CARGO_TOKEN` is set correctly
-   **Kotlin:** Verify `MAVEN_USERNAME`, `MAVEN_PASSWORD`, and `GPG_KEY` are set
-   **Lua:** Verify `LUA_API_KEY` is set correctly
-   **Perl:** Verify `PAUSE_USERNAME` and `PAUSE_PASSWORD` are set

### Tests Pass Locally But Fail in CI

-   Check language versions in CI match your local environment
-   Ensure all dependencies are listed in language-specific manifests
-   Review the test-matrix job output for the specific language that failed
-   Run `./strling clean <lang> && ./strling setup <lang> && ./strling test <lang>` locally

### Deployment Skipped

-   Verify you pushed a **tag** (not just a commit): `git push --tags`
-   Ensure the tag matches semver format: `vX.Y.Z`
-   Check that test-matrix completed successfully
-   Review the deployment job logs for the `if` condition evaluation
-   Verify the version doesn't already exist in the target registry (idempotent check)

### Version Already Published

-   Package registries don't allow re-publishing the same version
-   Update version in `bindings/python/pyproject.toml` (SSOT)
-   Run `python3 tooling/sync_versions.py --write` to propagate
-   Create a new tag matching the new version

## Version Management

STRling uses a **Single Source of Truth (SSOT)** approach for version management:

**SSOT Location:** `bindings/python/pyproject.toml`

**Workflow:**

1. Update version in `bindings/python/pyproject.toml`:

    ```toml
    [project]
    version = "3.0.0"  # Update this only
    ```

2. Run the version propagation script:

    ```bash
    python3 tooling/sync_versions.py --write
    ```

3. The script automatically updates all other binding manifests:
    - TypeScript: `bindings/typescript/package.json`
    - Rust: `bindings/rust/Cargo.toml`
    - C#: `bindings/csharp/src/STRling/STRling.csproj`
    - F#: `bindings/fsharp/src/STRling/STRling.fsproj`
    - Ruby: `bindings/ruby/strling.gemspec`
    - Dart: `bindings/dart/pubspec.yaml`
    - Kotlin: `bindings/kotlin/build.gradle.kts`
    - Lua: `bindings/lua/strling-scm-1.rockspec`
    - And all other bindings...

**Rule:** Never manually edit version numbers in non-Python manifests. Always use the SSOT + propagation workflow.

**Note:** The TypeScript binding is the Logic SSOT (the reference implementation for all language behavior and features), but Python is the Versioning SSOT (the single source for version numbers). This separation ensures clarity of responsibility.

## Monitoring

Monitor workflow runs:

1. Go to the **Actions** tab in your GitHub repository
2. Click on "STRling CI/CD Pipeline"
3. View recent runs and their status
4. Click on individual runs to see detailed logs for each job

## Security Best Practices

-   ✅ Never commit secrets to the repository
-   ✅ Use GitHub Secrets for sensitive tokens
-   ✅ Regularly rotate API tokens
-   ✅ Use scoped tokens (limit to specific packages when possible)
-   ✅ Review published packages after deployment
