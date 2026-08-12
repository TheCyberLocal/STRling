from __future__ import annotations

import copy
import importlib
import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

reference = importlib.import_module("tooling.legacy_reference.python_reference")


def request(
    operation: str = "parser.parse",
    *,
    input_value: dict[str, str] | None = None,
    options: dict[str, object] | None = None,
) -> dict[str, object]:
    spec = reference.OPERATION_SPECS[operation]
    key = spec["input"]
    return {
        "expected_legacy_surface": spec["surface"],
        "input": input_value or {key: "a"},
        "kind": reference.REQUEST_KIND,
        "operation": operation,
        "options": options or {},
        "protocol_version": reference.PROTOCOL_VERSION,
    }


class PythonReferenceProtocolTests(unittest.TestCase):
    def test_canonical_json_is_recursive_utf8_and_normalizes_negative_zero(
        self,
    ) -> None:
        self.assertEqual(
            reference.canonical_json(
                {"z": -0.0, "a": {"unicode": "λ", "array": [3, {"b": 2, "a": 1}]}}
            ),
            '{"a":{"array":[3,{"a":1,"b":2}],"unicode":"λ"},"z":0}',
        )

    def test_valid_request_is_copied_and_surface_is_runner_owned(self) -> None:
        raw = request()
        validated = reference.validate_request(raw)
        self.assertEqual(validated, raw)
        self.assertIsNot(validated, raw)

        wrong_surface = request()
        wrong_surface["expected_legacy_surface"] = "typescript.core.parser.parse"
        with self.assertRaisesRegex(
            reference.ProtocolError, "requires expected historical surface"
        ):
            reference.validate_request(wrong_surface)

    def test_malformed_and_unknown_requests_are_protocol_failures(self) -> None:
        missing = request()
        del missing["options"]
        with self.assertRaises(reference.ProtocolError) as missing_error:
            reference.validate_request(missing)
        self.assertEqual(missing_error.exception.code, "INVALID_SHAPE")

        unknown = request()
        unknown["operation"] = "unknown.operation"
        with self.assertRaises(reference.ProtocolError) as unknown_error:
            reference.validate_request(unknown)
        self.assertEqual(unknown_error.exception.code, "UNKNOWN_OPERATION")

    def test_implementation_identity_is_bounded_stable_and_sensitive(self) -> None:
        first = reference.create_implementation_identity(python_version="3.12.0")
        second = reference.create_implementation_identity(python_version="3.12.0")
        self.assertEqual(first, second)
        self.assertRegex(first["fingerprint"], r"^sha256:[0-9a-f]{64}$")
        paths = [entry["path"] for entry in first["inputs"]]
        self.assertIn("bindings/python/src/STRling/core/parser.py", paths)
        self.assertIn("bindings/python/pyproject.toml", paths)
        self.assertIn("bindings/python/requirements.txt", paths)
        self.assertNotIn("tooling/legacy_reference/python_reference.py", paths)
        self.assertFalse(any(path.startswith("bindings/typescript/") for path in paths))

        changed = copy.deepcopy(first["inputs"])
        changed[0]["sha256"] = "0" * 64
        self.assertNotEqual(
            reference.fingerprint_implementation_manifest(first["inputs"], "3.12.0"),
            reference.fingerprint_implementation_manifest(changed, "3.12.0"),
        )

    def test_parser_success_and_failure_are_faithful_observations(self) -> None:
        successful = reference.observe_request(
            request(input_value={"source": "(?<name>[a-z]+)"})
        )
        self.assertEqual(successful["runner"], reference.RUNNER)
        self.assertEqual(successful["outcome"]["status"], "success")
        self.assertEqual(successful["outcome"]["evidence"]["return_shape"], "tuple")

        failed = reference.observe_request(request(input_value={"source": "(abc"}))
        self.assertEqual(failed["outcome"]["status"], "legacy_failure")
        failure = failed["outcome"]["failure"]
        self.assertEqual(failure["class"], "STRlingParseError")
        self.assertEqual(failure["stage"], "parser")
        self.assertIn("formatted", failure)
        self.assertNotIn("stack", failure)

    def test_compiler_metadata_and_emitter_diagnostics_are_observed(self) -> None:
        compiled = reference.observe_request(
            request(
                "compiler.compile_with_metadata",
                input_value={"source": "(?<name>a)(?<=b)c++\\k<name>"},
            )
        )
        self.assertEqual(compiled["outcome"]["status"], "success")
        self.assertIn(
            "features_used",
            compiled["outcome"]["evidence"]["metadata"],
        )

        emitted = reference.observe_request(
            request(
                "emitter.pcre2.emit_with_diagnostics",
                input_value={"source": "(a+)+"},
            )
        )
        self.assertEqual(emitted["outcome"]["status"], "success")
        self.assertEqual(
            emitted["outcome"]["evidence"]["warnings"][0]["code"],
            "REDOS_RISK",
        )

    def test_pipeline_failures_retain_the_throwing_stage(self) -> None:
        parse_failure = reference.observe_request(
            request(
                "compiler.compile",
                input_value={"source": "a(b"},
            )
        )
        self.assertEqual(parse_failure["outcome"]["failure"]["stage"], "parser")

        emitter_failure = reference.observe_request(
            request(
                "emitter.pcre2.emit",
                input_value={"source": "(?<=a+)b"},
            )
        )
        self.assertEqual(emitter_failure["outcome"]["failure"]["stage"], "emitter")
        self.assertEqual(
            emitter_failure["outcome"]["failure"]["code"],
            "VLB_NOT_SUPPORTED",
        )

    def test_python_simply_shape_is_not_rewritten_as_typescript(self) -> None:
        observation = reference.observe_request(
            request(
                "api.simply.literal_to_string",
                input_value={"literal": "a.b"},
            )
        )
        evidence = observation["outcome"]["evidence"]
        self.assertEqual(evidence["return_shape"], "str")
        self.assertEqual(evidence["emitted_pattern"], r"a\.b")
        self.assertIn("named_groups", evidence)
        self.assertNotIn("namedGroups", evidence)

    def test_not_exposed_operations_are_unsupported_observations(self) -> None:
        raw = request("api.root.parse", input_value={"source": "a"})
        snapshot = copy.deepcopy(raw)
        observation = reference.observe_request(raw)
        self.assertEqual(raw, snapshot)
        self.assertEqual(
            observation["outcome"],
            {
                "reason": (
                    "the historical Python package root exports simply but not parse"
                ),
                "status": "unsupported",
            },
        )

    def test_repeat_observation_is_byte_identical(self) -> None:
        identity = reference.create_implementation_identity(python_version="3.12.0")
        raw = request(input_value={"source": "%flags im\na"})
        first = reference.observe_request(raw, implementation=identity)
        second = reference.observe_request(raw, implementation=identity)
        self.assertEqual(
            reference.canonical_line(first),
            reference.canonical_line(second),
        )


class PythonReferenceCorpusTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.corpus = reference.load_corpus()
        cls.certification = reference.certify_corpus()

    def test_corpus_is_source_authored_and_covers_all_operations(self) -> None:
        self.assertEqual(len(self.corpus["cases"]), 20)
        operations = {entry["request"]["operation"] for entry in self.corpus["cases"]}
        self.assertEqual(operations, set(reference.OPERATION_IDS))
        self.assertEqual(len({entry["id"] for entry in self.corpus["cases"]}), 20)

    def test_three_runs_are_deterministic_and_immutable(self) -> None:
        self.assertEqual(self.certification["status"], "passed")
        self.assertEqual(
            self.certification["repeatability"],
            {
                "canonical_batches_compared": 3,
                "canonical_observations_compared": 60,
                "mismatches": 0,
                "repeat_runs": 3,
            },
        )
        self.assertEqual(
            self.certification["fixture_immutability"],
            {
                "corpus_unchanged": True,
                "governed_implementation_inputs_unchanged": True,
            },
        )
        self.assertEqual(self.certification["unexplained_failures"], 0)

    def test_outcomes_and_malformed_cases_are_contained(self) -> None:
        self.assertEqual(
            self.certification["outcome_counts"],
            {"legacy_failure": 4, "success": 12, "unsupported": 4},
        )
        self.assertEqual(self.certification["malformed_cases"], 2)
        self.assertTrue(
            all(
                summary["repeat_equivalent"]
                for summary in self.certification["case_summaries"]
            )
        )

    def test_canonical_certification_has_independent_versions(self) -> None:
        self.assertEqual(reference.PROTOCOL_VERSION, "1.0.0")
        self.assertEqual(reference.OBSERVATION_SCHEMA_VERSION, "1.1.0")
        self.assertEqual(reference.CORPUS_VERSION, "1.0.0")
        self.assertEqual(reference.BATCH_SCHEMA_VERSION, "1.1.0")
        self.assertEqual(reference.CERTIFICATION_SCHEMA_VERSION, "1.1.0")
        self.assertTrue(reference.canonical_line(self.certification).endswith("\n"))

    def test_cli_contains_malformed_json(self) -> None:
        completed = subprocess.run(
            [
                sys.executable,
                str(Path(__file__).parents[1] / "python_reference.py"),
            ],
            cwd=ROOT,
            input="{",
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(completed.returncode, 2)
        failure = json.loads(completed.stderr)
        self.assertEqual(failure["kind"], reference.PROTOCOL_FAILURE_KIND)
        self.assertEqual(failure["error"]["code"], "MALFORMED_JSON")
        self.assertEqual(completed.stdout, "")


if __name__ == "__main__":
    unittest.main()
