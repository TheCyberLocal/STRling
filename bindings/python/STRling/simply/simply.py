import re

def repeat(min=None, max=None):
    if min is not None and max is not None:
        if max == '':  # Special case to handle the 'min,' syntax
            return f'{{{min},}}'
        if min > max:
            raise ValueError('min cannot be greater than max')
        return f'{{{min},{max}}}'
    elif min is not None:
        return f'{{{min}}}'
    return ''


class Pattern:
    def __init__(self, pattern: str, is_custom_set: bool, is_composite: bool):
        # character sets must be stripped when passed into new character set
        # grouped patterns or composites may not be submitted into a character set
        self.pattern = pattern
        self.is_custom_set = is_custom_set
        self.is_composite = is_composite

    def __call__(self, min: int = None, max: int = None):
        return Pattern(self.pattern + repeat(min, max))

    def __str__(self):
        return self.pattern

    def __add__(self, other):
        if not isinstance(other, Pattern):
            raise TypeError("You can only add instances of Pattern")

    def raw(self, min: int = None, max: int = None):
        return self.pattern + repeat(min, max)


def lit(text):
    regular_text = text.encode("unicode_escape").decode("utf-8")
    return re.escape(regular_text).replace(' ', 's') + repeat(min, max)
