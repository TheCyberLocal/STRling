
from .pattern import Pattern


############################
# Constructor Methods
########



def or_(*patterns):
    """
    Creates a pattern that matches any of the given patterns.

    This function constructs a non-capturing group that matches any of the provided patterns.

    Parameters:
        *patterns (Pattern): One or more Pattern instances to be matched.

    Returns:
        Pattern: A Pattern object representing the OR combination of the given patterns.

    Raises:
        ValueError: If any of the parameters is not an instance of Pattern.
    """
    if not all(isinstance(pattern, Pattern) for pattern in patterns):
        msg = (
        """
        Problem:
            Not all the parameters are an instance of Pattern.

        Solution:
            Use `simply.lit('abc123$')` to match literal characters,
            or use a predefined set like `simply.letters()`.
        """)
        raise ValueError(msg)
    joined = '|'.join(f'(?:{str(p)})' for p in patterns)
    return Pattern(f'(?:{joined})')

def may(*patterns):
    """
    Creates a pattern that optionally matches the given patterns.

    This function constructs a pattern that optionally matches the provided patterns.

    Parameters:
        *patterns (Pattern): One or more Pattern instances to be optionally matched.

    Returns:
        Pattern: A Pattern object representing the optional match of the given patterns.

    Raises:
        ValueError: If any of the parameters is not an instance of Pattern.
    """
    if not all(isinstance(pattern, Pattern) for pattern in patterns):
        msg = (
        """
        Problem:
            Not all the parameters are an instance of Pattern.

        Solution:
            Use `simply.lit('abc123$')` to match literal characters,
            or use a predefined set like `simply.letters()`.
        """)
        raise ValueError(msg)

    if len(patterns) == 1:
        return Pattern(f'{patterns[0]}?')

    joined = merge(*patterns)
    return Pattern(f'{joined}?', composite=True)



def merge(*patterns):
    """
    Creates a pattern that matches the concatenation of the given patterns.

    This function constructs a non-capturing group that matches the concatenation of the provided patterns.

    Parameters:
        *patterns (Pattern): One or more Pattern instances to be concatenated.

    Returns:
        Pattern: A Pattern object representing the concatenation of the given patterns.

    Raises:
        ValueError: If any of the parameters is not an instance of Pattern.
    """
    if not all(isinstance(pattern, Pattern) for pattern in patterns):
        msg = (
        """
        Problem:
            Not all the parameters are an instance of Pattern.

        Solution:
            Use `simply.lit('abc123$')` to match literal characters,
            or use a predefined set like `simply.letters()`.
        """)
        raise ValueError(msg)
    joined = ''.join(str(p) for p in patterns)
    new_pattern = f'(?:{joined})'
    return Pattern(new_pattern, composite=True)

def capture(*patterns):
    """
    Creates a pattern that captures the given patterns.

    This function constructs a capturing group that matches the provided patterns.

    Parameters:
        *patterns (Pattern): One or more Pattern instances to be captured.

    Returns:
        Pattern: A Pattern object representing the capturing group of the given patterns.

    Raises:
        ValueError: If any of the parameters is not an instance of Pattern.
    """
    if not all(isinstance(pattern, Pattern) for pattern in patterns):
        msg = (
        """
        Problem:
            Not all the parameters are an instance of Pattern.

        Solution:
            Use `simply.lit('abc123$')` to match literal characters,
            or use a predefined set like `simply.letters()`.
        """)
        raise ValueError(msg)

    joined = ''.join(str(p) for p in patterns)
    return Pattern(f'({joined})', composite=True)

def group(name, *patterns):
    """
    Creates a named capturing group for the given patterns.

    This function constructs a named capturing group that matches the provided patterns.

    Parameters:
        name (str): The name of the capturing group.
        *patterns (Pattern): One or more Pattern instances to be captured.

    Returns:
        Pattern: A Pattern object representing the named capturing group of the given patterns.

    Raises:
        ValueError: If any of the parameters is not an instance of Pattern.
    """
    if not all(isinstance(pattern, Pattern) for pattern in patterns):
        msg = (
        """
        Problem:
            Not all the parameters are an instance of Pattern.

        Solution:
            Use `simply.lit('abc123$')` to match literal characters,
            or use a predefined set like `simply.letters()`.
        """)
        raise ValueError(msg)

    joined = ''.join(str(p) for p in patterns)
    return Pattern(f'(?P<{name}>{joined})', composite=True)
