from __future__ import annotations

import copy
import tempfile
import unittest
from pathlib import Path

from tooling.exact_runtime_toolchains import (
    ExactRuntimeToolchainError,
    load_manifest,
    strategy_fingerprints,
    validate_manifest,
)


class ExactRuntimeToolchainsTests(unittest.TestCase):
    def test_current_manifest_is_valid(self) -> None:
        manifest = load_manifest()
        self.assertEqual("1.0.0", manifest["schema_version"])
        self.assertEqual(
            2,
            manifest["toolchains"]["cpython-3.11.15"]["reproducibility"][
                "identical_clean_builds"
            ],
        )

    def test_identity_and_reproducibility_mutations_fail_closed(self) -> None:
        manifest = load_manifest()
        mutations = []
        missing = copy.deepcopy(manifest)
        del missing["toolchains"]["pcre2-10.43"]
        mutations.append(missing)
        bad_hash = copy.deepcopy(manifest)
        bad_hash["toolchains"]["cpython-3.11.15"]["artifact"]["sha256"] = "0" * 63
        mutations.append(bad_hash)
        single_build = copy.deepcopy(manifest)
        single_build["toolchains"]["cpython-3.11.15"]["reproducibility"][
            "identical_clean_builds"
        ] = 1
        mutations.append(single_build)
        wrong_source = copy.deepcopy(manifest)
        wrong_source["toolchains"]["pcre2-10.42"]["source"]["commit"] = "0" * 40
        mutations.append(wrong_source)
        for mutation in mutations:
            with (
                self.subTest(mutation=mutation),
                self.assertRaises(ExactRuntimeToolchainError),
            ):
                validate_manifest(mutation)

    def test_loader_rejects_non_object(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "manifest.json"
            path.write_text("[]\n", encoding="utf-8")
            with self.assertRaises(ValueError):
                load_manifest(path)

    def test_current_rewrite_strategy_fingerprints_are_canonical(self) -> None:
        fingerprints = strategy_fingerprints()
        self.assertEqual(
            {
                "rewrite.atomic_literal.elide.v1",
                "rewrite.repeat_exactly_once.elide.v1",
            },
            set(fingerprints),
        )
        self.assertTrue(all(len(value) == 64 for value in fingerprints.values()))


if __name__ == "__main__":
    unittest.main()
