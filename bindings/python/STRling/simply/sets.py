
from .pattern import Pattern



############################
# User Char Sets
########


def between(start: str, end: str, min: int = None, max: int = None):
    """
    Creates a Pattern object for a range of characters.

    Parameters:
         - start (str or int): The starting character or number of the range.
         - end (str or int): The ending character or number of the range.
         - min (optional): Specifies the minimum number of characters to match.
         - max (optional): Specifies the maximum number of characters to match.

    Returns:
        Pattern: A Pattern object representing the character or number range.

    Raises:
        ValueError: If the range is invalid or if the types of start and end do not match.
    """
    if (not isinstance(start, str) or not isinstance(start, int)) and type(start) != type(end):
        raise ValueError("The `start` and `end` characters both be integers or strings.")

    elif isinstance(start, int) and isinstance(end, int):
        if start > end:
            raise ValueError("The `start` integer must not be greater than the `end` integer.")
        if not (0 <= start <= 9 and 0 <= end <= 9):
            raise ValueError("The `start` and `end` integers must be single digits (0-9).")
        new_pattern = f'[{start}-{end}]'

    elif isinstance(start, str) and isinstance(end, str):
        if start.isalpha() and end.isalpha():
            if len(start) != 1 or len(end) != 1:
                raise ValueError("The `start` and `end` strings must be single characters.")
            if start.islower() != end.islower():
                raise ValueError("The `start` and `end` must be of the same case. (both uppercase or both lowercase)")
            if start > end:
                raise ValueError("The `start` string must not be lexicographically greater than `end`. (A-Z, not Z-A)")
            new_pattern = f'[{start}-{end}]'
        else:
            raise ValueError("The strings `start` and `end` must both be letters. To use integers ensure they are not strings. ('0' => 0)")

    else:
        raise ValueError("Invalid range specified. Both start and end must be integers or letters of the same case.")

    return Pattern(new_pattern, custom_set=True)(min, max)


def not_between(start: str, end: str, min: int = None, max: int = None):
    """
    Creates a Pattern object for a negated range of characters.

    Parameters:
         - start (str or int): The starting character or number of the range.
         - end (str or int): The ending character or number of the range.
         - min (optional): Specifies the minimum number of characters to match.
         - max (optional): Specifies the maximum number of characters to match.

    Returns:
        Pattern: A Pattern object representing the negated character or number range.

    Raises:
        ValueError: If the range is invalid or if the types of start and end do not match.
    """
    if (not isinstance(start, str) or not isinstance(start, int)) and type(start) != type(end):
        raise ValueError("The `start` and `end` characters both be integers or strings.")

    elif isinstance(start, int) and isinstance(end, int):
        if start > end:
            raise ValueError("The `start` integer must not be greater than the `end` integer.")
        if not (0 <= start <= 9 and 0 <= end <= 9):
            raise ValueError("The `start` and `end` integers must be single digits (0-9).")
        new_pattern = f'[{start}-{end}]'

    elif isinstance(start, str) and isinstance(end, str):
        if start.isalpha() and end.isalpha():
            if len(start) != 1 or len(end) != 1:
                raise ValueError("The `start` and `end` strings must be single characters.")
            if start.islower() != end.islower():
                raise ValueError("The `start` and `end` must be of the same case. (both uppercase or both lowercase)")
            if start > end:
                raise ValueError("The `start` string must not be lexicographically greater than `end`. (A-Z, not Z-A)")
            new_pattern = f'[{start}-{end}]'
        else:
            raise ValueError("The strings `start` and `end` must both be letters. To use integers ensure they are not strings. ('0' => 0)")

    else:
        raise ValueError("Invalid range specified. Both start and end must be integers or letters of the same case.")

    return Pattern(new_pattern, custom_set=True, negated_set=True)(min, max)


def in_(*patterns):
    """
    Creates a Pattern object that matches any of the given patterns.

    Parameters:
        patterns (Pattern): One or more Pattern objects to match.

    Returns:
        Pattern: A Pattern object that matches any of the given patterns.

    Raises:
        ValueError: If any parameter is not an instance of Pattern or if a composite pattern is included.
        Note: A composite pattern is a pattern created by merge, capture, or group.
    """

    # All patterns must be instances of Pattern
    if not all(isinstance(pattern, Pattern) for pattern in patterns):
        msg = (
        """
        Problem:
            One or more parameters are not an instance of Pattern.

        Solution:
            Use `simply.lit('abc123$')` to match literal characters,
            or use a predefined set like `simply.letters()` as a parameter.
        """)
        raise ValueError(msg)

    # All pattern must be non-composite
    if any(pattern.composite for pattern in patterns if isinstance(pattern, Pattern)):
        msg = (
        """
        Problem:
            One or more parameters are composite
            (a pattern formed by group, merge, or capture),
            these cannot be inserted into a character set.

        Solution:
            Choose non-composite patterns as parameters.
        """)
        raise ValueError(msg)

    joined = r''
    for pattern in patterns:
        # All patterns must have a specified range
        if len(str(pattern)) > 1 and str(pattern)[-1] == '}' and str(pattern)[-2] != "\\":
            msg = (
            """
            Problem:
                The in_ method cannot take patterns with specified range.

            Solution:
                Remove the range on you pattern parameter.
                Example: `simply.letter(1, 2)` => `simply.letter()`
            """)
            raise ValueError(msg)
        if pattern.custom_set:
            joined += str(pattern)[1:-1]
        else:
            joined += str(pattern)

    new_pattern = f'[{joined}]'
    return Pattern(new_pattern, custom_set=True)(min, max)

def not_in(*patterns):
    """
    """
    if not all(isinstance(pattern, Pattern) for pattern in patterns):
        msg = (
        """
        Problem:
            All parameters must be instances of Pattern.

        Solution:
            Use `simply.lit('abc123$')` to match literal characters,
            or use a predefined set like `simply.letters()` as a parameter.
        """)
        raise ValueError(msg)

    if any(pattern.composite for pattern in patterns if isinstance(pattern, Pattern)):
        msg = (
        """
        Problem:
            One or more parameters is a composite pattern
            (an instance of the methods group, merge, or capture),
            these cannot be inserted into a character set.

        Solution:
            Choose non-composite patterns as parameters.
        """)
        raise ValueError(msg)

    joined = r''
    for pattern in patterns:
        if len(str(pattern)) > 1 and str(pattern)[-1] == '}' and str(pattern)[-2] != "\\":
            raise ValueError('The not_in method cannot take patterns with specified range.')
        if pattern.custom_set:
            joined += str(pattern)[1:-1]
        else:
            joined += str(pattern)

    new_pattern = f'[{joined}]'
    return Pattern(new_pattern, custom_set=True)(min, max)
