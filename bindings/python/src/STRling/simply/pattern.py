"""
Core Pattern class and error types for STRling.

This module defines the fundamental Pattern class that represents all STRling
patterns, along with the STRlingError exception class and compilation utilities.
The Pattern class provides chainable methods for applying quantifiers, repetitions,
and other modifiers to patterns. It serves as the foundation for all pattern
construction in the Simply API, wrapping internal AST nodes and providing a
user-friendly interface for pattern manipulation and compilation.
"""

from __future__ import annotations

import textwrap
import json
from STRling.core import nodes
from typing import Any, Dict, Optional, Union
from STRling.core.compiler import Compiler
from STRling.emitters.pcre2 import emit as emit_pcre2


class Simply:
    """
    Central manager for pattern compilation and emission.

    This internal class handles the compilation pipeline, transforming Pattern
    objects through the AST -> IR -> emitted regex string stages.
    """

    def __init__(self) -> None:
        self.compiler = Compiler()

    def build(
        self,
        pattern_obj: Pattern,
        flags: Optional[Union[Dict[str, bool], Any]] = None,
    ) -> str:
        """
        Compile a Pattern object's node to a regex string.

        Args:
            pattern_obj: The Pattern object to compile.
            flags: Optional regex flags to apply.

        Returns:
            The compiled regex string in PCRE2 format.
        """
        ir_root = self.compiler.compile(pattern_obj.node)
        return emit_pcre2(ir_root, flags)


# Global instance for use throughout the library
s = Simply()


class STRlingError(ValueError):
    """
    Custom error class for STRling pattern errors.

    This error class provides formatted, user-friendly error messages when invalid
    patterns are constructed or invalid arguments are provided to pattern functions.
    Error messages are automatically formatted with consistent indentation for
    better readability in console output.
    """

    def __init__(self, message: str) -> None:
        """
        Create a new STRlingError with formatted message.

        Args:
            message: The error message (can be multiline and will be reformatted).
        """
        self.message = textwrap.dedent(message).strip().replace("\n", "\n\t")
        super().__init__(self.message)

    def __str__(self) -> str:
        """
        Return the formatted error message with header and indentation.

        Returns:
            Formatted error message string.
        """
        return f"\n\nSTRlingError: Invalid Pattern Attempted.\n\n\t{self.message}"


def lit(text: str) -> Pattern:
    """
    Create a literal pattern from a string.

    This function wraps a plain string in a Pattern object, treating all characters
    as literals (no special regex meaning). It's the foundation for mixing literal
    text with pattern-based matching.

    Args:
        text: The text to use as a literal.

    Returns:
        A Pattern object representing the literal text.

    Examples:
        Simple Use: Match literal text
            >>> import STRling.simply as s
            >>> pattern = s.lit('hello')
            >>> bool(re.search(str(pattern), 'hello world'))
            True

        Advanced Use: Combine literal with patterns
            >>> email = s.merge(
            ...     s.letter(1, 0),
            ...     s.lit('@'),
            ...     s.letter(1, 0),
            ...     s.lit('.'),
            ...     s.letter(2, 4)
            ... )

    See Also:
        Pattern : The Pattern class that wraps all patterns
        merge : For combining multiple patterns
    """
    # Create a Literal node instead of escaping text
    return Pattern(nodes.Literal(text))


def repeat(min_rep: int | None = None, max_rep: int | None = None) -> str:
    if min_rep is not None and max_rep is not None:
        if max_rep == 0:
            return f"{{{min_rep},}}"
        if min_rep > max_rep:
            message = """
            Method: Pattern.__call__(min_rep, max_rep)

            The `min_rep` must not be greater than the `max_rep`.

            Ensure the lesser number is on the left and the greater number is on the right.
            """
            raise STRlingError(message)
        return f"{{{min_rep},{max_rep}}}"
    elif min_rep is not None:
        return f"{{{min_rep}}}"
    else:
        return ""


class Pattern:
    """
    A class to construct and compile clean and manageable regex expressions.

    Attributes:
        - node: The AST node representing this pattern piece
        - custom_set (bool): Indicates if the pattern is a custom character set.
        - negated (bool): Indicates if the pattern is a negated custom character set.
        - composite (bool): Indicates if the pattern is a composite pattern.
        - named_groups (list): Indicates the list of named groups within.
        - numbered_group (bool): Indicates if the pattern is a numbered group.
    """

    def __init__(
        self,
        node: nodes.Node,
        custom_set: bool = False,
        negated: bool = False,
        composite: bool = False,
        named_groups: list[str] | None = None,
        numbered_group: bool = False,
    ) -> None:
        # Store the AST node instead of a string pattern
        self.node = node
        # Keep compatibility attributes for now
        self.custom_set = custom_set
        self.negated = negated
        self.composite = composite
        self.named_groups = named_groups or []
        self.numbered_group = numbered_group

    def __call__(
        self, min_rep: int | None = None, max_rep: int | None = None
    ) -> "Pattern":
        """
        Applies a repetition pattern to the current pattern.

        Parameters: (min_rep/exact_rep, max_rep)
        - min_rep (optional): Specifies the minimum number of characters to match.
        - max_rep (optional): Specifies the maximum number of characters to match, 0 means unlimited, None means match exact count of min_rep.

        Returns:
        - A new Pattern object with the repetition pattern applied.
        """
        # Prevent errors if invoked with no range. For numbered (captured)
        # groups we require an explicit count -- calling without args is invalid.
        if min_rep is None and max_rep is None:
            if self.numbered_group:
                message = """
                Method: Pattern.__call__(min_rep, max_rep)

                Numbered (captured) groups require an explicit exact count.

                Provide an integer value like my_capture(3) not my_capture().
                """
                raise STRlingError(message)
            return self

        # If min_rep or max_rep are specified out of valid range
        if min_rep is not None and min_rep < 0 or max_rep is not None and max_rep < 0:
            message = """
            Method: Pattern.__call__(min_rep, max_rep)

            The `min_rep` and `max_rep` must be 0 or greater.
            """
            raise STRlingError(message)

        # Named group is unique and not repeatable
        if self.named_groups and min_rep is not None and max_rep is not None:
            message = """
            Method: Pattern.__call__(min_rep, max_rep)

            Named groups cannot be repeated as they must be unique.

            Consider using an unlabeled group (merge) or a numbered group (capture).
            """
            raise STRlingError(message)

        # A group already assigned a specified range cannot be reassigned
        if isinstance(self.node, nodes.Quantifier):
            message = """
            Method: Pattern.__call__(min_rep, max_rep)

            Cannot re-invoke pattern to specify range that already exists.

            Examples of invalid syntax:
                simply.letter(1, 2)(3, 4) # double invoked range is invalid
                my_pattern = simply.letter(1, 2) # my_pattern was set range (1, 2) # valid
                my_new_pattern = my_pattern(3, 4) # my_pattern was reinvoked (3, 4) # invalid

            Set the range on the first invocation, don't reassign it.

            Examples of valid syntax:
                You can either specify the range now:
                    my_pattern = simply.letter(1, 2)

                Or you can specify the range later:
                    my_pattern = simply.letter() # my_pattern was never assigned a range
                    my_new_pattern = my_pattern(1, 2) # my_pattern was invoked with (1, 2) for the first time.
            """
            raise STRlingError(message)

        # Create Quantifier node instead of appending a string
        if self.numbered_group:
            if max_rep is not None:
                message = """
                Method: Pattern.__call__(min_rep, max_rep)

                The `max_rep` parameter was specified when capture takes only one parameter, the exact number of copies.

                Consider using an unlabeled group (merge) for a range.
                """
                raise STRlingError(message)
            else:
                # Must have an exact integer count for numbered groups
                if min_rep is None:
                    message = """
                    Method: Pattern.__call__(min_rep, max_rep)

                    Numbered (captured) groups require an explicit exact count.

                    Provide an integer value like my_capture(3) not my_capture().
                    """
                    raise STRlingError(message)

                # Handle numbered groups by duplicating the node the exact count
                # (safe because min_rep is validated to be int above)
                children: list[nodes.Node] = [self.node] * min_rep
                new_node = nodes.Sequence(children)
                return self.create_modified_instance(new_node)
        else:
            # Regular case: create a quantifier node
            # If caller only provided max_rep but not min_rep, treat min as 0
            q_min: int = min_rep if min_rep is not None else 0
            q_max: Union[int, str] = (
                "Inf" if max_rep == 0 else max_rep if max_rep is not None else q_min
            )
            new_node = nodes.Quantifier(
                child=self.node, min=q_min, max=q_max, mode="Greedy"
            )
            return self.create_modified_instance(new_node)

    def __str__(self) -> str:
        """
        Returns the compiled regex string.
        """
        return s.build(self)

    def exec(self, text_to_search: str, target: str = "python") -> str:
        # 1. Load the feature matrix
        with open("spec/features.json") as f:
            feature_matrix: Dict[str, Dict[str, bool]] = json.load(f)

        # 2. Get the full artifact from the compiler
        compiler = Compiler()
        artifact: Dict[str, Any] = compiler.compile_with_metadata(self.node)
        features: list[str] = artifact.get("metadata", {}).get("features_used", [])

        # 3. Check for unsupported features
        unsupported = [
            f for f in features if not feature_matrix.get(f, {}).get(target, False)
        ]

        if unsupported:
            # 4. FALLBACK PATH: Use a WASM engine
            print(f"INFO: Using WASM fallback for features: {unsupported}")
            ir_root = artifact.get("ir")
            pcre2_regex_str = emit_pcre2(ir_root)  # type: ignore[arg-type]
            # return pcre2_wasm_engine.search(pcre2_regex_str, text_to_search)
            # For now, we can just show it would happen:
            return f"WASM_EXEC: '{pcre2_regex_str}' on '{text_to_search}'"
        else:
            # 5. NATIVE PATH: Use Python's `re` module
            # Note: This requires a new emitter for Python's regex syntax.
            # python_regex_str = emit_python_re(artifact["ir"])
            # return re.search(python_regex_str, text_to_search)
            # For now, we can simulate:
            ir_root = artifact.get("ir")
            pcre2_simulated_str = emit_pcre2(ir_root)  # type: ignore[arg-type]
            return f"NATIVE_EXEC: '{pcre2_simulated_str}' on '{text_to_search}'"

    @classmethod
    def create_modified_instance(cls, new_node: nodes.Node, **kwargs: Any) -> "Pattern":
        """
        Returns a copy of the pattern instance with a new node.
        """
        return cls(new_node, **kwargs)
