
from .pattern import Pattern



############################
# Custom Char Sets
########


def letter():
    """Matches any letter (uppercase or lowercase)."""
    return Pattern(r'[A-Za-z]', custom_set=True)

def upper():
    """Matches any uppercase letter."""
    return Pattern(r'[A-Z]', custom_set=True)

def lower():
    """Matches any lowercase letter."""
    return Pattern(r'[a-z]', custom_set=True)



############################
# Predefined Char Sets
########


def digit():
    """Matches any digit."""
    return Pattern(r'\d')

def space():
    """Matches any whitespace character."""
    return Pattern(r'\s')

def not_newline():
    """Matches any character except a newline."""
    return Pattern(r'.')

def newline():
    """Matches a newline character."""
    return Pattern(r'\n')

def tab():
    """Matches a tab character."""
    return Pattern(r'\t')

def carriage():
    """Matches a carriage return character."""
    return Pattern(r'\r')

def bound():
    """Matches a boundary character."""
    return Pattern(r'\b')

def start():
    """Matches the start of a line."""
    return Pattern(r'^')

def end():
    """Matches the end of a line."""
    return Pattern(r'$')
