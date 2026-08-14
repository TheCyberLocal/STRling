"""Tests for canonical standard-library exact-runtime certification."""

from __future__ import annotations

import copy
import unittest
from unittest import mock

from tooling import stdlib_runtime_certification as certification
from tooling.stdlib_runtime_certification import (
    EXPECTED_APPLICATION_COUNTS,
    PCRE2_CERTIFICATION_LIMITS,
    EXPECTED_PROFILE_IDS,
    EXPECTED_RECORD_COUNTS,
    StdlibRuntimeError,
    _assert_pcre_match,
    _whole_value_match,
    canonical_digest,
    validate_contract,
    validate_projection,
)


class StdlibRuntimeCertificationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.validation = validate_contract()

    def projection(self) -> dict[str, object]:
        variants = []
        for entry in self.validation["contract"]["entries"]:
            applications = []
            for profile_id in EXPECTED_PROFILE_IDS:
                application = {
                    "artifact": {"pattern": {"flags": [], "text": "x"}},
                    "planned_status": "native",
                    "profile_id": profile_id,
                }
                if profile_id == "profile:python-re/3.11":
                    application["pattern_kind"] = "str"
                elif profile_id == "profile:python-re/3.11-bytes":
                    application["pattern_kind"] = "bytes"
                applications.append(application)
            variants.append(
                {
                    "applications": applications,
                    "helper_id": entry["helper_id"],
                    "variant_id": entry["variant_id"],
                }
            )
        base = {
            "contract_sha256": self.validation["contract_sha256"],
            "projection_version": "1.0.0",
            "registry_version": self.validation["contract"]["registry_version"],
            "variants": variants,
        }
        return {**base, "result_sha256": canonical_digest(base)}

    def test_exact_denominators_are_validated_without_runtime_access(self) -> None:
        self.assertEqual(EXPECTED_RECORD_COUNTS, self.validation["record_counts"])
        self.assertEqual(
            EXPECTED_APPLICATION_COUNTS, self.validation["application_counts"]
        )
        self.assertEqual(8, self.validation["variant_count"])

    def test_projection_requires_every_variant_and_profile_in_order(self) -> None:
        projection = self.projection()
        validate_projection(projection, self.validation)
        altered = copy.deepcopy(projection)
        altered["variants"][0]["applications"].pop()
        unsigned = dict(altered)
        unsigned.pop("result_sha256")
        altered["result_sha256"] = canonical_digest(unsigned)
        with self.assertRaisesRegex(StdlibRuntimeError, "profile denominator"):
            validate_projection(altered, self.validation)

    def test_projection_rejects_unsupported_canonical_artifacts(self) -> None:
        projection = self.projection()
        projection["variants"][0]["applications"][0]["planned_status"] = "unsupported"
        unsigned = dict(projection)
        unsigned.pop("result_sha256")
        projection["result_sha256"] = canonical_digest(unsigned)
        with self.assertRaisesRegex(StdlibRuntimeError, "not executable"):
            validate_projection(projection, self.validation)

    def test_whole_value_semantics_use_each_runtime_coordinate_system(self) -> None:
        subject = "a😀"
        self.assertTrue(
            _whole_value_match([{"span": [0, 3]}], subject, "utf16-code-units")
        )
        self.assertTrue(_whole_value_match([{"span": [0, 2]}], subject, "code-points"))
        self.assertTrue(_whole_value_match([{"span": [0, 5]}], subject, "utf8-bytes"))
        self.assertFalse(_whole_value_match([{"span": [0, 1]}], subject, "code-points"))

    def test_pcre_stress_limit_exceeds_the_oversized_fixture(self) -> None:
        self.assertEqual(100_000, PCRE2_CERTIFICATION_LIMITS.depth)
        self.assertGreater(
            PCRE2_CERTIFICATION_LIMITS.depth,
            len("a" * 10_000 + "@example.com"),
        )

    def test_pcre_runtime_limits_are_not_treated_as_non_matches(self) -> None:
        item = {
            "case_id": "email.oversized.local",
            "expected_match": True,
            "input": "a@example.com",
            "profile_id": "profile:pcre2/10.42",
        }
        with self.assertRaisesRegex(AssertionError, "depth_limit.*-53"):
            _assert_pcre_match(
                item,
                {"outcome": "depth_limit", "return_code": -53, "span": None},
            )

    def test_projection_environment_preserves_windows_linker_discovery(self) -> None:
        values = {
            "CARGO_TARGET_DIR": "target-path",
            "INCLUDE": "include-path",
            "LIB": "library-path",
            "LIBPATH": "managed-library-path",
            "PATH": "executable-path",
            "SYSTEMROOT": "windows-root",
            "TEMP": "temporary-path",
            "TMP": "temporary-path",
        }
        with mock.patch.object(certification.os, "name", "nt"):
            with mock.patch.dict(certification.os.environ, values, clear=True):
                environment = certification._projection_environment()
        self.assertEqual(values, {key: environment[key] for key in values})
        self.assertEqual("C.UTF-8", environment["LANG"])
        self.assertEqual("C.UTF-8", environment["LC_ALL"])
        self.assertEqual("UTC", environment["TZ"])


if __name__ == "__main__":
    unittest.main()
