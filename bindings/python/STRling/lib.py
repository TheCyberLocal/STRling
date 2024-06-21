import re


# Range syntax
def repeat(min=None, max=None):
    """Create a range for the preceding symbol."""
    if min is not None and max is not None:
        if max == '':  # Special case to handle the 'min,' syntax
            return f'{{{min},}}'
        if min > max:
            raise ValueError('min cannot be greater than max')
        return f'{{{min},{max}}}'
    elif min is not None:
        return f'{{{min}}}'
    return ''


# Pattern class
class Pattern:
    def __init__(self, pattern):
        self.pattern = pattern

    def __call__(self, min=None, max=None):
        return self.pattern + repeat(min, max)

    def __str__(self):
        return self.pattern


# Decorators
def repeat_on_invoke(func, *args):
    pattern = func(*args)
    return Pattern(pattern)


# Symbols with positional arguments
def lit(text, min=None, max=None):
    """Match the literal string `text`."""
    return re.escape(text) + repeat(min, max)

def between(start_char=None, end_char=None, min=None, max=None):
    """Match any character between `start_char` and `end_char`."""
    return f'[{start_char}-{end_char}]' + repeat(min, max)

def in_(chars=None, min=None, max=None):
    """Match any character in `chars`."""
    return f'[{chars}]' + repeat(min, max)

def not_in(chars=None, min=None, max=None):
    """Match any character not in `chars`."""
    return f'[^{chars}]' + repeat(min, max)


# Symbols without positional arguments
@repeat_on_invoke
def digit():
    """Match a digit."""
    return r'\d'

@repeat_on_invoke
def letter():
    """Match a letter."""
    return r'[A-Za-z]'

@repeat_on_invoke
def upper():
    """Match a letter."""
    return r'[A-Z]'

@repeat_on_invoke
def lower():
    """Match a letter."""
    return r'[a-z]'

@repeat_on_invoke
def space():
    """Match a space."""
    return r'\s'

@repeat_on_invoke
def any():
    """Match any character."""
    return r'.'


# Whitespace characters
@repeat_on_invoke
def newline():
    """Match a newline."""
    return r'\n'

@repeat_on_invoke
def tab():
    """Match a tab."""
    return r'\t'

@repeat_on_invoke
def carriage():
    """Match a carriage return."""
    return r'\r'

@repeat_on_invoke
def bound():
    """Match the exact word `text`."""
    return r'\b'



# Anchors
def start():
    """Match the start of the string."""
    return Pattern(r'^')

def end():
    """Match the end of the string."""
    return Pattern(r'$')


# Lookarounds
def ahead(pattern):
    """Match if the pattern matches ahead."""
    return f'(?={pattern})'

def behind(pattern):
    """Match if the pattern matches behind."""
    return f'(?<={pattern})'

def not_ahead(pattern):
    """Match if the pattern does not match ahead."""
    return f'(?!{pattern})'

def not_behind(pattern):
    """Match if the pattern does not match behind."""
    return f'(?<!{pattern})'


# Conditionals
def or_(*patterns):
    """Match any of the given patterns."""
    joined = '|'.join(str(p) for p in patterns)
    return f'(?:{joined})'

def may(pattern):
    """Match zero or one occurrence of the pattern."""
    return f'{pattern}?'


# Grouping
def group(name, *patterns):
    """Create a named capture group with the given patterns."""
    joined = ''.join(str(p) for p in patterns)
    return f'(?P<{name}>{joined})'

def merge(*patterns):
    """Create a non-capturing group with the given patterns."""
    joined = ''.join(str(p) for p in patterns)
    return Pattern(f'(?:{joined})')
