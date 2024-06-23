
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
        __call__(min_rep=None, max_rep=None): Returns a new Pattern object with the repetition pattern applied.
        __str__(): Returns the pattern as a string.
        __add__(other): Allows addition of two Pattern objects.
    """
    def __init__(self, pattern: str, custom_set: bool = False, negated_set: bool = False, composite: bool = False, named_group: bool = False):
        # The regex pattern string for this instance.
        self.pattern = pattern
        # A custom set is regex with brackets [a-z]
        self.custom_set = custom_set
        # A negated set is negated regex with brackets [^a-z]
        self.negated_set = negated_set
        # A composite pattern is one enclosed in parenthesis.
        self.composite = composite
        # A named_group is one that cannot repeat.
        self.named_group = named_group

    def __call__(self, min_rep: int = None, max_rep: int = None):
        """
        Applies a repetition pattern to the current pattern.

        Parameters: (min_rep/exact_rep, max_rep)
        - min_rep (optional): Specifies the minimum number of characters to match.
        - max_rep (optional): Specifies the maximum number of characters to match.

        Special Cases:
        - If only `min_rep` is specified, it represents the exact number of characters to match.
        - If `max_rep` is 0, it means there is no upper limit.

        Returns:
            Pattern: A new Pattern object with the repetition pattern applied.
        """
        if self.named_group:
            msg = (
        """
        Problem:
            Cannot repeat a named group instance since names must be unique.

        Solution:
            Consider using an unlabeled group (merge), or a numbered group (capture).
        """)
            raise ValueError(msg)
        self.pattern += repeat(min_rep, max_rep)
        return self

    def __str__(self):
        """
        Returns the pattern as a string.

        Returns:
            str: The regex pattern as a string.
        """
        return self.pattern


def repeat(min_rep: int = None, max_rep: int = None):
    """
    Constructs a repetition pattern based on the specified minimum and maximum counts.

    Parameters: (min_rep/exact_rep, max_rep)
    - min_rep (optional): Specifies the minimum number of characters to match.
    - max_rep (optional): Specifies the maximum number of characters to match.

    Special Cases:
    - If only `min_rep` is specified, it represents the exact number of characters to match.
    - If `max_rep` is 0, it means there is no upper limit.

    Returns:
        str: A string representing the repetition pattern.
    """
    if min_rep is not None and max_rep is not None:
        if max_rep == 0:  # Special case to handle the 'min_rep,' syntax
            return f'{{{min_rep},}}'
        if min_rep > max_rep:
            msg = (
        """
        Problem:
            The `min_rep` param cannot be greater than the `max_rep`.

        Solution:
            You may have them swapped. Ensure the lesser number
            is on the left and the greater number is on the right.
        """)
            raise ValueError(msg)
        return f'{{{min_rep},{max_rep}}}'
    elif min_rep is not None:
        return f'{{{min_rep}}}'
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
