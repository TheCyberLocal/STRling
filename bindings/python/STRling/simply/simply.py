
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
    def __init__(self, pattern: str, custom_set=None, composite=None):
        # character sets must be stripped when passed into new character set
        # grouped patterns or composites may not be submitted into a character set
        self.pattern = pattern
        self.custom_set = custom_set
        self.composite = composite

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
    unicode_text = text.encode("unicode_escape")
    regular_text = unicode_text.decode("utf-8")
    escaped_text = regular_text.replace(' ', 's')
    return Pattern(escaped_text, custom_set=False, composite=False)

def between(start, end):
    new_pattern = f'[{start}-{end}]'
    return Pattern(new_pattern, custom_set=True, composite=False)

def in_(*patterns):
    if not all(isinstance(pattern, Pattern) for pattern in patterns):
        raise Exception('All parameters for _in method must be instances of Pattern')

    if any(pattern.composite for pattern in patterns if isinstance(pattern, Pattern)):
        raise Exception('The in_ method cannot take grouped patterns')

    joined = r''
    for pattern in patterns:
        if len(str(pattern)) > 1 and str(pattern)[-1] == '}' and str(pattern)[-2] != "\\":
            raise Exception('The in_ method cannot take patterns of specified range')
        if pattern.custom_set:
            joined += str(pattern)[1:-1]
        else:
            joined += str(pattern)

    new_pattern = f'[{joined}]'
    return Pattern(new_pattern, custom_set=True, composite=False)

def merge(*patterns):
    joined = ''.join(str(p) for p in patterns)
    new_pattern = f'(?:{joined})'
    return Pattern(new_pattern, custom_set=False, composite=True)

def letter():
    return Pattern(r'[A-Za-z]', custom_set=True, composite=False)

def digit():
    return Pattern(r'\d', custom_set=False, composite=False)
