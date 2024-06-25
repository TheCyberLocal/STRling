
from .pattern import Pattern, clean_param



############################
# Lookarounds
########


def ahead(pattern):
    """
    A positive lookahead checks for the presence of the specified pattern after the current position without including it in the result.

    Example: simply as s

        # Below only matches a digit followed by a letter.

        my_pattern = s.merge(s.digit(), s.ahead(s.letter()))

    Parameters:
    - pattern (Pattern/str): The pattern to look ahead for.

    Returns:
    - Pattern: A Pattern object representing the positive lookahead.

    Raises:
    - ValueError: If the parameter is not an instance of Pattern or str.
    """

    clean_pattern = clean_param(pattern)

    return Pattern(f'(?={clean_pattern})', composite=True)

def not_ahead(pattern):
    """
    A negative lookahead checks for the absence of the specified pattern after the current position without including it in the result.

    Example: simply as s

        # Below only matches a digit if not followed by a letter.

        my_pattern = s.merge(s.digit(), s.not_ahead(s.letter()))

    Parameters:
    - pattern (Pattern/str): The pattern to look ahead for and ensure is absent.

    Returns:
    - Pattern: A Pattern object representing the negative lookahead.

    Raises:
    - ValueError: If the parameter is not an instance of Pattern or str.
    """

    clean_pattern = clean_param(pattern)

    return Pattern(f'(?!{clean_pattern})', composite=True)

def behind(pattern):
    """
    A positive lookbehind checks for the presence of the specified pattern before the current position without including it in the result.

    Example: simply as s

        # Below only matches a letter preceded by a digit.

        my_pattern = s.merge(s.behind(s.digit()), s.letter())

    Parameters:
    - pattern (Pattern/str): The pattern to look behind for.

    Returns:
    - Pattern: A Pattern object representing the positive lookbehind.

    Raises:
    - ValueError: If the parameter is not an instance of Pattern or str.
    """

    clean_pattern = clean_param(pattern)

    return Pattern(f'(?<={clean_pattern})', composite=True)

def not_behind(pattern):
    """
    A negative lookbehind checks for the absence of the specified pattern before the current position without including it in the result.

    Example: simply as s

        # Below only matches a letter if not preceded by a digit.

        my_pattern = s.merge(s.behind(s.digit()), s.letter())

    Parameters:
    - pattern (Pattern/str): The pattern to look behind for and ensure is absent.

    Returns:
    - Pattern: A Pattern object representing the negative lookbehind.

    Raises:
    - ValueError: If the parameter is not an instance of Pattern or str.
    """

    clean_pattern = clean_param(pattern)

    return Pattern(f'(?<!{clean_pattern})', composite=True)
