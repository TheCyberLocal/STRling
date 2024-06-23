
from .pattern import Pattern



############################
# Custom Char Sets
########


def letter(min: int = None, max: int = None):
    """
    Matches any letter (uppercase or lowercase).

    Parameters: (min/exact, max)
    - min (optional): Specifies the minimum number of characters to match.
    - max (optional): Specifies the maximum number of characters to match.

    Special Cases:
    - If only `min` is specified, it represents the exact number of characters to match.
    - If `max` is 0, it means there is no upper limit.

    Returns: An instance of the Pattern class.
    """
    return Pattern(r'[A-Za-z]', custom_set=True)(min, max)


def not_letter(min: int = None, max: int = None):
    """
    Matches any character that is not a letter.

    Parameters: (min/exact, max)
    - min (optional): Specifies the minimum number of characters to match.
    - max (optional): Specifies the maximum number of characters to match.

    Special Cases:
    - If only `min` is specified, it represents the exact number of characters to match.
    - If `max` is 0, it means there is no upper limit.

    Returns: An instance of the Pattern class.
    """
    return Pattern(r'[^A-Za-z]', custom_set=True, negated_set=True)(min, max)


def upper(min: int = None, max: int = None):
    """
    Matches any uppercase letter.

    Parameters: (min/exact, max)
    - min (optional): Specifies the minimum number of characters to match.
    - max (optional): Specifies the maximum number of characters to match.

    Special Cases:
    - If only `min` is specified, it represents the exact number of characters to match.
    - If `max` is 0, it means there is no upper limit.

    Returns: An instance of the Pattern class.
    """
    return Pattern(r'[A-Z]', custom_set=True)(min, max)


def not_upper(min: int = None, max: int = None):
    """
    Matches any character that is not an uppercase letter.

    Parameters: (min/exact, max)
    - min (optional): Specifies the minimum number of characters to match.
    - max (optional): Specifies the maximum number of characters to match.

    Special Cases:
    - If only `min` is specified, it represents the exact number of characters to match.
    - If `max` is 0, it means there is no upper limit.

    Returns: An instance of the Pattern class.
    """
    return Pattern(r'[^A-Z]', custom_set=True, negated_set=True)(min, max)


def lower(min: int = None, max: int = None):
    """
    Matches any lowercase letter.

    Parameters: (min/exact, max)
    - min (optional): Specifies the minimum number of characters to match.
    - max (optional): Specifies the maximum number of characters to match.

    Special Cases:
    - If only `min` is specified, it represents the exact number of characters to match.
    - If `max` is 0, it means there is no upper limit.

    Returns: An instance of the Pattern class.
    """
    return Pattern(r'[a-z]', custom_set=True)(min, max)


def not_lower(min: int = None, max: int = None):
    """
    Matches any character that is not a lowercase letter.

    Parameters: (min/exact, max)
    - min (optional): Specifies the minimum number of characters to match.
    - max (optional): Specifies the maximum number of characters to match.

    Special Cases:
    - If only `min` is specified, it represents the exact number of characters to match.
    - If `max` is 0, it means there is no upper limit.

    Returns: An instance of the Pattern class.
    """
    return Pattern(r'[^a-z]', custom_set=True, negated_set=True)(min, max)



############################
# Predefined Char Sets
########


def digit(min: int = None, max: int = None):
    """
    Matches any digit.

    Parameters: (min/exact, max)
    - min (optional): Specifies the minimum number of characters to match.
    - max (optional): Specifies the maximum number of characters to match.

    Special Cases:
    - If only `min` is specified, it represents the exact number of characters to match.
    - If `max` is 0, it means there is no upper limit.

    Returns: An instance of the Pattern class.
    """
    return Pattern(r'\d')(min, max)


def not_digit(min: int = None, max: int = None):
    """
    Matches any character that is not a digit.

    Parameters: (min/exact, max)
    - min (optional): Specifies the minimum number of characters to match.
    - max (optional): Specifies the maximum number of characters to match.

    Special Cases:
    - If only `min` is specified, it represents the exact number of characters to match.
    - If `max` is 0, it means there is no upper limit.

    Returns: An instance of the Pattern class.
    """
    return Pattern(r'\D')(min, max)


def whitespace(min: int = None, max: int = None):
    """
    Matches any whitespace character. (Whitespaces include space, tab, newline, carriage return, etc.)

    Parameters: (min/exact, max)
    - min (optional): Specifies the minimum number of characters to match.
    - max (optional): Specifies the maximum number of characters to match.

    Special Cases:
    - If only `min` is specified, it represents the exact number of characters to match.
    - If `max` is 0, it means there is no upper limit.

    Returns: An instance of the Pattern class.
    """
    return Pattern(r'\s')(min, max)


def not_whitespace(min: int = None, max: int = None):
    """
    Matches any character that is not a whitespace character. (Whitespaces include space, tab, newline, carriage return, etc.)

    Parameters: (min/exact, max)
    - min (optional): Specifies the minimum number of characters to match.
    - max (optional): Specifies the maximum number of characters to match.

    Special Cases:
    - If only `min` is specified, it represents the exact number of characters to match.
    - If `max` is 0, it means there is no upper limit.

    Returns: An instance of the Pattern class.
    """
    return Pattern(r'\S')(min, max)


def newline(min: int = None, max: int = None):
    """
    Matches a newline character.

    Parameters: (min/exact, max)
    - min (optional): Specifies the minimum number of characters to match.
    - max (optional): Specifies the maximum number of characters to match.

    Special Cases:
    - If only `min` is specified, it represents the exact number of characters to match.
    - If `max` is 0, it means there is no upper limit.

    Returns: An instance of the Pattern class.
    """
    return Pattern(r'\n')(min, max)


def not_newline(min: int = None, max: int = None):
    """
    Matches any character that is not a newline.

    Parameters: (min/exact, max)
    - min (optional): Specifies the minimum number of characters to match.
    - max (optional): Specifies the maximum number of characters to match.

    Special Cases:
    - If only `min` is specified, it represents the exact number of characters to match.
    - If `max` is 0, it means there is no upper limit.

    Returns: An instance of the Pattern class.
    """
    return Pattern(r'.')(min, max)


def tab(min: int = None, max: int = None):
    """
    Matches a tab character.

    Parameters: (min/exact, max)
    - min (optional): Specifies the minimum number of characters to match.
    - max (optional): Specifies the maximum number of characters to match.

    Special Cases:
    - If only `min` is specified, it represents the exact number of characters to match.
    - If `max` is 0, it means there is no upper limit.

    Returns: An instance of the Pattern class.
    """
    return Pattern(r'\t')(min, max)


def not_tab(min: int = None, max: int = None):
    """
    Matches any character that is not a tab.

    Parameters: (min/exact, max)
    - min (optional): Specifies the minimum number of characters to match.
    - max (optional): Specifies the maximum number of characters to match.

    Special Cases:
    - If only `min` is specified, it represents the exact number of characters to match.
    - If `max` is 0, it means there is no upper limit.

    Returns: An instance of the Pattern class.
    """
    return Pattern(r'\T')(min, max)


def carriage(min: int = None, max: int = None):
    """
    Matches a carriage return character.

    Parameters: (min/exact, max)
    - min (optional): Specifies the minimum number of characters to match.
    - max (optional): Specifies the maximum number of characters to match.

    Special Cases:
    - If only `min` is specified, it represents the exact number of characters to match.
    - If `max` is 0, it means there is no upper limit.

    Returns: An instance of the Pattern class.
    """
    return Pattern(r'\r')(min, max)


def not_carriage(min: int = None, max: int = None):
    """
    Matches any character that is not a carriage return.

    Parameters: (min/exact, max)
    - min (optional): Specifies the minimum number of characters to match.
    - max (optional): Specifies the maximum number of characters to match.

    Special Cases:
    - If only `min` is specified, it represents the exact number of characters to match.
    - If `max` is 0, it means there is no upper limit.

    Returns: An instance of the Pattern class.
    """
    return Pattern(r'\R')(min, max)


def bound(min: int = None, max: int = None):
    """
    Matches a boundary character.

    Parameters: (min/exact, max)
    - min (optional): Specifies the minimum number of characters to match.
    - max (optional): Specifies the maximum number of characters to match.

    Special Cases:
    - If only `min` is specified, it represents the exact number of characters to match.
    - If `max` is 0, it means there is no upper limit.

    Returns: An instance of the Pattern class.
    """
    return Pattern(r'\b')(min, max)


def not_bound(min: int = None, max: int = None):
    """
    Matches any character that is not a boundary.

    Parameters: (min/exact, max)
    - min (optional): Specifies the minimum number of characters to match.
    - max (optional): Specifies the maximum number of characters to match.

    Special Cases:
    - If only `min` is specified, it represents the exact number of characters to match.
    - If `max` is 0, it means there is no upper limit.

    Returns: An instance of the Pattern class.
    """
    return Pattern(r'\B')(min, max)


def start():
    """
    Matches the start of a line.

    Parameters: None
    - This method cannot be specified a range.

    Returns: An instance of the Pattern class.

    Note: Their is no `simply.not_start()` function,
    to do this, use `simply.not_behind(simply.start())`.
    """
    return Pattern(r'^')


def end():
    """
    Matches the end of a line.

    Parameters: None
    - This method cannot be specified a range.

    Returns: An instance of the Pattern class.

    Note: Their is no `simply.not_end()` function,
    to do this, use `simply.not_ahead(simply.end())`.
    """
    return Pattern(r'$')
