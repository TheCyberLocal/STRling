from .pattern import STRlingError, Pattern, lit


def ahead(pattern):
    """
    A positive lookahead checks for the presence of the specified pattern after the current position without including it in the result.

    Parameters:
    - pattern (Pattern/str): The pattern to look ahead for.

    Returns:
    - An instance of the Pattern class.

    Examples:
        ```
        # Only matches a digit followed by a letter.
        my_pattern = s.merge(s.digit(), s.ahead(s.letter()))
        ```
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

    Parameters:
    - pattern (Pattern/str): The pattern to look ahead for and ensure is absent.

    Returns:
    - An instance of the Pattern class.

    Examples:
        ```
        # Only matches a digit if not followed by a letter.
        my_pattern = s.merge(s.digit(), s.not_ahead(s.letter()))
        ```
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

    Parameters:
    - pattern (Pattern/str): The pattern to look behind for.

    Returns:
    - An instance of the Pattern class.

    Examples:
        ```
        # Only matches a letter preceded by a digit.
        my_pattern = s.merge(s.behind(s.digit()), s.letter())
        ```
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

    Parameters:
    - pattern (Pattern/str): The pattern to look behind for and ensure is absent.

    Returns:
    - An instance of the Pattern class.

    Examples:
        ```
        # Only matches a letter if not preceded by a digit.
        my_pattern = s.merge(s.behind(s.digit()), s.letter())
        ```
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

def has(pattern):
    """
    A lookaround that checks for the presence of the specified pattern anywhere in the string without including it in the result.

    Parameters:
    - pattern (Pattern/str): The pattern to look for.

    Returns:
    - An instance of the Pattern class.

    Examples:
        ```
        # Only matches if the string contains the pattern.
        my_pattern = s.has(pattern)
        ```
    """

    if isinstance(pattern, str):
        pattern = lit(pattern)

    if not isinstance(pattern, Pattern):
        message = """
        Method: simply.has(pattern)

        The parameter must be an instance of `Pattern` or `str`.

        Use a string such as "123abc$" to match literal characters, or use a predefined set like `simply.letter()`.
        """
        raise STRlingError(message)

    return Pattern(f'(?=.*{pattern})', composite=True)

def has_not(pattern):
    """
    A lookaround that checks for the absence of the specified pattern everywhere in the string without including it in the result.

    Parameters:
    - pattern (Pattern/str): The pattern to look for and ensure is absent.

    Returns:
    - An instance of the Pattern class.

    Examples:
        ```
        # Only matches if the string doesn't contain the pattern.
        my_pattern = s.has_not(pattern)
        ```
    """

    if isinstance(pattern, str):
        pattern = lit(pattern)

    if not isinstance(pattern, Pattern):
        message = """
        Method: simply.has(pattern)

        The parameter must be an instance of `Pattern` or `str`.

        Use a string such as "123abc$" to match literal characters, or use a predefined set like `simply.letter()`.
        """
        raise STRlingError(message)

    return Pattern(f'(?!.*{pattern})', composite=True)
