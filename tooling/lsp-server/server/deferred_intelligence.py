"""Explicit transitional imports for P16-T03/P16-T04 editor features.

P16-T02 removes diagnostics and hover from this dependency. Completion,
navigation, semantic tokens, formatting, and code actions retain their legacy
implementation until their ordered tasks replace them.
"""

from STRling.core.intelligence import (  # noqa: F401
    SEMANTIC_TOKEN_MODIFIERS,
    SEMANTIC_TOKEN_TYPES,
    extract_document_symbols,
    find_registry_definition,
    format_pattern,
    get_completion_items,
    tokenize_pattern,
)

__all__ = [
    "SEMANTIC_TOKEN_MODIFIERS",
    "SEMANTIC_TOKEN_TYPES",
    "extract_document_symbols",
    "find_registry_definition",
    "format_pattern",
    "get_completion_items",
    "tokenize_pattern",
]
