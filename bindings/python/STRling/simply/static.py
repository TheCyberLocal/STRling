
from .pattern import Pattern, lit



############################
# Custom Char Sets
########

def special_char(min_rep: int = None, max_rep: int = None):
    """
    Matches any special character. => !"#$%&'()*+,-./:;<=>?@[\]^_`{|}~

    Parameters: (min_rep/exact_rep, max_rep)
    - min_rep (optional): Specifies the minimum number of characters to match.
    - max_rep (optional): Specifies the maximum number of characters to match.

    Special Cases:
    - If only `min_rep` is specified, it represents the exact number of characters to match.
    - If `max_rep` is 0, it means there is no upper limit.

    Returns:
    - An instance of the Pattern class.
    """
    special = lit("""!"#$%&'()*+,-./:;<=>?@[\]^_`{|}~""")
    return Pattern(f'[{str(special)}]', custom_set=True)(min_rep, max_rep)


def not_special_char(min_rep: int = None, max_rep: int = None):
    """
    Matches anything but a special character. => !"#$%&'()*+,-./:;<=>?@[\]^_`{|}~

    Parameters: (min_rep/exact_rep, max_rep)
    - min_rep (optional): Specifies the minimum number of characters to match.
    - max_rep (optional): Specifies the maximum number of characters to match.

    Special Cases:
    - If only `min_rep` is specified, it represents the exact number of characters to match.
    - If `max_rep` is 0, it means there is no upper limit.

    Returns:
    - An instance of the Pattern class.
    """
    special = lit("""!"#$%&'()*+,-./:;<=>?@[\]^_`{|}~""")
    return Pattern(f'[^{str(special)}]', custom_set=True, negated=True)(min_rep, max_rep)


def word_char(min_rep: int = None, max_rep: int = None):
    """
    Matches any word character.
    A word character is any case letter, a digit, or an underscore.

    Parameters: (min_rep/exact_rep, max_rep)
    - min_rep (optional): Specifies the minimum number of characters to match.
    - max_rep (optional): Specifies the maximum number of characters to match.

    Special Cases:
    - If only `min_rep` is specified, it represents the exact number of characters to match.
    - If `max_rep` is 0, it means there is no upper limit.

    Returns:
    - An instance of the Pattern class.
    """
    return Pattern(r'[a-zA-Z0-9_]', custom_set=True)(min_rep, max_rep)


def not_word_char(min_rep: int = None, max_rep: int = None):
    """
    Matches anything but a word character.
    A word character is any case letter, a digit, or an underscore.

    Parameters: (min_rep/exact_rep, max_rep)
    - min_rep (optional): Specifies the minimum number of characters to match.
    - max_rep (optional): Specifies the maximum number of characters to match.

    Special Cases:
    - If only `min_rep` is specified, it represents the exact number of characters to match.
    - If `max_rep` is 0, it means there is no upper limit.

    Returns:
    - An instance of the Pattern class.
    """
    return Pattern(r'[^a-zA-Z0-9_]', custom_set=True, negated=True)(min_rep, max_rep)


def letter(min_rep: int = None, max_rep: int = None):
    """
    Matches any letter (uppercase or lowercase).

    Parameters: (min_rep/exact_rep, max_rep)
    - min_rep (optional): Specifies the minimum number of characters to match.
    - max_rep (optional): Specifies the maximum number of characters to match.

    Special Cases:
    - If only `min_rep` is specified, it represents the exact number of characters to match.
    - If `max_rep` is 0, it means there is no upper limit.

    Returns:
    - An instance of the Pattern class.
    """
    return Pattern(r'[A-Za-z]', custom_set=True)(min_rep, max_rep)


def not_letter(min_rep: int = None, max_rep: int = None):
    """
    Matches any character that is not a letter.

    Parameters: (min_rep/exact_rep, max_rep)
    - min_rep (optional): Specifies the minimum number of characters to match.
    - max_rep (optional): Specifies the maximum number of characters to match.

    Special Cases:
    - If only `min_rep` is specified, it represents the exact number of characters to match.
    - If `max_rep` is 0, it means there is no upper limit.

    Returns:
    - An instance of the Pattern class.
    """
    return Pattern(r'[^A-Za-z]', custom_set=True, negated=True)(min_rep, max_rep)


def upper(min_rep: int = None, max_rep: int = None):
    """
    Matches any uppercase letter.

    Parameters: (min_rep/exact_rep, max_rep)
    - min_rep (optional): Specifies the minimum number of characters to match.
    - max_rep (optional): Specifies the maximum number of characters to match.

    Special Cases:
    - If only `min_rep` is specified, it represents the exact number of characters to match.
    - If `max_rep` is 0, it means there is no upper limit.

    Returns:
    - An instance of the Pattern class.
    """
    return Pattern(r'[A-Z]', custom_set=True)(min_rep, max_rep)


def not_upper(min_rep: int = None, max_rep: int = None):
    """
    Matches any character that is not an uppercase letter.

    Parameters: (min_rep/exact_rep, max_rep)
    - min_rep (optional): Specifies the minimum number of characters to match.
    - max_rep (optional): Specifies the maximum number of characters to match.

    Special Cases:
    - If only `min_rep` is specified, it represents the exact number of characters to match.
    - If `max_rep` is 0, it means there is no upper limit.

    Returns:
    - An instance of the Pattern class.
    """
    return Pattern(r'[^A-Z]', custom_set=True, negated=True)(min_rep, max_rep)


def lower(min_rep: int = None, max_rep: int = None):
    """
    Matches any lowercase letter.

    Parameters: (min_rep/exact_rep, max_rep)
    - min_rep (optional): Specifies the minimum number of characters to match.
    - max_rep (optional): Specifies the maximum number of characters to match.

    Special Cases:
    - If only `min_rep` is specified, it represents the exact number of characters to match.
    - If `max_rep` is 0, it means there is no upper limit.

    Returns:
    - An instance of the Pattern class.
    """
    return Pattern(r'[a-z]', custom_set=True)(min_rep, max_rep)


def not_lower(min_rep: int = None, max_rep: int = None):
    """
    Matches any character that is not a lowercase letter.

    Parameters: (min_rep/exact_rep, max_rep)
    - min_rep (optional): Specifies the minimum number of characters to match.
    - max_rep (optional): Specifies the maximum number of characters to match.

    Special Cases:
    - If only `min_rep` is specified, it represents the exact number of characters to match.
    - If `max_rep` is 0, it means there is no upper limit.

    Returns:
    - An instance of the Pattern class.
    """
    return Pattern(r'[^a-z]', custom_set=True, negated=True)(min_rep, max_rep)



############################
# Predefined Char Sets
########


def digit(min_rep: int = None, max_rep: int = None):
    """
    Matches any digit.

    Parameters: (min_rep/exact_rep, max_rep)
    - min_rep (optional): Specifies the minimum number of characters to match.
    - max_rep (optional): Specifies the maximum number of characters to match.

    Special Cases:
    - If only `min_rep` is specified, it represents the exact number of characters to match.
    - If `max_rep` is 0, it means there is no upper limit.

    Returns:
    - An instance of the Pattern class.
    """
    return Pattern(r'\d')(min_rep, max_rep)


def not_digit(min_rep: int = None, max_rep: int = None):
    """
    Matches any character that is not a digit.

    Parameters: (min_rep/exact_rep, max_rep)
    - min_rep (optional): Specifies the minimum number of characters to match.
    - max_rep (optional): Specifies the maximum number of characters to match.

    Special Cases:
    - If only `min_rep` is specified, it represents the exact number of characters to match.
    - If `max_rep` is 0, it means there is no upper limit.

    Returns:
    - An instance of the Pattern class.
    """
    return Pattern(r'\D')(min_rep, max_rep)


def hex_digit(min_rep: int = None, max_rep: int = None):
    """
    Matches any hex-digit character.
    A hex-digit character is any letter A through F (uppercase or lowercase) or any digit (0-9).

    Parameters: (min_rep/exact_rep, max_rep)
    - min_rep (optional): Specifies the minimum number of characters to match.
    - max_rep (optional): Specifies the maximum number of characters to match.

    Special Cases:
    - If only `min_rep` is specified, it represents the exact number of characters to match.
    - If `max_rep` is 0, it means there is no upper limit.

    Returns:
    - An instance of the Pattern class.
    """
    return Pattern(r'[A-Fa-f\d]')(min_rep, max_rep)


def not_hex_digit(min_rep: int = None, max_rep: int = None):
    """
    Matches anything but a hex-digit character.
    A hex-digit character is any letter A through F (uppercase or lowercase) or any digit (0-9).

    Parameters: (min_rep/exact_rep, max_rep)
    - min_rep (optional): Specifies the minimum number of characters to match.
    - max_rep (optional): Specifies the maximum number of characters to match.

    Special Cases:
    - If only `min_rep` is specified, it represents the exact number of characters to match.
    - If `max_rep` is 0, it means there is no upper limit.

    Returns:
    - An instance of the Pattern class.
    """
    return Pattern(r'[^A-Fa-f\d]')(min_rep, max_rep)


def whitespace(min_rep: int = None, max_rep: int = None):
    """
    Matches any whitespace character. (Whitespaces include space, tab, newline, carriage return, etc.)

    Parameters: (min_rep/exact_rep, max_rep)
    - min_rep (optional): Specifies the minimum number of characters to match.
    - max_rep (optional): Specifies the maximum number of characters to match.

    Special Cases:
    - If only `min_rep` is specified, it represents the exact number of characters to match.
    - If `max_rep` is 0, it means there is no upper limit.

    Returns:
    - An instance of the Pattern class.
    """
    return Pattern(r'\s')(min_rep, max_rep)


def not_whitespace(min_rep: int = None, max_rep: int = None):
    """
    Matches any character that is not a whitespace character. (Whitespaces include space, tab, newline, carriage return, etc.)

    Parameters: (min_rep/exact_rep, max_rep)
    - min_rep (optional): Specifies the minimum number of characters to match.
    - max_rep (optional): Specifies the maximum number of characters to match.

    Special Cases:
    - If only `min_rep` is specified, it represents the exact number of characters to match.
    - If `max_rep` is 0, it means there is no upper limit.

    Returns:
    - An instance of the Pattern class.
    """
    return Pattern(r'\S')(min_rep, max_rep)


def newline(min_rep: int = None, max_rep: int = None):
    """
    Matches a newline character.

    Parameters: (min_rep/exact_rep, max_rep)
    - min_rep (optional): Specifies the minimum number of characters to match.
    - max_rep (optional): Specifies the maximum number of characters to match.

    Special Cases:
    - If only `min_rep` is specified, it represents the exact number of characters to match.
    - If `max_rep` is 0, it means there is no upper limit.

    Returns:
    - An instance of the Pattern class.
    """
    return Pattern(r'\n')(min_rep, max_rep)


def not_newline(min_rep: int = None, max_rep: int = None):
    """
    Matches any character that is not a newline.

    Parameters: (min_rep/exact_rep, max_rep)
    - min_rep (optional): Specifies the minimum number of characters to match.
    - max_rep (optional): Specifies the maximum number of characters to match.

    Special Cases:
    - If only `min_rep` is specified, it represents the exact number of characters to match.
    - If `max_rep` is 0, it means there is no upper limit.

    Returns:
    - An instance of the Pattern class.
    """
    return Pattern(r'.')(min_rep, max_rep)


def tab(min_rep: int = None, max_rep: int = None):
    """
    Matches a tab character.

    Parameters: (min_rep/exact_rep, max_rep)
    - min_rep (optional): Specifies the minimum number of characters to match.
    - max_rep (optional): Specifies the maximum number of characters to match.

    Special Cases:
    - If only `min_rep` is specified, it represents the exact number of characters to match.
    - If `max_rep` is 0, it means there is no upper limit.

    Returns:
    - An instance of the Pattern class.
    """
    return Pattern(r'\t')(min_rep, max_rep)


def not_tab(min_rep: int = None, max_rep: int = None):
    """
    Matches any character that is not a tab.

    Parameters: (min_rep/exact_rep, max_rep)
    - min_rep (optional): Specifies the minimum number of characters to match.
    - max_rep (optional): Specifies the maximum number of characters to match.

    Special Cases:
    - If only `min_rep` is specified, it represents the exact number of characters to match.
    - If `max_rep` is 0, it means there is no upper limit.

    Returns:
    - An instance of the Pattern class.
    """
    return Pattern(r'\T')(min_rep, max_rep)


def carriage(min_rep: int = None, max_rep: int = None):
    """
    Matches a carriage return character.

    Parameters: (min_rep/exact_rep, max_rep)
    - min_rep (optional): Specifies the minimum number of characters to match.
    - max_rep (optional): Specifies the maximum number of characters to match.

    Special Cases:
    - If only `min_rep` is specified, it represents the exact number of characters to match.
    - If `max_rep` is 0, it means there is no upper limit.

    Returns:
    - An instance of the Pattern class.
    """
    return Pattern(r'\r')(min_rep, max_rep)


def not_carriage(min_rep: int = None, max_rep: int = None):
    """
    Matches any character that is not a carriage return.

    Parameters: (min_rep/exact_rep, max_rep)
    - min_rep (optional): Specifies the minimum number of characters to match.
    - max_rep (optional): Specifies the maximum number of characters to match.

    Special Cases:
    - If only `min_rep` is specified, it represents the exact number of characters to match.
    - If `max_rep` is 0, it means there is no upper limit.

    Returns:
    - An instance of the Pattern class.
    """
    return Pattern(r'\R')(min_rep, max_rep)


def bound(min_rep: int = None, max_rep: int = None):
    """
    Matches a boundary character.

    Parameters: (min_rep/exact_rep, max_rep)
    - min_rep (optional): Specifies the minimum number of characters to match.
    - max_rep (optional): Specifies the maximum number of characters to match.

    Special Cases:
    - If only `min_rep` is specified, it represents the exact number of characters to match.
    - If `max_rep` is 0, it means there is no upper limit.

    Returns:
    - An instance of the Pattern class.
    """
    return Pattern(r'\b')(min_rep, max_rep)


def not_bound(min_rep: int = None, max_rep: int = None):
    """
    Matches any character that is not a boundary.

    Parameters: (min_rep/exact_rep, max_rep)
    - min_rep (optional): Specifies the minimum number of characters to match.
    - max_rep (optional): Specifies the maximum number of characters to match.

    Special Cases:
    - If only `min_rep` is specified, it represents the exact number of characters to match.
    - If `max_rep` is 0, it means there is no upper limit.

    Returns:
    - An instance of the Pattern class.
    """
    return Pattern(r'\B')(min_rep, max_rep)


def start():
    """
    Matches the start of a line.

    Parameters: None
    - This method cannot be specified a range.

    Returns:
    - An instance of the Pattern class.

    Note: There is no `simply.not_start()` function,
    to do this, use `simply.not_behind(simply.start())`.
    """
    return Pattern(r'^')


def end():
    """
    Matches the end of a line.

    Parameters: None
    - This method cannot be specified a range.

    Returns:
    - An instance of the Pattern class.

    Note: There is no `simply.not_end()` function,
    to do this, use `simply.not_ahead(simply.end())`.
    """
    return Pattern(r'$')
