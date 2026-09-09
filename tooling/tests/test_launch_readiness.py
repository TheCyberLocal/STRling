from __future__ import annotations

import datetime
import json
import re
import unittest
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[2]


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


class TargetProfileCurrencyTests(unittest.TestCase):
    def test_currency_review_is_complete_current_and_version_exact(self) -> None:
        currency = load_json(ROOT / "governance/target-profile-currency.json")
        self.assertEqual("1.0.0", currency["schema_version"])
        reviewed = datetime.date.fromisoformat(currency["reviewed_on"])
        age = datetime.date.today() - reviewed
        self.assertGreaterEqual(age.days, 0)
        self.assertLessEqual(age.days, currency["review_interval_days"])
        self.assertEqual(
            ["ecmascript", "pcre2", "python-re"],
            [entry["family"] for entry in currency["families"]],
        )
        governed = {
            reference
            for entry in currency["families"]
            for reference in entry["governed_profiles"]
        }
        profiles = []
        for path in sorted((ROOT / "spec/targets/profiles").glob("*.json")):
            profile = load_json(path)
            profiles.append(f"{profile['profile_id']}@{profile['profile_version']}")
        self.assertEqual(set(profiles), governed)
        for entry in currency["families"]:
            self.assertRegex(entry["latest_evidence"], r"^https://")
            self.assertNotEqual("", entry["rationale"].strip())
        python = next(
            entry for entry in currency["families"] if entry["family"] == "python-re"
        )
        self.assertEqual("3.11.16", python["governed_minor_latest_patch_observed"])
        self.assertRegex(
            python["governed_minor_latest_patch_evidence"], r"python-31116/"
        )

    def test_release_policy_names_current_profile_revisions(self) -> None:
        policy = load_json(ROOT / "governance/release-policy.json")
        claims = {
            claim["id"]: claim
            for claim in policy["support_claims"]
            if claim["dimension"] == "target-profile"
        }
        for path in sorted((ROOT / "spec/targets/profiles").glob("*.json")):
            profile = load_json(path)
            slug = path.stem
            claim = claims[f"target:{slug}"]
            self.assertIn(f"revision {profile['profile_version']}", claim["subject"])


class PublicCredibilityTests(unittest.TestCase):
    def test_binding_api_references_are_nonempty_and_reject_retired_guidance(
        self,
    ) -> None:
        documents = {
            language: (ROOT / f"bindings/{language}/docs/api_reference.md").read_text(
                encoding="utf-8"
            )
            for language in ("python", "lua", "typescript", "ruby")
        }
        for language, document in documents.items():
            with self.subTest(language=language):
                self.assertGreater(len(document.split()), 80)
                self.assertIn("CompileResult", document)
        self.assertNotIn("new RegExp(String(", documents["typescript"])
        self.assertNotIn("STRling::Simply", documents["ruby"])
        self.assertIn("public module name is `Strling`", documents["ruby"])

    def test_pull_request_workflow_provisions_and_reviews_dependencies(self) -> None:
        workflow_text = (ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")
        workflow = yaml.safe_load(workflow_text)
        jobs = workflow["jobs"]
        quality = jobs["quality-hardgates"]["steps"]
        quality_names = [step.get("name") for step in quality]
        provision = next(
            step
            for step in quality
            if step.get("name") == "Provision exact governed regex runtimes"
        )
        self.assertIn("exact_runtime_provision", provision["run"])
        dependency_workflow = yaml.safe_load(
            (ROOT / ".github/workflows/dependency-review.yml").read_text(
                encoding="utf-8"
            )
        )
        dependency = dependency_workflow["jobs"]["dependency-review"]
        action = dependency["steps"][-1]["uses"]
        self.assertRegex(
            action,
            r"^actions/dependency-review-action@[0-9a-f]{40}$",
        )
        interop_fetch = (
            "cargo +1.75.0 fetch --manifest-path bindings/interop/Cargo.toml "
            "--locked --target wasm32-unknown-unknown"
        )
        core_fetch = (
            "cargo +1.75.0 fetch --manifest-path core/internal/Cargo.toml --locked"
        )
        core_build = (
            "cargo +1.75.0 build --manifest-path core/internal/Cargo.toml "
            "--locked --bins"
        )
        native_interop = (
            "cargo +1.75.0 build --manifest-path bindings/interop/Cargo.toml "
            "-p strling-interop --locked"
        )
        self.assertIn(core_fetch, workflow_text)
        self.assertIn(core_build, workflow_text)
        self.assertIn(native_interop, workflow_text)
        self.assertIn(interop_fetch, workflow_text)
        self.assertLess(
            workflow_text.index(interop_fetch),
            workflow_text.index("./strling bootstrap all"),
        )
        self.assertLess(
            workflow_text.index(core_fetch),
            workflow_text.index("./strling bootstrap all"),
        )
        self.assertLess(
            workflow_text.index(core_build),
            workflow_text.index("./strling bootstrap all"),
        )
        self.assertLess(
            workflow_text.index(native_interop),
            workflow_text.index("./strling bootstrap all"),
        )
        self.assertIn('dotnet-version: "9.0.x"', workflow_text)
        self.assertEqual(2, workflow_text.count('java-version: "21.0.12+1"'))
        dotnet = load_json(ROOT / "global.json")["sdk"]
        self.assertEqual("9.0.100", dotnet["version"])
        self.assertEqual("latestFeature", dotnet["rollForward"])
        for required in (
            "libuv1-dev",
            "r-base-dev",
            "cpanminus",
            "PERL5LIB=$HOME/perl5/lib/perl5",
            "(cd bindings/jvm && mvn -B -DskipTests install)",
        ):
            self.assertIn(required, workflow_text)
        self.assertLess(
            workflow_text.index("(cd bindings/jvm && mvn -B -DskipTests install)"),
            workflow_text.index("./strling bootstrap all"),
        )
        clean_source = next(
            step
            for step in quality
            if step.get("name") == "Restore clean certification source"
        )
        self.assertIn("git restore --source=HEAD --worktree", clean_source["run"])
        self.assertIn("git diff --exit-code", clean_source["run"])
        self.assertIn(
            "git status --porcelain --untracked-files=all", clean_source["run"]
        )
        self.assertIn(
            "STRLING_MAVEN_REPOSITORY=$HOME/.m2/repository", clean_source["run"]
        )
        self.assertLess(
            quality_names.index("Install quality dependencies"),
            quality_names.index("Restore clean certification source"),
        )
        self.assertLess(
            quality_names.index("Restore clean certification source"),
            quality_names.index("Run canonical certification profile"),
        )
        ignore_text = (ROOT / ".gitignore").read_text(encoding="utf-8")
        self.assertIn(".lua/", ignore_text)
        self.assertIn(".luarocks/", ignore_text)
        matrix = jobs["test-matrix"]["steps"]
        matrix_names = [step.get("name") for step in matrix]
        self.assertLess(
            matrix_names.index("📦 Install Dependencies (Setup)"),
            matrix_names.index("🔎 Validate Toolchain"),
        )
        for required in (
            "🔧 Install Python",
            "🔧 Install Java",
            "🔧 Install Rust quality components",
            "🔧 Install Python native Rust toolchain",
            "🔧 Install TypeScript WASM toolchain",
            "🔧 Install Python quality tools",
            "🔧 Install TypeScript repository tools",
            "🔧 Install Perl dependencies",
            "🔧 Install JVM adapter dependency",
            "🔧 Prime Python native dependencies",
            "🔧 Prime TypeScript WASM build",
        ):
            self.assertIn(required, matrix_names)
        interop = jobs["interop-platform-certification"]["steps"]
        interop_names = [step.get("name") for step in interop]
        self.assertLess(
            interop_names.index("Prefetch locked interop dependencies"),
            interop_names.index("Certify native and raw WebAssembly boundary"),
        )
        self.assertLess(
            interop_names.index("Prefetch raw WebAssembly dependencies"),
            interop_names.index("Certify native and raw WebAssembly boundary"),
        )

    def test_python_lowering_documentation_covers_active_code_range(self) -> None:
        source = (ROOT / "core/src/python_re_lowering.rs").read_text(encoding="utf-8")
        codes = {
            int(value)
            for value in re.findall(r"STRL-PYTHON_RE_LOWERING-(\d{4})", source)
        }
        document = (ROOT / "docs/migration/python-re-target-lowering.md").read_text(
            encoding="utf-8"
        )
        self.assertEqual(set(range(1, 17)), codes)
        self.assertIn("through `0016`", document)


if __name__ == "__main__":
    unittest.main()
