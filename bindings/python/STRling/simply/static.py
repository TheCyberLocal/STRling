
from .pattern import Pattern



############################
# Custom Char Sets
########


def letter():
    """
    Matches any letter (uppercase or lowercase).

    Parameters: (min/exact, max)
     - min (optional): Specifies the minimum number of characters to match.
     - max (optional): Specifies the maximum number of characters to match.

    Special Cases:
     - If only `min` is specified, it represents the exact number of characters to match.
     - If `max` is 0, it means there is no upper limit.
    """
    return Pattern(r'[A-Za-z]', custom_set=True)

def upper():
    """
    Matches any uppercase letter.

    Parameters: (min/exact, max)
     - min (optional): Specifies the minimum number of characters to match.
     - max (optional): Specifies the maximum number of characters to match.

    Special Cases:
     - If only `min` is specified, it represents the exact number of characters to match.
     - If `max` is 0, it means there is no upper limit.
    """
    return Pattern(r'[A-Z]', custom_set=True)

def lower():
    """
    Matches any lowercase letter.

    Parameters: (min/exact, max)
     - min (optional): Specifies the minimum number of characters to match.
     - max (optional): Specifies the maximum number of characters to match.

    Special Cases:
     - If only `min` is specified, it represents the exact number of characters to match.
     - If `max` is 0, it means there is no upper limit.
    """
    return Pattern(r'[a-z]', custom_set=True)



############################
# Predefined Char Sets
########


def digit():
    """
    Matches any digit.

    Parameters: (min/exact, max)
     - min (optional): Specifies the minimum number of characters to match.
     - max (optional): Specifies the maximum number of characters to match.

    Special Cases:
     - If only `min` is specified, it represents the exact number of characters to match.
     - If `max` is 0, it means there is no upper limit.
    """
    return Pattern(r'\d')

def space():
    """
    Matches any whitespace character.

    Parameters: (min/exact, max)
     - min (optional): Specifies the minimum number of characters to match.
     - max (optional): Specifies the maximum number of characters to match.

    Special Cases:
     - If only `min` is specified, it represents the exact number of characters to match.
     - If `max` is 0, it means there is no upper limit.
    """
    return Pattern(r'\s')

def not_newline():
    """
    Matches any character except a newline.

    Parameters: (min/exact, max)
     - min (optional): Specifies the minimum number of characters to match.
     - max (optional): Specifies the maximum number of characters to match.

    Special Cases:
     - If only `min` is specified, it represents the exact number of characters to match.
     - If `max` is 0, it means there is no upper limit.
    """
    return Pattern(r'.')

def newline():
    """
    Matches a newline character.

    Parameters: (min/exact, max)
     - min (optional): Specifies the minimum number of characters to match.
     - max (optional): Specifies the maximum number of characters to match.

    Special Cases:
     - If only `min` is specified, it represents the exact number of characters to match.
     - If `max` is 0, it means there is no upper limit.
    """
    return Pattern(r'\n')

def tab():
    """
    Matches a tab character.

    Parameters: (min/exact, max)
     - min (optional): Specifies the minimum number of characters to match.
     - max (optional): Specifies the maximum number of characters to match.

    Special Cases:
     - If only `min` is specified, it represents the exact number of characters to match.
     - If `max` is 0, it means there is no upper limit.
    """
    return Pattern(r'\t')

def carriage():
    """
    Matches a carriage return character.

    Parameters: (min/exact, max)
     - min (optional): Specifies the minimum number of characters to match.
     - max (optional): Specifies the maximum number of characters to match.

    Special Cases:
     - If only `min` is specified, it represents the exact number of characters to match.
     - If `max` is 0, it means there is no upper limit.
    """
    return Pattern(r'\r')

def bound():
    """
    Matches a boundary character.

    Parameters: (min/exact, max)
     - min (optional): Specifies the minimum number of characters to match.
     - max (optional): Specifies the maximum number of characters to match.

    Special Cases:
     - If only `min` is specified, it represents the exact number of characters to match.
     - If `max` is 0, it means there is no upper limit.
    """
    return Pattern(r'\b')

def start():
    """
    Matches the start of a line.

    Parameters: None
     - This method doesn't take a specified range of characters to meet.
    """
    return Pattern(r'^')

def end():
    """
    Matches the end of a line.

    Parameters: None
     - This method doesn't take a specified range of characters to meet.
    """
    return Pattern(r'$')
