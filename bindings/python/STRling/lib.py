import re


# Range syntax
def repeat(min=None, max=None):
    """Create a range for the preceding symbol."""
    if min is not None and max is not None:
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
def repetition(func):
    def wrapper(*args, **kwargs):
        pattern = func(*args, **kwargs)
        return Pattern(pattern)
    return wrapper


# Literals
@repetition
def lit(text):
    """Match the literal string `text`."""
    return re.escape(text)

@repetition
def digit():
    """Match a digit."""
    return r'\d'

@repetition
def letter():
    """Match a letter."""
    return r'[A-Za-z]'

@repetition
def upper():
    """Match a letter."""
    return r'[A-Z]'

@repetition
def lower():
    """Match a letter."""
    return r'[a-z]'

@repetition
def between(start_char, end_char):
    """Match any character between `start_char` and `end_char`."""
    return f'[{start_char}-{end_char}]'

@repetition
def in_(chars):
    """Match any character in `chars`."""
    return f'[{chars}]'

@repetition
def notin(chars):
    """Match any character not in `chars`."""
    return f'[^{chars}]'

@repetition
def space():
    """Match a space."""
    return r'\s'

@repetition
def any():
    """Match any character."""
    return r'.'


# Whitespace characters
@repetition
def newline():
    """Match a newline."""
    return r'\n'

@repetition
def tab():
    """Match a tab."""
    return r'\t'

@repetition
def carriage():
    """Match a carriage return."""
    return r'\r'


# Conditionals
def or_(*patterns):
    """Match any of the given patterns."""
    joined = '|'.join(str(p) for p in patterns)
    return Pattern(f'({joined})')

def may(pattern):
    """Match zero or one occurrence of the pattern."""
    return Pattern(f'{pattern}?')


# Anchors
def start():
    """Match the start of the string."""
    return Pattern(r'^')

def end():
    """Match the end of the string."""
    return Pattern(r'$')

def bound(text):
    """Match the exact word `text`."""
    return Pattern(r'\b')


# Lookarounds
def ahead(pattern):
    """Match if the pattern matches ahead."""
    return Pattern(f'(?={pattern})')

def behind(pattern):
    """Match if the pattern matches behind."""
    return Pattern(f'(?<={pattern})')

def notahead(pattern):
    """Match if the pattern does not match ahead."""
    return Pattern(f'(?!{pattern})')

def notbehind(pattern):
    """Match if the pattern does not match behind."""
    return Pattern(f'(?<!{pattern})')


# Grouping
def group(name, *patterns):
    """Create a named capture group with the given patterns."""
    joined = ''.join(str(p) for p in patterns)
    return Pattern(f'(?P<{name}>{joined})')

def merge(*patterns):
    """Create a non-capturing group with the given patterns."""
    joined = ''.join(str(p) for p in patterns)
    return Pattern(f'(?:{joined})')
