"""Setuptools hook that embeds the governed native interop library in wheels."""

from __future__ import annotations

import subprocess
import sys
import sysconfig
from pathlib import Path

from setuptools import setup
from setuptools.command.build_py import build_py
from wheel.bdist_wheel import bdist_wheel


class BuildWithNativeInterop(build_py):
    def run(self) -> None:
        super().run()
        output = Path(self.build_lib) / "STRling" / "_native"
        subprocess.run(
            [
                sys.executable,
                str(Path(__file__).with_name("scripts") / "assemble_native.py"),
                "--output",
                str(output),
            ],
            check=True,
        )


class PlatformInteropWheel(bdist_wheel):
    def finalize_options(self) -> None:
        super().finalize_options()
        self.root_is_pure = False

    def get_tag(self):
        return "py3", "none", sysconfig.get_platform().replace("-", "_")


setup(
    cmdclass={
        "bdist_wheel": PlatformInteropWheel,
        "build_py": BuildWithNativeInterop,
    },
    zip_safe=False,
)
