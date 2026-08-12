from __future__ import annotations

import copy
import json
import tempfile
import unittest
from pathlib import Path

from tooling.pcre2_feature_probe import (
    PCRE2_MULTILINE,
    PCRE2_NEWLINE_ANY,
    PCRE2_UCP,
    PCRE2_UTF,
    canonical_digest,
    profile_configuration,
    run_probe,
)


ROOT = Path(__file__).resolve().parents[2]
PROFILE_1042 = ROOT / "spec" / "targets" / "profiles" / "pcre2-10.42.json"
PROFILE_1043 = ROOT / "spec" / "targets" / "profiles" / "pcre2-10.43.json"
CORPUS = ROOT / "tests" / "target" / "pcre2" / "versioned-features.json"


def load(path: Path) -> object:
    return json.loads(path.read_text(encoding="utf-8"))


class FakeEngine:
    expected_version = "10.43"

    def __init__(self, _library: Path):
        pass

    def version(self) -> str:
        return f"{self.expected_version} exact-test"

    def run_case(self, _pattern, observations, _configuration):
        return {"compile": "ok", "matches": list(observations)}


class Pcre2FeatureProbeTests(unittest.TestCase):
    def test_exact_profiles_map_only_explicit_options(self) -> None:
        earlier = profile_configuration(load(PROFILE_1042))
        modern = profile_configuration(load(PROFILE_1043))
        expected_flags = PCRE2_MULTILINE | PCRE2_UCP | PCRE2_UTF
        self.assertEqual(expected_flags, earlier.compile_options)
        self.assertEqual(expected_flags, modern.compile_options)
        self.assertEqual("pcre2_match", earlier.matcher_api)
        self.assertEqual(PCRE2_NEWLINE_ANY, earlier.newline)
        self.assertIsNone(earlier.maximum_variable_lookbehind)
        self.assertEqual(255, modern.maximum_variable_lookbehind)

    def test_unknown_or_implicit_profile_options_fail_closed(self) -> None:
        profile = load(PROFILE_1043)
        unknown = copy.deepcopy(profile)
        unknown["options"].append(
            {
                "option_id": "pcre2.jit",
                "stage": "runtime",
                "value": True,
                "selection": "profile_default",
            }
        )
        with self.assertRaisesRegex(ValueError, "unsupported PCRE2 probe option"):
            profile_configuration(unknown)

        implicit = copy.deepcopy(profile)
        next(
            option
            for option in implicit["options"]
            if option["option_id"] == "pcre2.matcher_api"
        )["value"] = "pcre2_dfa_match"
        with self.assertRaisesRegex(ValueError, "explicit pcre2.matcher_api"):
            profile_configuration(implicit)

    def test_shared_corpus_has_exact_profile_expectations(self) -> None:
        corpus = load(CORPUS)
        self.assertEqual(16, len(corpus["cases"]))
        self.assertEqual(["10.42", "10.43"], corpus["profiles"])
        self.assertEqual(
            len(corpus["cases"]),
            len({case["id"] for case in corpus["cases"]}),
        )
        for case in corpus["cases"]:
            self.assertTrue(case["pattern"])
            self.assertEqual({"10.42", "10.43"}, set(case["profiles"]))
            for expectation in case["profiles"].values():
                self.assertIn(expectation["status"], {"native", "unsupported"})
                self.assertIn(expectation["compile"], {"ok", "error"})
                if expectation["compile"] == "error":
                    self.assertEqual([], expectation["matches"])

    def test_probe_output_is_canonical_and_version_bound(self) -> None:
        fixture = {
            "corpus_version": "test",
            "profiles": ["10.43"],
            "cases": [
                {
                    "id": "one",
                    "pattern": "a",
                    "profiles": {
                        "10.43": {
                            "status": "native",
                            "compile": "ok",
                            "matches": [{"subject": "a", "matched": True}],
                        }
                    },
                }
            ],
        }
        with tempfile.TemporaryDirectory() as directory:
            temporary = Path(directory)
            fixture_path = temporary / "fixture.json"
            fixture_path.write_text(json.dumps(fixture), encoding="utf-8")
            library_path = temporary / "libpcre2-8.so"
            library_path.write_bytes(b"exact-library")
            first = run_probe(
                fixture_path,
                PROFILE_1043,
                library_path,
                engine_factory=FakeEngine,
            )
            second = run_probe(
                fixture_path,
                PROFILE_1043,
                library_path,
                engine_factory=FakeEngine,
            )
        self.assertEqual(first, second)
        self.assertEqual(first["result_sha256"], canonical_digest({
            key: value for key, value in first.items() if key != "result_sha256"
        }))
        self.assertEqual("profile:pcre2/10.43", first["profile"]["profile_id"])

        class WrongVersionEngine(FakeEngine):
            expected_version = "10.42"

        with tempfile.TemporaryDirectory() as directory:
            temporary = Path(directory)
            fixture_path = temporary / "fixture.json"
            fixture_path.write_text(json.dumps(fixture), encoding="utf-8")
            library_path = temporary / "libpcre2-8.so"
            library_path.write_bytes(b"wrong-library")
            with self.assertRaisesRegex(ValueError, "does not match"):
                run_probe(
                    fixture_path,
                    PROFILE_1043,
                    library_path,
                    engine_factory=WrongVersionEngine,
                )


if __name__ == "__main__":
    unittest.main()
