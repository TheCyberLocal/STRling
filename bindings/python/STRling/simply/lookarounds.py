
from .pattern import Pattern


############################
# Lookarounds
########


def ahead(pattern):
    """
    Creates a Pattern object that performs a positive lookahead.

    A positive lookahead checks for the presence of the specified pattern
    without including it in the result.

    Parameters:
        pattern (Pattern): The pattern to look ahead for.

    Returns:
        Pattern: A Pattern object representing the positive lookahead.

    Raises:
        ValueError: If the parameter is not an instance of Pattern.
    """
    if not isinstance(pattern, Pattern):
        msg = (
        """
        Problem:
            The parameter is not an instance of Pattern.

        Solution:
            Use `simply.lit('abc123$')` to match literal characters,
            or use a predefined set like `simply.letters()`.
        """)
        raise ValueError(msg)
    return Pattern(f'(?={pattern})', composite=True)

def not_ahead(pattern):
    """
    Creates a Pattern object that performs a negative lookahead.

    A negative lookahead checks for the absence of the specified pattern
    without including it in the result.

    Parameters:
        pattern (Pattern): The pattern to look ahead for and ensure is absent.

    Returns:
        Pattern: A Pattern object representing the negative lookahead.

    Raises:
        ValueError: If the parameter is not an instance of Pattern.
    """
    if not isinstance(pattern, Pattern):
        msg = (
        """
        Problem:
            The parameter is not an instance of Pattern.

        Solution:
            Use `simply.lit('abc123$')` to match literal characters,
            or use a predefined set like `simply.letters()`.
        """)
        raise ValueError(msg)
    return Pattern(f'(?!{pattern})', composite=True)

def behind(pattern):
    """
    Creates a Pattern object that performs a positive lookbehind.

    A positive lookbehind checks for the presence of the specified pattern
    before the current position without including it in the result.

    Parameters:
        pattern (Pattern): The pattern to look behind for.

    Returns:
        Pattern: A Pattern object representing the positive lookbehind.

    Raises:
        ValueError: If the parameter is not an instance of Pattern.
    """
    if not isinstance(pattern, Pattern):
        msg = (
        """
        Problem:
            The parameter is not an instance of Pattern.

        Solution:
            Use `simply.lit('abc123$')` to match literal characters,
            or use a predefined set like `simply.letters()`.
        """)
        raise ValueError(msg)
    return Pattern(f'(?<={pattern})', composite=True)

def not_behind(pattern):
    """
    Creates a Pattern object that performs a negative lookbehind.

    A negative lookbehind checks for the absence of the specified pattern
    before the current position without including it in the result.

    Parameters:
        pattern (Pattern): The pattern to look behind for and ensure is absent.

    Returns:
        Pattern: A Pattern object representing the negative lookbehind.

    Raises:
        ValueError: If the parameter is not an instance of Pattern.
    """
    if not isinstance(pattern, Pattern):
        msg = (
        """
        Problem:
            The parameter is not an instance of Pattern.

        Solution:
            Use `simply.lit('abc123$')` to match literal characters,
            or use a predefined set like `simply.letters()`.
        """)
        raise ValueError(msg)
    return Pattern(f'(?<!{pattern})', composite=True)
