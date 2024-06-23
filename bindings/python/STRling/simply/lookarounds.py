
from .pattern import Pattern


############################
# Lookarounds
########


def ahead(pattern):
    """
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
        raise Exception(msg)
    return Pattern(f'(?={pattern})', composite=True, repeatable=False)

def behind(pattern):
    """
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
        raise Exception(msg)
    return Pattern(f'(?<={pattern})', composite=True, repeatable=False)

def not_ahead(pattern):
    """
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
        raise Exception(msg)
    return Pattern(f'(?!{pattern})', composite=True, repeatable=False)

def not_behind(pattern):
    """
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
        raise Exception(msg)
    return Pattern(f'(?<!{pattern})', composite=True, repeatable=False)
