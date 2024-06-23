# Imports here

import re



####################################################
##  This is just the setup and helpers functions  ##
##  Scroll further down to see the user tools     ##
####################################################


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



###############################################
##   All functions below are for the user    ##
###############################################


def lit(text):
    """
    The only non-literal symbol is backslash \\\\.
    If you want one backslash, you must use two \\\\\\\\.
    """
    escaped_text = re.escape(text).replace(' ', 's').replace('/', '\/')
    return Pattern(escaped_text)



#################################
##    Custom Character Sets    ##
#################################


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
        raise Exception(msg)

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
        raise Exception(msg)

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
        raise Exception(msg)

    joined = r''
    for pattern in patterns:
        if len(str(pattern)) > 1 and str(pattern)[-1] == '}' and str(pattern)[-2] != "\\":
            raise Exception('The in_ method cannot take patterns with specified range.')
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
        raise Exception(msg)

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
        raise Exception(msg)

    joined = r''
    for pattern in patterns:
        if len(str(pattern)) > 1 and str(pattern)[-1] == '}' and str(pattern)[-2] != "\\":
            raise Exception('The not_in method cannot take patterns with specified range.')
        if pattern.custom_set:
            joined += str(pattern)[1:-1]
        else:
            joined += str(pattern)

    new_pattern = f'[{joined}]'
    return Pattern(new_pattern, custom_set=True)

def letter():
    """
    """
    return Pattern(r'[A-Za-z]', custom_set=True)

def upper():
    """
    """
    return Pattern(r'[A-Z]', custom_set=True)

def lower():
    """
    """
    return Pattern(r'[a-z]', custom_set=True)



#####################################
##    Predefined Character Sets    ##
#####################################


def digit():
    """
    """
    return Pattern(r'\d')

def space():
    """
    """
    return Pattern(r'\s')

def not_newline():
    """
    """
    return Pattern(r'.')

def newline():
    """
    """
    return Pattern(r'\n')

def tab():
    """
    """
    return Pattern(r'\t')

def carriage():
    """
    """
    return Pattern(r'\r')

def bound():
    """
    """
    return Pattern(r'\b')

def start():
    """
    """
    return Pattern(r'^')

def start():
    """
    """
    return Pattern(r'$')


#######################
##    Lookarounds    ##
#######################

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






def or_(*patterns):
    if not all(isinstance(pattern, Pattern) for pattern in patterns):
        msg = (
        """
        Problem:
            Not all the parameters are an instance of Pattern.

        Solution:
            Use `simply.lit('abc123$')` to match literal characters,
            or use a predefined set like `simply.letters()`.
        """)
        raise Exception(msg)
    joined = '|'.join(f'(?:{str(p)})' for p in patterns)
    return Pattern(f'(?:{joined})')

def may(*patterns):
    if not all(isinstance(pattern, Pattern) for pattern in patterns):
        msg = (
        """
        Problem:
            Not all the parameters are an instance of Pattern.

        Solution:
            Use `simply.lit('abc123$')` to match literal characters,
            or use a predefined set like `simply.letters()`.
        """)
        raise Exception(msg)

    if len(patterns) == 1:
        return Pattern(f'{patterns[0]}?')

    joined = merge(*patterns)
    return Pattern(f'{joined}?', composite=True)



def merge(*patterns):
    if not all(isinstance(pattern, Pattern) for pattern in patterns):
        msg = (
        """
        Problem:
            Not all the parameters are an instance of Pattern.

        Solution:
            Use `simply.lit('abc123$')` to match literal characters,
            or use a predefined set like `simply.letters()`.
        """)
        raise Exception(msg)
    joined = ''.join(str(p) for p in patterns)
    new_pattern = f'(?:{joined})'
    return Pattern(new_pattern, composite=True)

def capture(*patterns):
    if not all(isinstance(pattern, Pattern) for pattern in patterns):
        msg = (
        """
        Problem:
            Not all the parameters are an instance of Pattern.

        Solution:
            Use `simply.lit('abc123$')` to match literal characters,
            or use a predefined set like `simply.letters()`.
        """)
        raise Exception(msg)

    joined = ''.join(str(p) for p in patterns)
    return Pattern(f'({joined})', composite=True)

def group(name, *patterns):
    if not all(isinstance(pattern, Pattern) for pattern in patterns):
        msg = (
        """
        Problem:
            Not all the parameters are an instance of Pattern.

        Solution:
            Use `simply.lit('abc123$')` to match literal characters,
            or use a predefined set like `simply.letters()`.
        """)
        raise Exception(msg)

    joined = ''.join(str(p) for p in patterns)
    return Pattern(f'(?P<{name}>{joined})', composite=True, repeatable=False)
