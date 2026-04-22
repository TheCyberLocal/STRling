"""Bundled ``pygls`` transport shim for the VS Code extension.

The runtime imports the concrete submodules directly; this package initializer
stays intentionally empty so static analysis does not need to resolve any
re-exported sibling modules.
"""
