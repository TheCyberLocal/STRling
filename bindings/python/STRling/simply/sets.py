
from .pattern import Pattern



############################
# User Char Sets
########


def between(start, end):
    """
    """
    if not (start.isalpha() and end.isalpha() or
        start.isdigit() and end.isdigit()):
        msg = (
        """
        Problem:
            Invalid Range Specified.

        Solution:
            The start and end character must both
            be numbers or letters of the same case.
        """)
        raise ValueError(msg)

    new_pattern = f'[{start}-{end}]'
    return Pattern(new_pattern, custom_set=True)

def in_(*patterns):
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
            raise ValueError('The in_ method cannot take patterns with specified range.')
        if pattern.custom_set:
            joined += str(pattern)[1:-1]
        else:
            joined += str(pattern)

    new_pattern = f'[{joined}]'
    return Pattern(new_pattern, custom_set=True)

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
    return Pattern(new_pattern, custom_set=True)
