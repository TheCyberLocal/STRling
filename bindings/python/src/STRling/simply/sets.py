"""
Character set and range functions for pattern matching in STRling.

This module provides functions for creating character class patterns, including
ranges (between), custom sets (custom_set), and utilities for combining sets.
Character sets are fundamental building blocks for matching specific groups of
characters, and these functions make it easy to define complex character matching
rules without dealing with raw regex character class syntax.
"""

from __future__ import annotations

from .pattern import STRlingError, Pattern, lit
from STRling.core import nodes


def between(
    start: str | int,
    end: str | int,
    min_rep: int | None = None,
    max_rep: int | None = None,
) -> Pattern:
    """
    Matches characters within a specified range (e.g., 'a' to 'z' or 0 to 9).

    Creates a character class that matches any character between and including
    the start and end characters. The range must be either digits (0-9) or
    letters of the same case (A-Z or a-z).

    Parameters
    ----------
    start : str or int
        The starting character or digit of the range. Must be a single character
        or digit 0-9.
    end : str or int
        The ending character or digit of the range. Must be a single character
        or digit 0-9, and must not be less than start.
    min_rep : int, optional
        Minimum number of characters to match. If None, matches exactly once.
    max_rep : int, optional
        Maximum number of characters to match. Use 0 for unlimited. If None,
        matches exactly min_rep times.

    Returns
    -------
    Pattern
        A new Pattern object representing the character range.

    Examples
    --------
    Simple Use: Match digits 0-9
        >>> import STRling.simply as s
        >>> import re
        >>> pattern = s.between(0, 9)
        >>> bool(re.search(str(pattern), '5'))
        True

    Advanced Use: Match lowercase vowels with repetition
        >>> vowels = s.between('a', 'e')  # matches a, b, c, d, e
        >>> pattern = s.merge(s.between('a', 'z', 3, 5))  # 3-5 lowercase letters
        >>> bool(re.match(str(pattern), 'abc'))
        True
        >>> bool(re.match(str(pattern), 'abcdef'))
        True

    Raises
    ------
    STRlingError
        If start and end are not both integers or both letters of same case,
        if start > end, or if values are out of valid range.

    Notes
    -----
    Both start and end must be:
    - Either both integers in range 0-9
    - Or both single letters of the same case (both uppercase or both lowercase)

    The range is inclusive on both ends. For example, `between('a', 'c')` matches
    'a', 'b', and 'c'.

    See Also
    --------
    not_between : For matching characters outside a range
    in_chars : For matching specific characters (not a range)
    """

    if not (isinstance(start, str) and isinstance(end, str)) and not (
        isinstance(start, int) and isinstance(end, int)
    ):
        message = """
        Method: simply.between(start, end)

        The 'start' and 'end' arguments must both be integers (0-9) or letters of the same case (A-Z or a-z).
        """
        raise STRlingError(message)

    if isinstance(start, int):
        if start > end:
            message = """
            Method: simply.between(start, end)

            The 'start' integer must not be greater than the 'end' integer.
            """
            raise STRlingError(message)

        if not (0 <= start <= 9 and 0 <= end <= 9):
            message = """
            Method: simply.between(start, end)

            The 'start' and 'end' integers must be single digits (0-9).
            """
            raise STRlingError(message)

        start_char = str(start)
        end_char = str(end)
    else:
        if not start.isalpha() or not end.isalpha():
            message = """
            Method: simply.between(start, end)

            The 'start' and 'end' must be alphabetical characters.
            """
            raise STRlingError(message)

        if len(start) != 1 or len(end) != 1:
            message = """
            Method: simply.between(start, end)

            The 'start' and 'end' characters must be single letters.
            """
            raise STRlingError(message)

        if start.islower() != end.islower():
            message = """
            Method: simply.between(start, end)

            The 'start' and 'end' characters must be of the same case.
            """
            raise STRlingError(message)

        if start > end:
            message = """
            Method: simply.between(start, end)

            The 'start' character must not be lexicographically greater than the 'end' character.
            """
            raise STRlingError(message)

        start_char = start
        end_char = end

    node = nodes.CharacterClass(False, [nodes.ClassRange(start_char, end_char)])
    p = Pattern(node, custom_set=True)
    return p(min_rep, max_rep) if min_rep is not None else p


def not_between(
    start: str | int,
    end: str | int,
    min_rep: int | None = None,
    max_rep: int | None = None,
) -> Pattern:
    """
    Matches characters outside a specified range (inverse of between).

    Creates a negated character class that matches any character NOT between
    the start and end characters (inclusive). The range must be either digits
    (0-9) or letters of the same case (A-Z or a-z).

    Parameters
    ----------
    start : str or int
        The starting character or digit of the range to exclude. Must be a
        single character or digit 0-9.
    end : str or int
        The ending character or digit of the range to exclude. Must be a
        single character or digit 0-9, and must not be less than start.
    min_rep : int, optional
        Minimum number of characters to match. If None, matches exactly once.
    max_rep : int, optional
        Maximum number of characters to match. Use 0 for unlimited. If None,
        matches exactly min_rep times.

    Returns
    -------
    Pattern
        A new Pattern object representing the negated character range.

    Examples
    --------
    Simple Use: Match non-digits
        >>> import STRling.simply as s
        >>> import re
        >>> pattern = s.not_between(0, 9)
        >>> bool(re.search(str(pattern), 'A'))
        True
        >>> bool(re.search(str(pattern), '5'))
        False

    Advanced Use: Match characters that are not vowels
        >>> not_vowels = s.not_between('a', 'e')  # excludes a, b, c, d, e
        >>> pattern = s.not_between('a', 'z', 1, 0)  # One or more non-lowercase
        >>> bool(re.match(str(pattern), 'ABC'))
        True

    Raises
    ------
    STRlingError
        If start and end are not both integers or both letters of same case,
        if start > end, or if values are out of valid range.

    Notes
    -----
    This is the inverse of `between()`. It matches any character that is NOT
    in the specified range. For example, `not_between('a', 'c')` matches any
    character except 'a', 'b', and 'c'.

    See Also
    --------
    between : For matching characters within a range
    not_in_chars : For excluding specific characters (not a range)
    """

    if not (isinstance(start, str) and isinstance(end, str)) and not (
        isinstance(start, int) and isinstance(end, int)
    ):
        message = """
        Method: simply.not_between(start, end)

        The 'start' and 'end' arguments must both be integers (0-9) or letters of the same case (A-Z or a-z).
        """
        raise STRlingError(message)

    if isinstance(start, int):
        if start > end:
            message = """
            Method: simply.not_between(start, end)

            The 'start' integer must not be greater than the 'end' integer.
            """
            raise STRlingError(message)

        if not (0 <= start <= 9 and 0 <= end <= 9):
            message = """
            Method: simply.not_between(start, end)

            The 'start' and 'end' integers must be single digits (0-9).
            """
            raise STRlingError(message)

        start_char = str(start)
        end_char = str(end)
    else:
        if not start.isalpha() or not end.isalpha():
            message = """
            Method: simply.not_between(start, end)

            The 'start' and 'end' must be alphabetical characters.
            """
            raise STRlingError(message)

        if len(start) != 1 or len(end) != 1:
            message = """
            Method: simply.not_between(start, end)

            The 'start' and 'end' characters must be single letters.
            """
            raise STRlingError(message)

        if start.islower() != end.islower():
            message = """
            Method: simply.not_between(start, end)

            The 'start' and 'end' characters must be of the same case.
            """
            raise STRlingError(message)

        if start > end:
            message = """
            Method: simply.not_between(start, end)

            The 'start' character must not be lexicographically greater than the 'end' character.
            """
            raise STRlingError(message)

        start_char = start
        end_char = end

    node = nodes.CharacterClass(True, [nodes.ClassRange(start_char, end_char)])
    p = Pattern(node, custom_set=True, negated=True)
    return p(min_rep, max_rep) if min_rep is not None else p


def in_chars(*patterns: Pattern | str) -> Pattern:
    """
    Matches any one of the specified characters or character classes.

    Creates a character class containing all provided patterns. Patterns must be
    non-composite (individual characters or character sets), not complex patterns
    with subpatterns.

    Parameters
    ----------
    *patterns : Pattern or str
        One or more non-composite patterns to include in the character class.
        Strings are automatically converted to literal patterns.

    Returns
    -------
    Pattern
        A new Pattern object representing the character class.

    Examples
    --------
    Simple Use: Match letters, digits, or punctuation
        >>> import STRling.simply as s
        >>> import re
        >>> pattern = s.in_chars(s.letter(), s.digit(), ',.')
        >>> bool(re.search(str(pattern), 'A'))
        True
        >>> bool(re.search(str(pattern), '5'))
        True
        >>> bool(re.search(str(pattern), ','))
        True

    Advanced Use: Build a custom identifier character set
        >>> # Allow letters, digits, underscore, and hyphen
        >>> id_chars = s.in_chars(s.letter(), s.digit(), '_-')
        >>> identifier = s.merge(s.letter(), id_chars.rep(0, 0))
        >>> bool(re.match(str(identifier), 'my_id-123'))
        True

    Raises
    ------
    STRlingError
        If any parameter is not a Pattern or string, or if any pattern is
        composite (contains subpatterns).

    Notes
    -----
    All patterns must be non-composite. This means you cannot use `in_chars()`
    with patterns like `s.merge()`, `s.capture()`, or `s.any_of()`. Use only
    simple character sets like `s.letter()`, `s.digit()`, or literal strings.

    This is similar to a character class `[abc]` in traditional regex, where
    you specify individual characters to match.

    See Also
    --------
    not_in_chars : For matching characters NOT in the set
    between : For matching a range of characters
    any_of : For alternation between composite patterns
    """

    # Check all patterns are instance of Pattern or str
    clean_patterns = []
    for pattern in patterns:
        if isinstance(pattern, str):
            pattern = lit(pattern)

        if not isinstance(pattern, Pattern):
            message = """
            Method: simply.in_chars(*patterns)

            The parameters must be instances of `Pattern` or `str`.

            Use a string such as "123abc$" to match literal characters, or use a predefined set like `simply.letter()`.
            """
            raise STRlingError(message)

        clean_patterns.append(pattern)

    if any(p.composite for p in clean_patterns):
        message = """
        Method: simply.in_chars(*patterns)

        All patterns must be non-composite.
        """
        raise STRlingError(message)

    items = []
    for pattern in clean_patterns:
        # Extract items from pattern's node
        if hasattr(pattern.node, "items"):
            items.extend(pattern.node.items)
        elif isinstance(pattern.node, nodes.Literal):
            for char in pattern.node.value:
                items.append(nodes.ClassLiteral(char))
        else:
            # For other node types, convert to string and add as literals
            pattern_str = str(pattern)
            for char in pattern_str:
                items.append(nodes.ClassLiteral(char))

    node = nodes.CharacterClass(False, items)
    return Pattern(node, custom_set=True)


def not_in_chars(*patterns: Pattern | str) -> Pattern:
    """
    Matches any character NOT in the specified set (negated character class).

    Creates a negated character class that matches any character that is NOT
    one of the provided patterns. Patterns must be non-composite (individual
    characters or character sets), not complex patterns with subpatterns.

    Parameters
    ----------
    *patterns : Pattern or str
        One or more non-composite patterns to exclude from matches. Strings
        are automatically converted to literal patterns.

    Returns
    -------
    Pattern
        A new Pattern object representing the negated character class.

    Examples
    --------
    Simple Use: Match anything except letters, digits, and punctuation
        >>> import STRling.simply as s
        >>> import re
        >>> pattern = s.not_in_chars(s.letter(), s.digit(), ',.')
        >>> bool(re.search(str(pattern), '@'))
        True
        >>> bool(re.search(str(pattern), 'A'))
        False

    Advanced Use: Validate input contains only allowed characters
        >>> # Ensure no special characters in username
        >>> allowed = s.merge(s.in_chars(s.alpha_num(), '_-'), s.rep(0, 0))
        >>> forbidden = s.not_in_chars(s.alpha_num(), '_-')
        >>> has_forbidden = s.has(forbidden)

    Raises
    ------
    STRlingError
        If any parameter is not a Pattern or string, or if any pattern is
        composite (contains subpatterns).

    Notes
    -----
    All patterns must be non-composite. This means you cannot use `not_in_chars()`
    with patterns like `s.merge()`, `s.capture()`, or `s.any_of()`. Use only
    simple character sets like `s.letter()`, `s.digit()`, or literal strings.

    This is similar to a negated character class `[^abc]` in traditional regex,
    which matches any character except those listed.

    See Also
    --------
    in_chars : For matching characters in the set
    not_between : For excluding a range of characters
    """

    # Check all patterns are instance of Pattern or str
    clean_patterns = []
    for pattern in patterns:
        if isinstance(pattern, str):
            pattern = lit(pattern)

        if not isinstance(pattern, Pattern):
            message = """
            Method: simply.not_in_chars(*patterns)

            The parameters must be instances of `Pattern` or `str`.

            Use a string such as "123abc$" to match literal characters, or use a predefined set like `simply.letter()`.
            """
            raise STRlingError(message)

        clean_patterns.append(pattern)

    if any(p.composite for p in clean_patterns):
        message = """
        Method: simply.not_in_chars(*patterns)

        All patterns must be non-composite.
        """
        raise STRlingError(message)

    items = []
    for pattern in clean_patterns:
        # Extract items from pattern's node
        if hasattr(pattern.node, "items"):
            items.extend(pattern.node.items)
        elif isinstance(pattern.node, nodes.Literal):
            for char in pattern.node.value:
                items.append(nodes.ClassLiteral(char))
        else:
            # For other node types, convert to string and add as literals
            pattern_str = str(pattern)
            for char in pattern_str:
                items.append(nodes.ClassLiteral(char))

    node = nodes.CharacterClass(True, items)
    return Pattern(node, custom_set=True, negated=True)
