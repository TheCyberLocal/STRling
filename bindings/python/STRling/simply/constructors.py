
from .pattern import Pattern


############################
# Constructor Methods
########



def any_of(*patterns):
    """
    Creates a pattern that matches any one of the provided patterns.

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
            or use a predefined set like `simply.letter()`.
        """)
        raise ValueError(msg)
    joined = '|'.join(f'(?:{str(p)})' for p in patterns)
    return Pattern(f'(?:{joined})', composite=True)

def may(*patterns):
    """
    Creates a pattern that optionally matches the provided patterns.

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
            or use a predefined set like `simply.letter()`.
        """)
        raise ValueError(msg)

    if len(patterns) == 1:
        return Pattern(f'{patterns[0]}?')

    joined = merge(*patterns)
    return Pattern(f'{joined}?', composite=True)



def merge(*patterns):
    """
    Combines the provided patterns into one larger pattern.

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
            or use a predefined set like `simply.letter()`.
        """)
        raise ValueError(msg)
    joined = ''.join(str(p) for p in patterns)
    new_pattern = f'(?:{joined})'
    return Pattern(new_pattern, composite=True)

def capture(*patterns):
    """
    Creates a numbered group that can be indexed for extracting part of a match.

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
            or use a predefined set like `simply.letter()`.
        """)
        raise ValueError(msg)

    joined = ''.join(str(p) for p in patterns)
    return Pattern(f'({joined})', composite=True)

def group(name, *patterns):
    """
    Creates a named group that can be referenced for extracting part of a match.

    Parameters:
        name (str): The name of the capturing group.
        *patterns (Pattern): One or more Pattern instances to be captured.

    Returns:
        Pattern: A Pattern object representing the named capturing group of the given patterns.

    Raises:
        ValueError: If any of the parameters is not an instance of Pattern.
    """
    if not isinstance(name, str):
        raise ValueError('The `name` parameter must be a string.')
    if not all(isinstance(pattern, Pattern) for pattern in patterns):
        msg = (
        """
        Problem:
            Not all the parameters are an instance of Pattern.

        Solution:
            Use `simply.lit('abc123$')` to match literal characters,
            or use a predefined set like `simply.letter()`.
        """)
        raise ValueError(msg)

    joined = ''.join(str(p) for p in patterns)
    return Pattern(f'(?P<{name}>{joined})', composite=True, named_group=True)
