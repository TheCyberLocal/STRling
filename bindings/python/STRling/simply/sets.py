
from .pattern import STRlingError, Pattern, lit



############################
# User Char Sets
########


def nums(start: int, end: int, min_rep: int = None, max_rep: int = None):
    """
    Matches all positive integers within and including the start and end of a number range.

    Examples:
        - Matches any number from 0 to 255.

        my_pattern1 = s.between(0, 255)

        - Matches any uppercase letter from 10 to 20.

        my_pattern2 = s.between(10, 20)

    Parameters:
    - start (str or int): The starting character or digit of the range.
    - end (str or int): The ending character or digit of the range.
    - min_rep (optional): Specifies the minimum digit of characters to match.
    - max_rep (optional): Specifies the maximum digit of characters to match.

    Returns:
    - Pattern: A Pattern object representing a positive integer range.
    """
    if not (isinstance(start, int) and isinstance(end, int)):
        message = """
        Method: simply.nums(start, end)

        The `start` and `end` arguments must both be positive integers (0+).
        """
        raise STRlingError(message)

    if start > end:
        message = """
        Method: simply.nums(start, end)

        The `start` integer must not be greater than the `end` integer.
        """
        raise STRlingError(message)

    # Matching 0-255, (?:25[0-5]|2[0-4][0-9]|1[0-9]{2}|[1-9][0-9]|[0-9])
    # Matching 0-255, (?:2[0-5]{2}|1[0-9]{2}|[1-9][0-9]|[0-9])

    # Matching 0-10000, (?:10000|[1-9][0-9]{3}|[1-9][0-9]{2}|[1-9][0-9]|[0-9])
    # Matching 0-1000,  (?:1000|[1-9][0-9]{2}|[1-9][0-9]|[0-9])
    # Matching 0-100,   (?:100|[1-9][0-9]|[0-9])
    # Matching 0-10,    (?:10|[0-9])

    # Matching 1000-10000, (?:10000|[1-9][0-9]{3})
    # Matching 100-10000, (?:10000|[1-9][0-9]{3}|[1-9][0-9]{2})
    # Matching 100-1000,(?:1000|[1-9][0-9]{2})
    # Matching 10-100,  (?:100|[1-9][0-9])

    # Matching 0-14567, (?:1[0-4][0-5][0-6][0-7]|[1-9][0-9]{3}|[1-9][0-9]{2}|[1-9][0-9]|[0-9])
    # Matching 0-1456, (?:1[0-4][0-5][0-6]|[1-9][0-9]{2}|[1-9][0-9]|[0-9])
    # Matching 0-155, (?:1[0-5]{2}|[1-9][0-9]|[1-9][0-9]|[0-9])
    # Matching 0-7456, (?:7[0-4][0-5][0-6]|[1-6][0-9]{3}|[1-9][0-9]{2}|[1-9][0-9]|[0-9])

    # Matching 155-14567, (?:1[0-4][0-5][0-6][0-7]|[1-9][0-9]{3}|[2-9][0-9]{2}|1[6-9][0-9]|15[5-9])
    # Matching 256-1456, (?:1[0-4][0-5][0-6]|[2-9][5-9][6-9])
    # Matching 123-158, (?:1[2-5][3-8])
    # Matching 567-7456, (?:7[0-4][0-5][0-6]|[1-6][0-9]{3}|[5-9][6-9][7-9])

    # For traversing the logic from an end to 0 is as follows:
    # Matching 0-87654 can be broken down into matching 80000-87654 and 0-79999.
    # Matching 80000-87654, (?:8765[0-4]|876[0-5][0-9]|87[0-6][0-9]{2}|8[0-7][0-9]{3}).
    # Matching 0-79999 can be broken down into matching 10000-79999, 1000-9999, 100-999, 10-99, and 0-9.
    # Matching 0-79999, (?:[1-7][0-9]{4}|[1-9][0-9]{3}|[1-9][0-9]{2}|[1-9][0-9]|[0-9]).

    if start != 0:
        raise ValueError("start must be 0 for testing.")

    start, end = str(start), str(end)
    for i in range(1, len(end)):
        const_for_upper_bound = end[0:-i]
        flexible_range = f"[0-{end[-i]}]"

        range_gap = i - 1
        if range_gap > 0:
            flexible_range += "[0-9]"
        if range_gap > 1:
            flexible_range += f"{{{range_gap}}}"

        # 8765 [0-4] 0
        # 876 [0-5][0-9] 1
        # 87 [0-6][0-9]{2} 2
        # 8 [0-7][0-9]{3} 3

        print(const_for_upper_bound, flexible_range, range_gap)


def between(start: str, end: str, min_rep: int = None, max_rep: int = None):
    """
    Matches all characters within and including the start and end of a letter or number range.

    Examples:
        - Matches any digit from 0 to 9.

        my_pattern1 = s.between(0, 9)

        - Matches any lowercase letter from 'a' to 'z'.

        my_pattern2 = s.between('a', 'z')

        - Matches any uppercase letter from 'A' to 'Z'.

        my_pattern3 = s.between('A', 'Z')

    Parameters:
    - start (str or int): The starting character or digit of the range.
    - end (str or int): The ending character or digit of the range.
    - min_rep (optional): Specifies the minimum digit of characters to match.
    - max_rep (optional): Specifies the maximum digit of characters to match.

    Returns:
    - Pattern: A Pattern object representing the character or digit range.
    """

    if not (isinstance(start, str) and isinstance(end, str)) and not (isinstance(start, int) and isinstance(end, int)):
        message = """
        Method: simply.between(start, end)

        The `start` and `end` arguments must both be integers (0-9) or letters of the same case (A-Z or a-z).
        """
        raise STRlingError(message)

    if isinstance(start, int):
        if start > end:
            message = """
            Method: simply.between(start, end)

            The `start` integer must not be greater than the `end` integer.
            """
            raise STRlingError(message)

        if not (0 <= start <= 9 and 0 <= end <= 9):
            message = """
            Method: simply.between(start, end)

            The `start` and `end` integers must be single digits (0-9).
            """
            raise STRlingError(message)

        new_pattern = f'[{start}-{end}]'

    if isinstance(start, str):
        if not start.isalpha() or not end.isalpha():
            message = """
            Method: simply.between(start, end)

            The `start` and `end` must be alphabetical characters.
            """
            raise STRlingError(message)

        if len(start) != 1 or len(end) != 1:
            message = """
            Method: simply.between(start, end)

            The `start` and `end` characters must be single letters.
            """
            raise STRlingError(message)

        if start.islower() != end.islower():
            message = """
            Method: simply.between(start, end)

            The `start` and `end` characters must be of the same case.
            """
            raise STRlingError(message)

        if start > end:
            message = """
            Method: simply.between(start, end)

            The `start` character must not be lexicographically greater than the `end` character.
            """
            raise STRlingError(message)

        new_pattern = f'[{start}-{end}]'

    return Pattern(new_pattern, custom_set=True)(min_rep, max_rep)


def not_between(start: str, end: str, min_rep: int = None, max_rep: int = None):
    """
    Matches any character not within or including the start and end of a letter or digit range.

    Examples:
        - Matches any character that is not a digit from 0 to 9.

        my_pattern1 = s.not_between(0, 9)

        - Matches any character that is not a lowercase letter from 'a' to 'z'.

        my_pattern2 = s.not_between('a', 'z')

        - Matches any character that is not a uppercase letter from 'A' to 'Z'.

        my_pattern3 = s.not_between('A', 'Z')

    Parameters:
    - start (str or int): The starting character or digit of the range.
    - end (str or int): The ending character or digit of the range.
    - min_rep (optional): Specifies the minimum digit of characters to match.
    - max_rep (optional): Specifies the maximum digit of characters to match.

    Returns:
    - Pattern: A Pattern object representing the negated character or digit range.
    """

    if not (isinstance(start, str) and isinstance(end, str)) and not (isinstance(start, int) and isinstance(end, int)):
        message = """
        Method: simply.not_between(start, end)

        The `start` and `end` arguments must both be integers (0-9) or letters of the same case (A-Z or a-z).
        """
        raise STRlingError(message)

    if isinstance(start, int):
        if start > end:
            message = """
            Method: simply.not_between(start, end)

            The `start` integer must not be greater than the `end` integer.
            """
            raise STRlingError(message)

        if not (0 <= start <= 9 and 0 <= end <= 9):
            message = """
            Method: simply.not_between(start, end)

            The `start` and `end` integers must be single digits (0-9).
            """
            raise STRlingError(message)

        new_pattern = f'[^{start}-{end}]'

    if isinstance(start, str):
        if not start.isalpha() or not end.isalpha():
            message = """
            Method: simply.not_between(start, end)

            The `start` and `end` must be alphabetical characters.
            """
            raise STRlingError(message)

        if len(start) != 1 or len(end) != 1:
            message = """
            Method: simply.not_between(start, end)

            The `start` and `end` characters must be single letters.
            """
            raise STRlingError(message)

        if start.islower() != end.islower():
            message = """
            Method: simply.not_between(start, end)

            The `start` and `end` characters must be of the same case.
            """
            raise STRlingError(message)

        if start > end:
            message = """
            Method: simply.not_between(start, end)

            The `start` character must not be lexicographically greater than the `end` character.
            """
            raise STRlingError(message)

        new_pattern = f'[^{start}-{end}]'

    return Pattern(new_pattern, custom_set=True, negated=True)(min_rep, max_rep)


def in_chars(*patterns):
    """
    Matches any provided patterns, but they can't include subpatterns.

    Example:
        - Matches any letter, digit, comma, and period.

        my_pattern = s.in_chars(s.letter(), s.digit(), ',.')

    Parameters:
    - patterns (Pattern/str): One or more non-composite patterns to match.

    Returns:
    - Pattern: A Pattern object that matches any of the given patterns.
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

    joined = r''
    for pattern in clean_patterns:
        if len(str(pattern)) > 1 and str(pattern)[-1] == '}' and str(pattern)[-2] != "\\":
            message = """
            Method: simply.in_chars(*patterns)

            Patterns must not have specified ranges.
            """
            raise STRlingError(message)

        if pattern.custom_set:
            if pattern.negated:
                message = """
                Method: simply.in_chars(*patterns)

                To match the characters specified in a negated set, move the parameters directly into simply.in_chars(*patterns).

                Example: simply.in_chars(simply.not_in_chars(*patterns)) => simply.in_chars(*patterns)
                """
                raise STRlingError(message)
            else:
                joined += str(pattern)[1:-1]  # [pattern] => pattern
        else:
            joined += str(pattern)

    new_pattern = f'[{joined}]'
    return Pattern(new_pattern, custom_set=True)

def not_in_chars(*patterns):
    """
    Matches anything but the provided patterns, but they can't include subpatterns.

    Example:

        - Matches any character that is not a letter, digit, comma, and period.

        my_pattern = s.not_in_chars(s.letter(), s.digit(), ',.')

    Parameters:
    - patterns (Pattern/str): One or more non-composite patterns to avoid.

    Note: A composite pattern is one consisting of subpatterns,
    they are created by constructors and lookarounds.

    Returns:
    - Pattern: A Pattern object that matches any of the given patterns.
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

    joined = r''
    for pattern in clean_patterns:
        if len(str(pattern)) > 1 and str(pattern)[-1] == '}' and str(pattern)[-2] != "\\":
            message = """
            Method: simply.not_in_chars(*patterns)

            Patterns must not have specified ranges.
            """
            raise STRlingError(message)

        if pattern.custom_set:
            if pattern.negated:
                joined += str(pattern)[2:-1]  # [^pattern] => pattern
            else:
                joined += str(pattern)[1:-1]  # [pattern] => pattern
        else:
            joined += str(pattern)

    new_pattern = f'[^{joined}]'
    return Pattern(new_pattern, custom_set=True, negated=True)
