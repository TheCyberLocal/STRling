"""Setuptools hook that embeds the governed native interop library in wheels."""

from __future__ import annotations

import shutil
import subprocess
import sys
import sysconfig
from pathlib import Path

from setuptools import setup
from setuptools.command.build_py import build_py
from setuptools.command.sdist import sdist
from wheel.bdist_wheel import bdist_wheel


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
NATIVE_SOURCE_PATHS = (
    Path("bindings/interop/Cargo.lock"),
    Path("bindings/interop/Cargo.toml"),
    Path("bindings/interop/fuzz/Cargo.toml"),
    Path("bindings/interop/fuzz/fuzz_targets"),
    Path("bindings/interop/src"),
    Path("core/internal/Cargo.lock"),
    Path("core/internal/Cargo.toml"),
    Path("core/src"),
    Path("spec/interop/1.0/abi.json"),
    Path("spec/portability/equivalence/1.0"),
    Path("spec/stdlib/registry/1.0/canonical-semantics.json"),
    Path("spec/targets/profiles/ecmascript-2024.json"),
    Path("spec/targets/profiles/pcre2-10.42.json"),
    Path("spec/targets/profiles/pcre2-10.43.json"),
    Path("spec/targets/profiles/python-re-3.11-bytes.json"),
    Path("spec/targets/profiles/python-re-3.11.json"),
    Path("tests/conformance/ecmascript-runtime-certification.json"),
    Path("tests/conformance/pcre2-runtime-certification.json"),
    Path("tests/conformance/python-re-runtime-certification.json"),
)


class SdistWithNativeSource(sdist):
    """Embed the exact governed Rust source needed to rebuild the native wheel."""

    def make_release_tree(self, base_dir: str, files: list[str]) -> None:
        super().make_release_tree(base_dir, files)
        release_root = Path(base_dir)
        shutil.copy2(REPOSITORY_ROOT / "LICENSE", release_root / "LICENSE")
        native_root = release_root / "_native_source"
        for relative in NATIVE_SOURCE_PATHS:
            source = REPOSITORY_ROOT / relative
            destination = native_root / relative
            if source.is_dir():
                shutil.copytree(source, destination)
            else:
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source, destination)


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
        "sdist": SdistWithNativeSource,
    },
    zip_safe=False,
)
