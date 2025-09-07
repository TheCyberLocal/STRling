from .pattern import STRlingError, Pattern, lit
from STRling.core import nodes


def between(start: str, end: str, min_rep: int = None, max_rep: int = None):
    """
    Matches all characters within and including the start and end of a letter or digit range.

    Parameters:
    - start (str or int): The starting character or digit of the range.
    - end (str or int): The ending character or digit of the range.
    - min_rep (optional): Specifies the minimum digit of characters to match.
    - max_rep (optional): Specifies the maximum digit of characters to match.

    Returns:
    - An instance of the Pattern class.

    Examples:
        ```
        # Matches any digit from 0 to 9.
        my_pattern1 = s.between(0, 9)

        # Matches any lowercase letter from 'a' to 'z'.
        my_pattern2 = s.between('a', 'z')

        # Matches any uppercase letter from 'A' to 'Z'.
        my_pattern3 = s.between('A', 'Z')
        ```
    """

    if not (isinstance(start, str) and isinstance(end, str)) and not (isinstance(start, int) and isinstance(end, int)):
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

    node = nodes.CharClass(False, [nodes.ClassRange(start_char, end_char)])
    p = Pattern(node, custom_set=True)
    return p(min_rep, max_rep) if min_rep is not None else p


def not_between(start: str, end: str, min_rep: int = None, max_rep: int = None):
    """
    Matches any character not within or including the start and end of a letter or digit range.

    Parameters:
    - start (str or int): The starting character or digit of the range.
    - end (str or int): The ending character or digit of the range.
    - min_rep (optional): Specifies the minimum digit of characters to match.
    - max_rep (optional): Specifies the maximum digit of characters to match.

    Returns:
    - An instance of the Pattern class.

    Examples:
        ```
        # Matches any character that is not a digit from 0 to 9.
        my_pattern1 = s.not_between(0, 9)

        # Matches any character that is not a lowercase letter from 'a' to 'z'.
        my_pattern2 = s.not_between('a', 'z')

        # Matches any character that is not a uppercase letter from 'A' to 'Z'.
        my_pattern3 = s.not_between('A', 'Z')
        ```
    """

    if not (isinstance(start, str) and isinstance(end, str)) and not (isinstance(start, int) and isinstance(end, int)):
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

    node = nodes.CharClass(True, [nodes.ClassRange(start_char, end_char)])
    p = Pattern(node, custom_set=True, negated=True)
    return p(min_rep, max_rep) if min_rep is not None else p


def in_chars(*patterns):
    """
    Matches any provided patterns, but they can't include subpatterns.

    Parameters:
    - patterns (Pattern/str): One or more non-composite patterns to match.

    Returns:
    - An instance of the Pattern class.

    Examples:
        ```
        # Matches any letter, digit, comma, and period.
        my_pattern = s.in_chars(s.letter(), s.digit(), ',.')
        ```
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
        if hasattr(pattern.node, 'items'):
            items.extend(pattern.node.items)
        elif isinstance(pattern.node, nodes.Lit):
            for char in pattern.node.value:
                items.append(nodes.ClassLiteral(char))
        else:
            # For other node types, convert to string and add as literals
            pattern_str = str(pattern)
            for char in pattern_str:
                items.append(nodes.ClassLiteral(char))

    node = nodes.CharClass(False, items)
    return Pattern(node, custom_set=True)


def not_in_chars(*patterns):
    """
    Matches anything but the provided patterns, but they can't include subpatterns.

    Parameters:
    - patterns (Pattern/str): One or more non-composite patterns to avoid.

    Returns:
    - An instance of the Pattern class.

    Examples:
        ```
        # Matches any character that is not a letter, digit, comma, and period.
        my_pattern = s.not_in_chars(s.letter(), s.digit(), ',.')
        ```
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
        if hasattr(pattern.node, 'items'):
            items.extend(pattern.node.items)
        elif isinstance(pattern.node, nodes.Lit):
            for char in pattern.node.value:
                items.append(nodes.ClassLiteral(char))
        else:
            # For other node types, convert to string and add as literals
            pattern_str = str(pattern)
            for char in pattern_str:
                items.append(nodes.ClassLiteral(char))

    node = nodes.CharClass(True, items)
    return Pattern(node, custom_set=True, negated=True)
