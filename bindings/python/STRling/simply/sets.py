
from .pattern import STRlingError, Pattern, clean_params



############################
# User Char Sets
########


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
    - start (str or int): The starting character or number of the range.
    - end (str or int): The ending character or number of the range.
    - min_rep (optional): Specifies the minimum number of characters to match.
    - max_rep (optional): Specifies the maximum number of characters to match.

    Returns:
    - Pattern: A Pattern object representing the character or number range.

    Raises:
    - ValueError: If the range is invalid or if the types of start and end do not match.
    """

    # Verify start and end are both strings or integers
    if (not isinstance(start, str) or not isinstance(start, int)) and type(start) != type(end):
        problem = """
        Invalid Arguments Specified.
        """
        solution = """
        The `start` and `end` arguments must both be integers (0-9) or letters of the same case (A-Z or a-z).
        """
        raise STRlingError(problem, solution)

    # If start is int then end is int
    if isinstance(start, int):
        if start > end:
            problem = """
            Invalid Arguments Specified.
            """
            solution = """
            The `start` integer must not be greater than the `end` integer.
            """
            raise STRlingError(problem, solution)

        if not (0 <= start <= 9 and 0 <= end <= 9):
            problem = """
            Invalid Arguments Specified.
            """
            solution = """
            The `start` and `end` integers must be single digits (0-9).
            """
            raise STRlingError(problem, solution)

        new_pattern = f'[{start}-{end}]'

    # If start is string then end is string
    if isinstance(start, str):
        if not start.isalpha() or not end.isalpha():
            problem = """
            Invalid Arguments Specified.
            """
            solution = """
            The `start` and `end` strings must both be letters. To use integers ensure they are not strings. ('0' => 0)
            """
            raise STRlingError(problem, solution)

        if len(start) != 1 or len(end) != 1:
            problem = """
            Invalid Arguments Specified.
            """
            solution = """
            The `start` and `end` strings must be single characters.
            """
            raise STRlingError(problem, solution)

        if start.islower() != end.islower():
            problem = """
            Invalid Arguments Specified.
            """
            solution = """
            The `start` and `end` must be of the same case. (both uppercase or both lowercase)
            """
            raise STRlingError(problem, solution)

        if start > end:
            problem = """
            Invalid Arguments Specified.
            """
            solution = """
            The `start` string must not be lexicographically greater than `end`. (A-Z, not Z-A)
            """
            raise STRlingError(problem, solution)

        new_pattern = f'[{start}-{end}]'

    return Pattern(new_pattern, custom_set=True)(min_rep, max_rep)


def not_between(start: str, end: str, min_rep: int = None, max_rep: int = None):
    """
    Matches any character not within or including the start and end of a letter or number range.

    Examples:
        - Matches any character that is not a digit from 0 to 9.

        my_pattern1 = s.not_between(0, 9)

        - Matches any character that is not a lowercase letter from 'a' to 'z'.

        my_pattern2 = s.not_between('a', 'z')

        - Matches any character that is not a uppercase letter from 'A' to 'Z'.

        my_pattern3 = s.not_between('A', 'Z')

    Parameters:
    - start (str or int): The starting character or number of the range.
    - end (str or int): The ending character or number of the range.
    - min_rep (optional): Specifies the minimum number of characters to match.
    - max_rep (optional): Specifies the maximum number of characters to match.

    Returns:
    - Pattern: A Pattern object representing the negated character or number range.

    Raises:
    - ValueError: If the range is invalid or if the types of start and end do not match.
    """

    # Verify start and end are both strings or integers
    if (not isinstance(start, str) or not isinstance(start, int)) and type(start) != type(end):
        problem = """
        Invalid Arguments Specified.
        """
        solution = """
        The `start` and `end` arguments must both be integers (0-9) or letters of the same case (A-Z or a-z).
        """
        raise STRlingError(problem, solution)

    # If start is int then end is int
    if isinstance(start, int):
        if start > end:
            problem = """
            Invalid Arguments Specified.
            """
            solution = """
            The `start` integer must not be greater than the `end` integer.
            """
            raise STRlingError(problem, solution)

        if not (0 <= start <= 9 and 0 <= end <= 9):
            problem = """
            Invalid Arguments Specified.
            """
            solution = """
            The `start` and `end` integers must be single digits (0-9).
            """
            raise STRlingError(problem, solution)

        new_pattern = f'[^{start}-{end}]'

    # If start is string then end is string
    if isinstance(start, str):
        if not start.isalpha() or not end.isalpha():
            problem = """
            Invalid Arguments Specified.
            """
            solution = """
            The `start` and `end` strings must both be letters. To use integers ensure they are not strings. ('0' => 0)
            """
            raise STRlingError(problem, solution)

        if len(start) != 1 or len(end) != 1:
            problem = """
            Invalid Arguments Specified.
            """
            solution = """
            The `start` and `end` strings must be single characters.
            """
            raise STRlingError(problem, solution)

        if start.islower() != end.islower():
            problem = """
            Invalid Arguments Specified.
            """
            solution = """
            The `start` and `end` must be of the same case. (both uppercase or both lowercase)
            """
            raise STRlingError(problem, solution)

        if start > end:
            problem = """
            Invalid Arguments Specified.
            """
            solution = """
            The `start` string must not be lexicographically greater than `end`. (A-Z, not Z-A)
            """
            raise STRlingError(problem, solution)

        new_pattern = f'[^{start}-{end}]'

    return Pattern(new_pattern, custom_set=True, negated=True)(min_rep, max_rep)


def in_chars(*patterns):
    """
    Matches any provided patterns, but they can't include subpatterns.

    Example:
        - Matches any letter, digit, comma, and period.

        my_pattern = s.in_chars(s.letter(), s.digit(), ',.')

    Parameters:
    - patterns (Pattern/str): One or more patterns to match.

    Returns:
    - Pattern: A Pattern object that matches any of the given patterns.

    Raises:
    - ValueError: If any parameter is not an instance of Pattern or str.
    - ValueError: If any parameter is a composite pattern.

    Note: A composite pattern is one consisting of subpatterns,
    they are created by constructors and lookarounds.
    """

    clean_patterns = clean_params(*patterns)

    # All pattern must be non-composite
    if any(p.composite for p in clean_patterns):
        problem = """
        Cannot insert composite patterns into a character set.
        """
        solution = """
        Use `simply.any_of()` instead of `simply.in_chars()`.
        """
        raise STRlingError(problem, solution)

    joined = r''
    for pattern in clean_patterns:
        # All patterns must not have a specified range
        if len(str(pattern)) > 1 and str(pattern)[-1] == '}' and str(pattern)[-2] != "\\":
            problem = """
            Cannot add range to `simply.in_chars()`.
            """
            solution = """
            Remove the range on you pattern parameter.
            Example: `simply.letter(1, 2)` => `simply.letter()`
            """
            raise STRlingError(problem, solution)

        # Custom sets must be stripped of brackets and negated sets are not allowed
        if pattern.custom_set:
            if pattern.negated:
                problem = """
                Cannot add a negated set `simply.not_in_chars()` to a positive set `simply.in_chars()`.
                """
                solution = """
                If you want to match the parameters specified,
                consider putting the parameters of `simply.not_in_chars(*params)`
                directly into this `simply.in_chars(*params)` function.
                """
                raise STRlingError(problem, solution)
            else:
                joined += str(pattern)[1:-1] # [pattern] => pattern
        else: # Just the unbracketed add pattern
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
    - patterns (Pattern/str): One or more patterns to match.

    Returns:
    - Pattern: A Pattern object that matches any of the given patterns.

    Raises:
    - ValueError: If any parameter is not an instance of Pattern or str.
    - ValueError: If any parameter is a composite pattern.

    Note: A composite pattern is one consisting of subpatterns,
    they are created by constructors and lookarounds.
    """

    clean_patterns = clean_params(*patterns)

    # All pattern must be non-composite
    if any(p.composite for p in clean_patterns):
        problem = """
        Cannot insert composite patterns into a character set.
        """
        solution = """
        Use `simply.any_of()` instead of `simply.in_chars()`.
        """
        raise STRlingError(problem, solution)

    joined = r''
    for pattern in clean_patterns:
        # All patterns must not have a specified range
        if len(str(pattern)) > 1 and str(pattern)[-1] == '}' and str(pattern)[-2] != "\\":
            problem = """
            Cannot add range to `simply.in_chars()`.
            """
            solution = """
            Remove the range on you pattern parameter.
            Example: `simply.letter(1, 2)` => `simply.letter()`
            """
            raise STRlingError(problem, solution)
        if pattern.custom_set:
            if pattern.negated:
                joined += str(pattern)[2:-1] # [^pattern] => pattern
            else:
                joined += str(pattern)[1:-1] # [pattern] => pattern
        else: # Just the unbracketed add pattern
            joined += str(pattern)

    new_pattern = f'[^{joined}]'
    return Pattern(new_pattern, custom_set=True, negated=True)
