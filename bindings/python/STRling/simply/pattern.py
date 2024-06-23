
import re



############################
# Base Functions
########


class Pattern:
    """
    """
    def __init__(self, pattern: str, custom_set=False, composite=False, repeatable=True):
        # character sets must be stripped when passed into new character set
        # grouped patterns or composites may not be submitted into a character set
        self.pattern = pattern
        self.custom_set = custom_set
        self.composite = composite
        self.repeatable = repeatable

    def __call__(self, min: int = None, max: int = None):
        return Pattern(self.pattern + repeat(min, max))

    def __str__(self):
        return self.pattern

    def __add__(self, other):
        if not isinstance(other, Pattern):
            raise TypeError("You can only add instances of Pattern")

    def raw(self, min: int = None, max: int = None):
        return self.pattern + repeat(min, max)


def repeat(min=None, max=None):
    """
    """
    if min is not None and max is not None:
        if max == '':  # Special case to handle the 'min,' syntax
            return f'{{{min},}}'
        if min > max:
            raise ValueError('Min cannot be greater than max.')
        return f'{{{min},{max}}}'
    elif min is not None:
        return f'{{{min}}}'
    return ''


def lit(text):
    """
    The only non-literal symbol is backslash \\\\.
    You must use two to represent one \\\\\\\\.
    """
    escaped_text = re.escape(text).replace(' ', 's').replace('/', '\/')
    return Pattern(escaped_text)
