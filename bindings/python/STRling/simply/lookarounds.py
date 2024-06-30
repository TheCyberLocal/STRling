
from .pattern import STRlingError, Pattern, lit



############################
# Lookarounds
########


def ahead(pattern):
    """
    A positive lookahead checks for the presence of the specified pattern after the current position without including it in the result.

    Example: simply as s
        - Only matches a digit followed by a letter.

        my_pattern = s.merge(s.digit(), s.ahead(s.letter()))

    Parameters:
    - pattern (Pattern/str): The pattern to look ahead for.

    Returns:
    - Pattern: A Pattern object representing the positive lookahead.
    """

    if isinstance(pattern, str):
        pattern = lit(pattern)

    if not isinstance(pattern, Pattern):
        message = """
        Method: simply.ahead(pattern)

        The parameter must be an instance of `Pattern` or `str`.

        Use a string such as "123abc$" to match literal characters, or use a predefined set like `simply.letter()`.
        """
        raise STRlingError(message)

    return Pattern(f'(?={pattern})', composite=True)

def not_ahead(pattern):
    """
    A negative lookahead checks for the absence of the specified pattern after the current position without including it in the result.

    Example: simply as s
        - Only matches a digit if not followed by a letter.

        my_pattern = s.merge(s.digit(), s.not_ahead(s.letter()))

    Parameters:
    - pattern (Pattern/str): The pattern to look ahead for and ensure is absent.

    Returns:
    - Pattern: A Pattern object representing the negative lookahead.
    """

    if isinstance(pattern, str):
        pattern = lit(pattern)

    if not isinstance(pattern, Pattern):
        message = """
        Method: simply.not_ahead(pattern)

        The parameter must be an instance of `Pattern` or `str`.

        Use a string such as "123abc$" to match literal characters, or use a predefined set like `simply.letter()`.
        """
        raise STRlingError(message)

    return Pattern(f'(?!{pattern})', composite=True)

def behind(pattern):
    """
    A positive lookbehind checks for the presence of the specified pattern before the current position without including it in the result.

    Example: simply as s
        - Only matches a letter preceded by a digit.

        my_pattern = s.merge(s.behind(s.digit()), s.letter())

    Parameters:
    - pattern (Pattern/str): The pattern to look behind for.

    Returns:
    - Pattern: A Pattern object representing the positive lookbehind.
    """

    if isinstance(pattern, str):
        pattern = lit(pattern)

    if not isinstance(pattern, Pattern):
        message = """
        Method: simply.behind(pattern)

        The parameter must be an instance of `Pattern` or `str`.

        Use a string such as "123abc$" to match literal characters, or use a predefined set like `simply.letter()`.
        """
        raise STRlingError(message)

    return Pattern(f'(?<={pattern})', composite=True)

def not_behind(pattern):
    """
    A negative lookbehind checks for the absence of the specified pattern before the current position without including it in the result.

    Example: simply as s
        - Only matches a letter if not preceded by a digit.

        my_pattern = s.merge(s.behind(s.digit()), s.letter())

    Parameters:
    - pattern (Pattern/str): The pattern to look behind for and ensure is absent.

    Returns:
    - Pattern: A Pattern object representing the negative lookbehind.
    """

    if isinstance(pattern, str):
        pattern = lit(pattern)

    if not isinstance(pattern, Pattern):
        message = """
        Method: simply.not_behind(pattern)

        The parameter must be an instance of `Pattern` or `str`.

        Use a string such as "123abc$" to match literal characters, or use a predefined set like `simply.letter()`.
        """
        raise STRlingError(message)

    return Pattern(f'(?<!{pattern})', composite=True)
