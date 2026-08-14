"""Explicit transitional imports for P16-T04 editor features.

P16-T02 removes diagnostics and hover from this dependency. P16-T03 removes
completion, navigation, document symbols, and semantic tokens. Formatting and
code actions retain their legacy implementation until P16-T04 replaces them.
"""

from STRling.core.intelligence import format_pattern

__all__ = ["format_pattern"]
