import re


# Decorators
def repetition(func):
  def wrapper(*args, min=None, max=None, **kwargs):
    pattern = func(*args, **kwargs)
    pattern += repeat(min, max)
    return pattern
  return wrapper


# Range syntax
def repeat(min=None, max=None):
    """Create a range for the preceding symbol"""
    if min is not None and max is not None:
        if min > max:
            raise ValueError('min cannot be greater than max')
        return f'{{{min},{max}}}'
    elif min is not None:
        return f'{{{min}}}'
    return ''


# Literals
@repetition
def lit(text):
    """Match the literal string `text`, optionally specifying repeat."""
    return re.escape(text)

@repetition
def digit(min=None, max=None):
    """Match a digit, optionally specifying repeat."""
    return r'\d'

@repetition
def letter(min=None, max=None):
    """Match a letter."""
    return r'[A-Za-z]'

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
    joined = '|'.join(patterns)
    return f'({joined})'

def may(pattern):
    """Match zero or one occurrence of the pattern."""
    return f'{pattern}?'


# Anchors
def start():
    """Match the start of the string."""
    return r'^'

def end():
    """Match the end of the string."""
    return r'$'

def bound(text):
    """Match the exact word `text`."""
    return r'\b'


# Lookarounds
def ahead(pattern):
    """Match if the pattern matches ahead."""
    return f'(?={pattern})'

def behind(pattern):
    """Match if the pattern matches behind."""
    return f'(?<={pattern})'

def notahead(pattern):
    """Match if the pattern does not match ahead."""
    return f'(?!{pattern})'

def notbehind(pattern):
    """Match if the pattern does not match behind."""
    return f'(?<!{pattern})'


# Grouping
def group(name, *patterns):
    """Create a named capture group with the given patterns."""
    joined = ''.join(patterns)
    return f'(?P<{name}>{joined})'

def merge(*patterns):
    """Create a non-capturing group with the given patterns."""
    joined = ''.join(patterns)
    return f'(?:{joined})'
