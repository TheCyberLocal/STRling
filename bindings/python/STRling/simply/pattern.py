
import re



############################
# Base Functions
########


class Pattern:
    """
    A class to construct and compile clean and manageable regex expressions.

    Attributes:
        pattern (str): The regex pattern as a string.
        custom_set (bool): Indicates if the pattern is a custom character set.
        composite (bool): Indicates if the pattern is a composite pattern.
        repeatable (bool): Indicates if the pattern can be repeated.

    Methods:
        __call__(min=None, max=None): Returns a new Pattern object with the repetition pattern applied.
        __str__(): Returns the pattern as a string.
        __add__(other): Allows addition of two Pattern objects.
    """
    def __init__(self, pattern: str, custom_set: bool = False, negated_set: bool = False, composite: bool = False):
        # The regex pattern string for this instance.
        self.pattern = pattern
        # A custom set is regex with brackets [a-z]
        self.custom_set = custom_set
        # A negated set is negated regex with brackets [^a-z]
        self.negated_set = negated_set
        # A composite is any pattern pattern in parenthesis.
        self.composite = composite

    def __call__(self, min: int = None, max: int = None):
        """
        Applies a repetition pattern to the current pattern.

        Parameters: (min/exact, max)
        - min (optional): Specifies the minimum number of characters to match.
        - max (optional): Specifies the maximum number of characters to match.

        Special Cases:
        - If only `min` is specified, it represents the exact number of characters to match.
        - If `max` is 0, it means there is no upper limit.

        Returns:
            Pattern: A new Pattern object with the repetition pattern applied.
        """
        return Pattern(self.pattern + repeat(min, max))

    def __str__(self):
        """
        Returns the pattern as a string.

        Returns:
            str: The regex pattern as a string.
        """
        return self.pattern


def repeat(min: int = None, max: int = None):
    """
    Constructs a repetition pattern based on the specified minimum and maximum counts.

    Parameters: (min/exact, max)
    - min (optional): Specifies the minimum number of characters to match.
    - max (optional): Specifies the maximum number of characters to match.

    Special Cases:
    - If only `min` is specified, it represents the exact number of characters to match.
    - If `max` is 0, it means there is no upper limit.

    Returns:
        str: A string representing the repetition pattern.
    """
    if min is not None and max is not None:
        if max == 0:  # Special case to handle the 'min,' syntax
            return f'{{{min},}}'
        if min > max:
            msg = (
        """
        Problem:
            The `min` param cannot be greater than the `max`.

        Solution:
            You may have them swapped. Ensure the lesser number
            is on the left and the greater number is on the right.
        """)
            raise ValueError(msg)
        return f'{{{min},{max}}}'
    elif min is not None:
        return f'{{{min}}}'
    else:
        return ''


def lit(text):
    """
    Creates a Pattern object that matches the given literal text.

    The only non-literal symbol is backslash \\\\.
    You must use two to represent one \\\\\\\\.

    Parameters:
        text (str): The literal text to match.

    Returns:
        Pattern: A Pattern object that matches the literal text.
    """
    if not isinstance(text, str):
        msg = (
        """
        Problem:
            The text parameter is not a string.

        Solution:
            Specify your literal text in quotes `simply.lit('abc123$')`.
        """)
        raise ValueError(msg)
    escaped_text = re.escape(text).replace('/', '\/')
    return Pattern(escaped_text)
