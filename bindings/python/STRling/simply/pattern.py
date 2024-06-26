
import re, textwrap


############################
# Base Functions
########

class STRlingError(ValueError):
    def __init__(self, problem, solution):
        self.problem = textwrap.dedent(problem).strip().replace('\n', '\n\t\t')
        self.solution = textwrap.dedent(solution).strip().replace('\n', '\n\t\t')
        super().__init__(self.problem)

    def __str__(self):
        return f"\n\nSTRlingError: Attempted Constructing Invalid Pattern.\n\n\tProblem:\n\t\t{self.problem}\n\n\tSolution:\n\t\t{self.solution}"


class Pattern:
    """
    A class to construct and compile clean and manageable regex expressions.

    Attributes:
        - pattern (str): The regex pattern as a string.
        - custom_set (bool): Indicates if the pattern is a custom character set.
        - composite (bool): Indicates if the pattern is a composite pattern.
        - repeatable (bool): Indicates if the pattern can be repeated.

    Methods:
        - __call__(min_rep=None, max_rep=None): Returns a new Pattern object with the repetition pattern applied.
        - __str__(): Returns the pattern as a string.
        - __add__(other): Allows addition of two Pattern objects.
    """
    def __init__(self, pattern: str, custom_set: bool = False, negated: bool = False, composite: bool = False, named_groups: list = [], numbered_group: bool = False):
        # The regex pattern string for this instance.
        self.pattern = pattern
        # A custom set is regex with brackets [a-z]
        self.custom_set = custom_set
        # A negated set is negated regex with brackets [^a-z]
        self.negated = negated
        # A composite pattern is one enclosed in parenthesis.
        self.composite = composite
        # A pattern with named_groups cannot repeat.
        self.named_groups = named_groups
        # A numbered_group is one that is copied rather than repeated
        self.numbered_group = numbered_group

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
        - A new Pattern object with the repetition pattern applied.
        """
        # Prevent errors if invoked with no range
        if min_rep is None and max_rep is None:
            return self

        # If min_rep or max_rep are specified as non-integers
        if min_rep is not None and not isinstance(min_rep, int) or max_rep is not None and not isinstance(max_rep, int):
            raise ValueError("The invoked parameters `min_rep` and `max_rep` must be integers.")

        # If min_rep or max_rep are specified out of valid range
        if min_rep is not None and min_rep < 1 or max_rep is not None and max_rep < 0:
            raise ValueError("`min_rep` must be greater than 0 and `max_rep` must be 0 or greater.")

        # Named group is unique and not repeatable
        if self.named_groups and min_rep is not None and max_rep is not None:
            msg = (
        """
        Problem:
            Cannot repeat a named group instance since names must be unique.

        Solution:
            Consider using an unlabeled group (merge), or a numbered group (capture).
        """)
            raise ValueError(msg)

        # A group already assigned a specified range cannot be reassigned
        if len(self.pattern) > 1 and self.pattern[-1] == '}' and self.pattern[-2] != '\\':
            msg = (
        """
        Problem:
            Cannot re-invoke pattern to specify range that already exists.

            Examples of invalid syntax:
                simply.letter(1, 2)(3, 4) # double invoked range is invalid
                my_pattern = simply.letter(1, 2) # my_pattern was set range (1, 2) # valid
                my_new_pattern = my_pattern(3, 4) # my_pattern was reinvoked (3, 4) # invalid


        Solution:
            Set the range on the first invocation, don't reassign it.

            Examples of valid syntax:
                You can either specify the range now:
                    my_pattern = simply.letter(1, 2)

                Or you can specify the range later:
                    my_pattern = simply.letter() # my_pattern was never assigned a range
                    my_new_pattern = my_pattern(1, 2) # my_pattern was invoked with (1, 2) for the first time
        """)
            raise ValueError(msg)

        # Special Case: A numbered group repeats by copying, not amending a range.
        if self.numbered_group:
            if max_rep is not None:
                raise ValueError("Capture has only one parameter, copies: int = None.")
            else:
                new_pattern = f'(?:{self.pattern * min_rep})'
        # Regular Case: Add range syntax.
        else:
            new_pattern = self.pattern + repeat(min_rep, max_rep)

        # Return new instance with updated pattern
        return self.create_modified_instance(new_pattern)

    def __str__(self):
        """
        Returns the pattern object as a RegEx string.
        """
        return self.pattern

    @classmethod
    def create_modified_instance(cls, new_pattern, **kwargs):
        return cls(new_pattern, **kwargs)


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
    - A string representing the repetition pattern.
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
        - text (str): The literal text to match.

    Returns:
    - A Pattern object that matches the literal text.
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

def clean_params(*patterns):
    """
    Validates and converts input patterns to Pattern objects if necessary.

    This function processes multiple patterns, ensuring that each pattern
    is either a string or an instance of the Pattern class. If a string is
    provided, it is converted to a Pattern object using the lit() function.

    Example:
        - Converts 'abc' to a Pattern object and returns a list of Pattern objects.

        clean_patterns = clean_params('abc', s.digit())

    Parameters:
    - patterns: A variable number of arguments, each of which should be a string or Pattern.

    Returns:
    - list: A list of validated Pattern objects.

    Raises:
    - ValueError: If any parameter is not an instance of Pattern or str.
    """
    clean_patterns = []
    for pattern in patterns:
        if isinstance(pattern, str):
            pattern = lit(pattern)

        if not isinstance(pattern, Pattern):
            msg = (
        """
        Problem:
            Not all the parameters are an instance of Pattern or str.

        Solution:
            For your parameters, use a string such as "123abc$" to match
            literal characters, or use a predefined set like `simply.letter()`.
        """)
            raise ValueError(msg)

        clean_patterns.append(pattern)

    return clean_patterns

def clean_param(pattern):
    """
    Validates and converts an input pattern to a Pattern object if necessary.

    This function processes a single pattern, ensuring that the pattern
    is either a string or an instance of the Pattern class. If a string is
    provided, it is converted to a Pattern object using the lit() function.

    Example:
        - Converts 'abc' to a Pattern object and returns it.

        clean_pattern = clean_param('abc')

    Parameters:
    - pattern (Pattern/str): The pattern to validate and convert.

    Returns:
    - Pattern: A validated Pattern object.

    Raises:
    - ValueError: If the parameter is not an instance of Pattern or str.
    """
    if isinstance(pattern, str):
        pattern = lit(pattern)

    if not isinstance(pattern, Pattern):
        msg = (
        """
        Problem:
            The parameter is not an instance of Pattern or str.

        Solution:
            For your parameters, use a string such as "123abc$" to match
            literal characters, or use a predefined set like `simply.letter()`.
        """)
        raise ValueError(msg)

    return pattern

def check_unique_groups(*patterns):
    """
    Checks for duplicate named groups across multiple patterns.

    Args:
    - patterns: The patterns to check.

    Raises:
    - ValueError: If there are duplicate named groups.
    """

    named_group_counts = {}

    for pattern in patterns:
        for group_name in pattern.named_groups:
            if group_name in named_group_counts:
                named_group_counts[group_name] += 1
            else:
                named_group_counts[group_name] = 1

    duplicates = {name: count for name, count in named_group_counts.items() if count > 1}
    if duplicates:
        duplicate_info = ", ".join([f"{name}: {count}" for name, count in duplicates.items()])
        msg = (
        f"""
        Problem:
            Duplicate named groups found: {duplicate_info}.
            These must be unique for later reference.

        Solution:
            Ensure you don't include any specific named group more than once.
            If you must use the pattern more than once it should not be a named group.

            If you need later reference change the named group to `simply.capture()`.
            If you don't need later reference change the named group to `simply.merge()`.
        """)
        raise ValueError(msg)

    return named_group_counts.keys()
