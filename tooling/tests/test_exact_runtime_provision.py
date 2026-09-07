from __future__ import annotations

import io
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from tooling.exact_runtime_provision import (
    ExactRuntimeProvisionError,
    main,
    runtime_environment,
    write_environment,
)
from tooling.exact_runtime_toolchains import load_manifest


class ExactRuntimeProvisionTests(unittest.TestCase):
    def test_environment_handoff_is_complete_and_stable(self) -> None:
        environment = runtime_environment(load_manifest())
        self.assertEqual(
            {
                "STRLING_CPYTHON_311_BINARY": (
                    "/opt/strling-toolchains/install/cpython-3.11.15/bin/python3.11"
                ),
                "STRLING_NODE_22_BINARY": "/opt/node-v22.23.2-linux-x64/bin/node",
                "STRLING_PCRE2_1042_LIBRARY": (
                    "/opt/pcre2-10.42-build-default/libpcre2-8.so.0.11.2"
                ),
                "STRLING_PCRE2_1043_LIBRARY": (
                    "/opt/pcre2-10.43-build-default/libpcre2-8.so.0.12.0"
                ),
            },
            environment,
        )

    def test_environment_file_is_sorted_and_append_only(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "github.env"
            path.write_text("EXISTING=value\n", encoding="utf-8")
            write_environment(path, {"ZETA": "/z", "ALPHA": "/a"})
            self.assertEqual(
                "EXISTING=value\nALPHA=/a\nZETA=/z\n",
                path.read_text(encoding="utf-8"),
            )

    def test_environment_file_rejects_line_injection(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "github.env"
            with self.assertRaises(ExactRuntimeProvisionError):
                write_environment(path, {"RUNTIME": "/safe\nUNSAFE=value"})
            self.assertFalse(path.exists())

    def test_environment_file_rejects_malformed_variable_name(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "github.env"
            with self.assertRaises(ExactRuntimeProvisionError):
                write_environment(path, {"RUNTIME=UNSAFE": "/safe"})
            self.assertFalse(path.exists())

    def test_execute_mode_hands_verified_environment_to_strict_audit(self) -> None:
        manifest = load_manifest()
        environment = runtime_environment(manifest)
        completed = mock.Mock(returncode=0)
        with (
            mock.patch("tooling.exact_runtime_provision.load_manifest", return_value=manifest),
            mock.patch(
                "tooling.exact_runtime_provision.verify_configured_runtimes",
                return_value={"toolchains": manifest["toolchains"]},
            ),
            mock.patch("tooling.exact_runtime_provision.subprocess.run", return_value=completed) as run,
            mock.patch("sys.argv", ["exact-runtime-provision", "--execute-adversarial"]),
            mock.patch("sys.stdout", new=io.StringIO()),
            mock.patch.dict(
                "tooling.exact_runtime_provision.os.environ", {}, clear=True
            ),
        ):
            self.assertEqual(0, main())
            command = run.call_args.args[0]
            self.assertIn("tooling.adversarial_semantic_audit", command)
            self.assertIn("--strict", command)
            self.assertIn("--output", command)
            for name, value in environment.items():
                self.assertEqual(value, run.call_args.kwargs["env"][name])


if __name__ == "__main__":
    unittest.main()
