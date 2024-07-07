import re, textwrap


class STRlingError(ValueError):
    def __init__(self, message):
        self.message = textwrap.dedent(message).strip().replace('\n', '\n\t')
        super().__init__(self.message)

    def __str__(self):
        return f"\n\nSTRlingError: Invalid Pattern Attempted.\n\n\t{self.message}"

def lit(text):
    escaped_text = re.escape(text).replace('/', '\/')
    return Pattern(escaped_text)

def repeat(min_rep: int = None, max_rep: int = None):
    if min_rep is not None and max_rep is not None:
        if max_rep == 0:
            return f'{{{min_rep},}}'
        if min_rep > max_rep:
            message = """
            Method: Pattern.__call__(min_rep, max_rep)

            The `min_rep` must not be greater than the `max_rep`.

            Ensure the lesser number is on the left and the greater number is on the right.
            """
            raise STRlingError(message)
        return f'{{{min_rep},{max_rep}}}'
    elif min_rep is not None:
        return f'{{{min_rep}}}'
    else:
        return ''

class Pattern:
    """
    A class to construct and compile clean and manageable regex expressions.

    Attributes:
        - pattern (str): The regex pattern as a string.
        - custom_set (bool): Indicates if the pattern is a custom character set.
        - negated (bool): Indicates if the pattern is a negated custom character set.
        - composite (bool): Indicates if the pattern is a composite pattern.
        - named_groups (list): Indicates the list of named groups within.
        - numbered_group (bool): Indicates if the pattern is a numbered group.

    Methods:
        - __call__(min_rep=None, max_rep=None): Returns a new Pattern object with the repetition pattern applied.
        - __str__(): Returns the pattern as a string.
        - create_modified_instance(): Returns an independent copy of the pattern instance.
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
        - max_rep (optional): Specifies the maximum number of characters to match, 0 means unlimited, None means match exact count of min_rep.

        Returns:
        - A new Pattern object with the repetition pattern applied.
        """
        # Prevent errors if invoked with no range
        if min_rep is None and max_rep is None:
            return self

        # If min_rep or max_rep are specified as non-integers
        if min_rep is not None and not isinstance(min_rep, int) or max_rep is not None and not isinstance(max_rep, int):
            message = """
            Method: Pattern.__call__(min_rep, max_rep)

            The `min_rep` and `max_rep` arguments must be integers (0-9).
            """
            raise STRlingError(message)

        # If min_rep or max_rep are specified out of valid range
        if min_rep is not None and min_rep < 0 or max_rep is not None and max_rep < 0:
            message = """
            Method: Pattern.__call__(min_rep, max_rep)

            The `min_rep` and `max_rep` must be 0 or greater.
            """
            raise STRlingError(message)

        # Named group is unique and not repeatable
        if self.named_groups and min_rep is not None and max_rep is not None:
            message = """
            Method: Pattern.__call__(min_rep, max_rep)

            Named groups cannot be repeated as they must be unique.

            Consider using an unlabeled group (merge) or a numbered group (capture).
            """
            raise STRlingError(message)

        # A group already assigned a specified range cannot be reassigned
        if len(self.pattern) > 1 and self.pattern[-1] == '}' and self.pattern[-2] != '\\':
            message = """
            Method: Pattern.__call__(min_rep, max_rep)

            Cannot re-invoke pattern to specify range that already exists.

            Examples of invalid syntax:
                simply.letter(1, 2)(3, 4) # double invoked range is invalid
                my_pattern = simply.letter(1, 2) # my_pattern was set range (1, 2) # valid
                my_new_pattern = my_pattern(3, 4) # my_pattern was reinvoked (3, 4) # invalid

            Set the range on the first invocation, don't reassign it.

            Examples of valid syntax:
                You can either specify the range now:
                    my_pattern = simply.letter(1, 2)

                Or you can specify the range later:
                    my_pattern = simply.letter() # my_pattern was never assigned a range
                    my_new_pattern = my_pattern(1, 2) # my_pattern was invoked with (1, 2) for the first time.
            """
            raise STRlingError(message)

        # A numbered group repeats by copying, not amending a range.
        if self.numbered_group:
            if max_rep is not None:
                message = """
                Method: Pattern.__call__(min_rep, max_rep)

                The `max_rep` parameter was specified when capture takes only one parameter, the exact number of copies.

                Consider using an unlabeled group (merge) for a range.
                """
                raise STRlingError(message)
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
        """
        Returns a copy of the pattern instance.
        """
        return cls(new_pattern, **kwargs)
