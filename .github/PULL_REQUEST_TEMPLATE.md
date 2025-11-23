## 🚀 Description

## 📋 Type of Change

-   [ ] 🐛 **Bug Fix** (Non-breaking change which fixes an issue)
-   [ ] ✨ **New Feature** (Non-breaking change which adds functionality)
-   [ ] 💥 **Breaking Change** (Fix or feature that would cause existing functionality to not work as expected)
-   [ ] 📝 **Documentation** (Update to README, API docs, or comments)
-   [ ] 🔧 **Chore/Tooling** (Build scripts, CI configuration, etc.)

---

## ⚠️ Architecture Safety Check

**STRling enforces a strict "Single Source of Truth" (SSOT) architecture. Please confirm you have NOT violated these rules:**

### 1. Logic & Specs (The "Golden Master" Rule)

-   [ ] **I have NOT manually edited any JSON files in `tests/spec/`.**
    -   _Rationale:_ These files are generated artifacts. Manual changes will be overwritten.
-   [ ] **If I modified core logic (grammar/parsing):**
    -   [ ] I updated the source in `bindings/typescript`.
    -   [ ] I ran `npm run build:specs` in `bindings/typescript` to regenerate the JSON specs.
    -   [ ] I verified the new specs appear correctly in `tests/spec/`.

### 2. Versioning (The "Python" Rule)

-   [ ] **I have NOT manually bumped version numbers in `package.json`, `Cargo.toml`, etc.**
    -   _Rationale:_ The versioning SSOT is `bindings/python/pyproject.toml`. The CI pipeline handles propagation.
-   [ ] **If this is a release preparation:**
    -   [ ] I only updated `bindings/python/pyproject.toml`.
    -   [ ] I ran `python3 tooling/sync_versions.py --write` to update the ecosystem.

---

## 🧪 Testing & Verification

-   [ ] **Core Logic:** TypeScript (`npm test`)
-   [ ] **Target Binding(s):**
    -   [ ] Python (`pytest`)
    -   [ ] Rust (`cargo test`)
    -   [ ] Go (`go test ./...`)
    -   [ ] Java/Kotlin/C#/Others: ********\_********
-   [ ] **Conformance:** I ran the conformance suite for the modified language(s) and confirmed ~594+ tests passed.

## ✅ Checklist

-   [ ] My code follows the style guidelines of this project.
-   [ ] I have performed a self-review of my own code.
-   [ ] I have commented my code, particularly in hard-to-understand areas.
-   [ ] I have made corresponding changes to the documentation (`docs/`).
-   [ ] My changes generate no new warnings.
-   [ ] New and existing unit tests pass locally with my changes.
