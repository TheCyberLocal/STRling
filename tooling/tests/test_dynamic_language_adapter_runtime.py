from __future__ import annotations

import json
import os
import unittest

from tooling import dynamic_language_adapter_runtime as runtime


class DynamicLanguageAdapterRuntimeTests(unittest.TestCase):
    def test_governed_version_ranges_accept_certification_rows(self) -> None:
        runtime._assert_versions(
            {
                "ruby": "ruby 3.3.1",
                "php": "PHP 8.3.4",
                "perl": "v5.38.2",
                "lua": "Lua 5.4.7",
                "r": "Rscript (R) version 4.4.1",
            }
        )

    def test_governed_version_ranges_fail_closed(self) -> None:
        with self.assertRaisesRegex(runtime.DynamicLanguageRuntimeError, "outside"):
            runtime._assert_versions(
                {
                    "ruby": "ruby 2.7.8",
                    "php": "PHP 8.3.4",
                    "perl": "v5.38.2",
                    "lua": "Lua 5.4.7",
                    "r": "Rscript (R) version 4.4.1",
                }
            )

    def test_semantic_copy_denominator_is_fully_retired(self) -> None:
        self.assertEqual(83, runtime._semantic_copy_count())

    def test_probe_validates_request_utf8_and_returns_unicode(self) -> None:
        self.assertIn("strling_valid_utf8(input, input_len)", runtime.PROBE_SOURCE)
        self.assertIn(r"\xe9\x9b\xaa", runtime.PROBE_SOURCE)
        self.assertEqual({"unicode": "雪"}, runtime.EXPECTED_RESULT)

    def test_probe_tracks_release_per_calling_thread(self) -> None:
        self.assertIn("_Thread_local int outstanding", runtime.PROBE_SOURCE)
        self.assertNotIn("__sync_lock_test_and_set", runtime.PROBE_SOURCE)
        self.assertIn("STRLING_PROBE_RELEASE_STATUS", runtime.PROBE_SOURCE)
        self.assertIn("STRLING_PROBE_SPIN", runtime.PROBE_SOURCE)

    def test_observations_require_all_exact_operations(self) -> None:
        target = runtime.ROOT / "target"
        target.mkdir(exist_ok=True)
        binding = f"runtime-observation-test-{os.getpid()}"
        path = target / f"{binding}.json"
        try:
            observation = {
                operation: runtime.EXPECTED_RESULT for operation in runtime.OPERATIONS
            }
            path.write_text(
                json.dumps(observation, ensure_ascii=False), encoding="utf-8"
            )
            self.assertEqual(observation, runtime._read_observation(target, binding))
            observation.pop("compile")
            path.write_text(
                json.dumps(observation, ensure_ascii=False), encoding="utf-8"
            )
            with self.assertRaisesRegex(
                runtime.DynamicLanguageRuntimeError, "operation set"
            ):
                runtime._read_observation(target, binding)
            observation["compile"] = {"unicode": "drift"}
            path.write_text(
                json.dumps(observation, ensure_ascii=False), encoding="utf-8"
            )
            with self.assertRaisesRegex(runtime.DynamicLanguageRuntimeError, "drifted"):
                runtime._read_observation(target, binding)
        finally:
            path.unlink(missing_ok=True)


if __name__ == "__main__":
    unittest.main()
