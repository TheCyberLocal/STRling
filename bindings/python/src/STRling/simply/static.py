from .pattern import Pattern, lit
from STRling.core import nodes


def alpha_num(min_rep: int = None, max_rep: int = None):
    """
    Matches any letter (uppercase or lowercase) or digit.

    Parameters: (min_rep, max_rep)
    - min_rep (optional): Specifies the minimum number of characters to match.
    - max_rep (optional): Specifies the maximum number of characters to match, 0 means unlimited, None means match exact count of min_rep.

    Returns:
    - An instance of the Pattern class.
    """
    node = nodes.CharClass(False, [
        nodes.ClassRange('A', 'Z'),
        nodes.ClassRange('a', 'z'),
        nodes.ClassRange('0', '9')
    ])
    p = Pattern(node, custom_set=True)
    return p(min_rep, max_rep) if min_rep is not None else p


def not_alpha_num(min_rep: int = None, max_rep: int = None):
    """
    Matches any character that is not a letter or digit.

    Parameters: (min_rep, max_rep)
    - min_rep (optional): Specifies the minimum number of characters to match.
    - max_rep (optional): Specifies the maximum number of characters to match, 0 means unlimited, None means match exact count of min_rep.

    Returns:
    - An instance of the Pattern class.
    """
    node = nodes.CharClass(True, [
        nodes.ClassRange('A', 'Z'),
        nodes.ClassRange('a', 'z'),
        nodes.ClassRange('0', '9')
    ])
    p = Pattern(node, custom_set=True, negated=True)
    return p(min_rep, max_rep) if min_rep is not None else p


def special_char(min_rep: int = None, max_rep: int = None):
    r"""
    Matches any special character. => !"#$%&'()*+,-./:;<=>?@[\]^_`{|}~

    Parameters: (min_rep, max_rep)
    - min_rep (optional): Specifies the minimum number of characters to match.
    - max_rep (optional): Specifies the maximum number of characters to match, 0 means unlimited, None means match exact count of min_rep.

    Returns:
    - An instance of the Pattern class.
    """
    special = r"""!"#$%&'()*+,-./:;<=>?@[\]^_`{|}~"""
    items = [nodes.ClassLiteral(char) for char in special]
    node = nodes.CharClass(False, items)
    p = Pattern(node, custom_set=True)
    return p(min_rep, max_rep) if min_rep is not None else p


def not_special_char(min_rep: int = None, max_rep: int = None):
    r"""
    Matches anything but a special character. => !"#$%&'()*+,-./:;<=>?@[\]^_`{|}~

    Parameters: (min_rep, max_rep)
    - min_rep (optional): Specifies the minimum number of characters to match.
    - max_rep (optional): Specifies the maximum number of characters to match, 0 means unlimited, None means match exact count of min_rep.

    Returns:
    - An instance of the Pattern class.
    """
    special = r"""!"#$%&'()*+,-./:;<=>?@[\]^_`{|}~"""
    items = [nodes.ClassLiteral(char) for char in special]
    node = nodes.CharClass(True, items)
    p = Pattern(node, custom_set=True, negated=True)
    return p(min_rep, max_rep) if min_rep is not None else p


def letter(min_rep: int = None, max_rep: int = None):
    """
    Matches any letter (uppercase or lowercase).

    Parameters: (min_rep, max_rep)
    - min_rep (optional): Specifies the minimum number of characters to match.
    - max_rep (optional): Specifies the maximum number of characters to match, 0 means unlimited, None means match exact count of min_rep.

    Returns:
    - An instance of the Pattern class.
    """
    node = nodes.CharClass(False, [
        nodes.ClassRange('A', 'Z'),
        nodes.ClassRange('a', 'z'),
    ])
    p = Pattern(node, custom_set=True)
    return p(min_rep, max_rep) if min_rep is not None else p


def not_letter(min_rep: int = None, max_rep: int = None):
    """
    Matches any character that is not a letter.

    Parameters: (min_rep, max_rep)
    - min_rep (optional): Specifies the minimum number of characters to match.
    - max_rep (optional): Specifies the maximum number of characters to match, 0 means unlimited, None means match exact count of min_rep.

    Returns:
    - An instance of the Pattern class.
    """
    node = nodes.CharClass(True, [
        nodes.ClassRange('A', 'Z'),
        nodes.ClassRange('a', 'z'),
    ])
    p = Pattern(node, custom_set=True, negated=True)
    return p(min_rep, max_rep) if min_rep is not None else p


def upper(min_rep: int = None, max_rep: int = None):
    """
    Matches any uppercase letter.

    Parameters: (min_rep, max_rep)
    - min_rep (optional): Specifies the minimum number of characters to match.
    - max_rep (optional): Specifies the maximum number of characters to match, 0 means unlimited, None means match exact count of min_rep.

    Returns:
    - An instance of the Pattern class.
    """
    node = nodes.CharClass(False, [
        nodes.ClassRange('A', 'Z'),
    ])
    p = Pattern(node, custom_set=True)
    return p(min_rep, max_rep) if min_rep is not None else p


def not_upper(min_rep: int = None, max_rep: int = None):
    """
    Matches any character that is not an uppercase letter.

    Parameters: (min_rep, max_rep)
    - min_rep (optional): Specifies the minimum number of characters to match.
    - max_rep (optional): Specifies the maximum number of characters to match, 0 means unlimited, None means match exact count of min_rep.

    Returns:
    - An instance of the Pattern class.
    """
    node = nodes.CharClass(True, [
        nodes.ClassRange('A', 'Z'),
    ])
    p = Pattern(node, custom_set=True, negated=True)
    return p(min_rep, max_rep) if min_rep is not None else p


def lower(min_rep: int = None, max_rep: int = None):
    """
    Matches any lowercase letter.

    Parameters: (min_rep, max_rep)
    - min_rep (optional): Specifies the minimum number of characters to match.
    - max_rep (optional): Specifies the maximum number of characters to match, 0 means unlimited, None means match exact count of min_rep.

    Returns:
    - An instance of the Pattern class.
    """
    node = nodes.CharClass(False, [
        nodes.ClassRange('a', 'z'),
    ])
    p = Pattern(node, custom_set=True)
    return p(min_rep, max_rep) if min_rep is not None else p


def not_lower(min_rep: int = None, max_rep: int = None):
    """
    Matches any character that is not a lowercase letter.

    Parameters: (min_rep, max_rep)
    - min_rep (optional): Specifies the minimum number of characters to match.
    - max_rep (optional): Specifies the maximum number of characters to match, 0 means unlimited, None means match exact count of min_rep.

    Returns:
    - An instance of the Pattern class.
    """
    node = nodes.CharClass(True, [
        nodes.ClassRange('a', 'z'),
    ])
    p = Pattern(node, custom_set=True, negated=True)
    return p(min_rep, max_rep) if min_rep is not None else p


def hex_digit(min_rep: int = None, max_rep: int = None):
    """
    Matches any hex-digit character.
    A hex-digit character is any letter A through F (uppercase or lowercase) or any digit (0-9).

    Parameters: (min_rep, max_rep)
    - min_rep (optional): Specifies the minimum number of characters to match.
    - max_rep (optional): Specifies the maximum number of characters to match, 0 means unlimited, None means match exact count of min_rep.

    Returns:
    - An instance of the Pattern class.
    """
    node = nodes.CharClass(False, [
        nodes.ClassRange('A', 'F'),
        nodes.ClassRange('a', 'f'),
        nodes.ClassRange('0', '9'),
    ])
    p = Pattern(node, custom_set=True)
    return p(min_rep, max_rep) if min_rep is not None else p


def not_hex_digit(min_rep: int = None, max_rep: int = None):
    """
    Matches anything but a hex-digit character.
    A hex-digit character is any letter A through F (uppercase or lowercase) or any digit (0-9).

    Parameters: (min_rep, max_rep)
    - min_rep (optional): Specifies the minimum number of characters to match.
    - max_rep (optional): Specifies the maximum number of characters to match, 0 means unlimited, None means match exact count of min_rep.

    Returns:
    - An instance of the Pattern class.
    """
    node = nodes.CharClass(True, [
        nodes.ClassRange('A', 'F'),
        nodes.ClassRange('a', 'f'),
        nodes.ClassRange('0', '9'),
    ])
    p = Pattern(node, custom_set=True, negated=True)
    return p(min_rep, max_rep) if min_rep is not None else p



############################
# Predefined Char Sets
########


def digit(min_rep: int = None, max_rep: int = None):
    """
    Matches any digit.

    Parameters: (min_rep, max_rep)
    - min_rep (optional): Specifies the minimum number of characters to match.
    - max_rep (optional): Specifies the maximum number of characters to match, 0 means unlimited, None means match exact count of min_rep.

    Returns:
    - An instance of the Pattern class.
    """
    node = nodes.CharClass(False, [nodes.ClassEscape('d')])
    p = Pattern(node)
    return p(min_rep, max_rep) if min_rep is not None else p


def not_digit(min_rep: int = None, max_rep: int = None):
    """
    Matches any character that is not a digit.

    Parameters: (min_rep, max_rep)
    - min_rep (optional): Specifies the minimum number of characters to match.
    - max_rep (optional): Specifies the maximum number of characters to match, 0 means unlimited, None means match exact count of min_rep.

    Returns:
    - An instance of the Pattern class.
    """
    node = nodes.CharClass(False, [nodes.ClassEscape('D')])
    p = Pattern(node)
    return p(min_rep, max_rep) if min_rep is not None else p


def whitespace(min_rep: int = None, max_rep: int = None):
    """
    Matches any whitespace character. (Whitespaces include space, tab, newline, carriage return, etc.)

    Parameters: (min_rep, max_rep)
    - min_rep (optional): Specifies the minimum number of characters to match.
    - max_rep (optional): Specifies the maximum number of characters to match, 0 means unlimited, None means match exact count of min_rep.

    Returns:
    - An instance of the Pattern class.
    """
    node = nodes.CharClass(False, [nodes.ClassEscape('s')])
    p = Pattern(node)
    return p(min_rep, max_rep) if min_rep is not None else p


def not_whitespace(min_rep: int = None, max_rep: int = None):
    """
    Matches any character that is not a whitespace character. (Whitespaces include space, tab, newline, carriage return, etc.)

    Parameters: (min_rep, max_rep)
    - min_rep (optional): Specifies the minimum number of characters to match.
    - max_rep (optional): Specifies the maximum number of characters to match, 0 means unlimited, None means match exact count of min_rep.

    Returns:
    - An instance of the Pattern class.
    """
    node = nodes.CharClass(False, [nodes.ClassEscape('S')])
    p = Pattern(node)
    return p(min_rep, max_rep) if min_rep is not None else p


def newline(min_rep: int = None, max_rep: int = None):
    """
    Matches a newline character.

    Parameters: (min_rep, max_rep)
    - min_rep (optional): Specifies the minimum number of characters to match.
    - max_rep (optional): Specifies the maximum number of characters to match, 0 means unlimited, None means match exact count of min_rep.

    Returns:
    - An instance of the Pattern class.
    """
    node = nodes.CharClass(False, [nodes.ClassEscape('n')])
    p = Pattern(node)
    return p(min_rep, max_rep) if min_rep is not None else p


def not_newline(min_rep: int = None, max_rep: int = None):
    """
    Matches any character that is not a newline.

    Parameters: (min_rep, max_rep)
    - min_rep (optional): Specifies the minimum number of characters to match.
    - max_rep (optional): Specifies the maximum number of characters to match, 0 means unlimited, None means match exact count of min_rep.

    Returns:
    - An instance of the Pattern class.
    """
    node = nodes.CharClass(False, [nodes.ClassEscape('r')])
    p = Pattern(node)
    return p(min_rep, max_rep) if min_rep is not None else p


def tab(min_rep: int = None, max_rep: int = None):
    """
    Matches a tab character.

    Parameters: (min_rep, max_rep)
    - min_rep (optional): Specifies the minimum number of characters to match.
    - max_rep (optional): Specifies the maximum number of characters to match, 0 means unlimited, None means match exact count of min_rep.

    Returns:
    - An instance of the Pattern class.
    """
    node = nodes.CharClass(False, [nodes.ClassEscape('t')])
    p = Pattern(node)
    return p(min_rep, max_rep) if min_rep is not None else p


def carriage(min_rep: int = None, max_rep: int = None):
    """
    Matches a carriage return character.

    Parameters: (min_rep, max_rep)
    - min_rep (optional): Specifies the minimum number of characters to match.
    - max_rep (optional): Specifies the maximum number of characters to match, 0 means unlimited, None means match exact count of min_rep.

    Returns:
    - An instance of the Pattern class.
    """
    node = nodes.CharClass(False, [nodes.ClassEscape('r')])
    p = Pattern(node)
    return p(min_rep, max_rep) if min_rep is not None else p


def bound(min_rep: int = None, max_rep: int = None):
    """
    Matches a boundary character.

    Parameters: (min_rep, max_rep)
    - min_rep (optional): Specifies the minimum number of characters to match.
    - max_rep (optional): Specifies the maximum number of characters to match, 0 means unlimited, None means match exact count of min_rep.

    Returns:
    - An instance of the Pattern class.
    """
    node = nodes.CharClass(False, [nodes.ClassEscape('b')])
    p = Pattern(node)
    return p(min_rep, max_rep) if min_rep is not None else p


def not_bound(min_rep: int = None, max_rep: int = None):
    """
    Matches any character that is not a boundary.

    Parameters: (min_rep, max_rep)
    - min_rep (optional): Specifies the minimum number of characters to match.
    - max_rep (optional): Specifies the maximum number of characters to match, 0 means unlimited, None means match exact count of min_rep.

    Returns:
    - An instance of the Pattern class.
    """
    node = nodes.CharClass(False, [nodes.ClassEscape('B')])
    p = Pattern(node)
    return p(min_rep, max_rep) if min_rep is not None else p


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
