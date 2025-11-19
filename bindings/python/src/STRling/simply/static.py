r"""
Predefined character classes and static patterns for STRling.

This module provides convenient functions for matching common character types
(letters, digits, whitespace, etc.) and special patterns (any character, word
boundaries, etc.). These are the most frequently used building blocks for
pattern construction, offering a clean alternative to regex shorthand classes
like \d, \w, \s, etc.
"""

from .pattern import Pattern, lit
from STRling.core import nodes


def alpha_num(min_rep: int = None, max_rep: int = None):
    """
    Matches any alphanumeric character (letter or digit).

    Creates a pattern that matches uppercase letters (A-Z), lowercase letters
    (a-z), or digits (0-9). This is equivalent to `[A-Za-z0-9]` in traditional regex.

    Parameters
    ----------
    min_rep : int, optional
        Minimum number of characters to match. If None, matches exactly once.
    max_rep : int, optional
        Maximum number of characters to match. Use 0 for unlimited repetition.
        If None, matches exactly min_rep times.

    Returns
    -------
    Pattern
        A new Pattern object representing the alphanumeric character class.

    Examples
    --------
    Simple Use: Match a single alphanumeric character
        >>> import STRling.simply as s
        >>> import re
        >>> pattern = s.alpha_num()
        >>> bool(re.search(str(pattern), 'A'))
        True
        >>> bool(re.search(str(pattern), '5'))
        True
        >>> bool(re.search(str(pattern), '@'))
        False

    Advanced Use: Match username (3-16 alphanumeric characters)
        >>> username = s.alpha_num(3, 16)
        >>> bool(re.match(str(username), 'user123'))
        True
        >>> bool(re.match(str(username), 'ab'))
        False

    Notes
    -----
    When min_rep and max_rep are both None, matches exactly one character.
    When only min_rep is provided and max_rep is None, matches exactly min_rep characters.
    When max_rep is 0, matches min_rep or more characters (unlimited).

    See Also
    --------
    not_alpha_num : For matching non-alphanumeric characters
    letter : For matching only letters
    digit : For matching only digits
    """
    node = nodes.CharacterClass(False, [
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
    node = nodes.CharacterClass(True, [
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
    node = nodes.CharacterClass(False, items)
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
    node = nodes.CharacterClass(True, items)
    p = Pattern(node, custom_set=True, negated=True)
    return p(min_rep, max_rep) if min_rep is not None else p


def letter(min_rep: int = None, max_rep: int = None):
    """
    Matches any letter (uppercase or lowercase).

    Creates a pattern that matches uppercase letters (A-Z) or lowercase letters
    (a-z). This is equivalent to `[A-Za-z]` in traditional regex.

    Parameters
    ----------
    min_rep : int, optional
        Minimum number of characters to match. If None, matches exactly once.
    max_rep : int, optional
        Maximum number of characters to match. Use 0 for unlimited repetition.
        If None, matches exactly min_rep times.

    Returns
    -------
    Pattern
        A new Pattern object representing the letter character class.

    Examples
    --------
    Simple Use: Match a single letter
        >>> import STRling.simply as s
        >>> import re
        >>> pattern = s.letter()
        >>> bool(re.search(str(pattern), 'A'))
        True
        >>> bool(re.search(str(pattern), '5'))
        False

    Advanced Use: Match word (1 or more letters)
        >>> word = s.letter(1, 0)
        >>> bool(re.match(str(word), 'hello'))
        True

    Notes
    -----
    This matches both uppercase and lowercase letters. For case-specific
    matching, use `upper()` or `lower()` instead.

    See Also
    --------
    not_letter : For matching non-letter characters
    upper : For matching only uppercase letters
    lower : For matching only lowercase letters
    alpha_num : For matching letters or digits
    """
    node = nodes.CharacterClass(False, [
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
    node = nodes.CharacterClass(True, [
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
    node = nodes.CharacterClass(False, [
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
    node = nodes.CharacterClass(True, [
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
    node = nodes.CharacterClass(False, [
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
    node = nodes.CharacterClass(True, [
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
    node = nodes.CharacterClass(False, [
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
    node = nodes.CharacterClass(True, [
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
    r"""
    Matches any decimal digit (0-9).

    Creates a pattern that matches any digit from 0 to 9. This is equivalent
    to `[0-9]` or `\d` in traditional regex.

    Parameters
    ----------
    min_rep : int, optional
        Minimum number of digits to match. If None, matches exactly once.
    max_rep : int, optional
        Maximum number of digits to match. Use 0 for unlimited repetition.
        If None, matches exactly min_rep times.

    Returns
    -------
    Pattern
        A new Pattern object representing the digit character class.

    Examples
    --------
    Simple Use: Match a single digit
        >>> import STRling.simply as s
        >>> import re
        >>> pattern = s.digit()
        >>> bool(re.search(str(pattern), '5'))
        True
        >>> bool(re.search(str(pattern), 'A'))
        False

    Advanced Use: Match phone number (10 digits)
        >>> phone = s.digit(10)
        >>> bool(re.match(str(phone), '5551234567'))
        True

    Advanced Use: Match year (4 digits)
        >>> year = s.digit(4, 4)
        >>> bool(re.match(str(year), '2024'))
        True

    See Also
    --------
    not_digit : For matching non-digit characters
    hex_digit : For matching hexadecimal digits (0-9, A-F)
    alpha_num : For matching letters or digits
    """
    node = nodes.CharacterClass(False, [nodes.ClassEscape('d')])
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
    node = nodes.CharacterClass(False, [nodes.ClassEscape('D')])
    p = Pattern(node)
    return p(min_rep, max_rep) if min_rep is not None else p


def whitespace(min_rep: int = None, max_rep: int = None):
    r"""
    Matches any whitespace character.

    Creates a pattern that matches whitespace characters including space, tab,
    newline, carriage return, form feed, and vertical tab. This is equivalent
    to `\s` in traditional regex.

    Parameters
    ----------
    min_rep : int, optional
        Minimum number of whitespace characters to match. If None, matches exactly once.
    max_rep : int, optional
        Maximum number of whitespace characters to match. Use 0 for unlimited
        repetition. If None, matches exactly min_rep times.

    Returns
    -------
    Pattern
        A new Pattern object representing the whitespace character class.

    Examples
    --------
    Simple Use: Match a single whitespace
        >>> import STRling.simply as s
        >>> import re
        >>> pattern = s.whitespace()
        >>> bool(re.search(str(pattern), ' '))
        True
        >>> bool(re.search(str(pattern), '\t'))
        True

    Advanced Use: Match words separated by whitespace
        >>> word = s.letter(1, 0)
        >>> space = s.whitespace(1, 0)
        >>> words = s.merge(word, space, word)
        >>> bool(re.match(str(words), 'hello world'))
        True

    Notes
    -----
    Whitespace characters include: space ( ), tab (\t), newline (\n),
    carriage return (\r), form feed (\f), and vertical tab (\v).

    See Also
    --------
    not_whitespace : For matching non-whitespace characters
    newline : For matching only newline characters
    tab : For matching only tab characters
    """
    node = nodes.CharacterClass(False, [nodes.ClassEscape('s')])
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
    node = nodes.CharacterClass(False, [nodes.ClassEscape('S')])
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
    node = nodes.CharacterClass(False, [nodes.ClassEscape('n')])
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
    node = nodes.CharacterClass(False, [nodes.ClassEscape('r')])
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
    node = nodes.CharacterClass(False, [nodes.ClassEscape('t')])
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
    node = nodes.CharacterClass(False, [nodes.ClassEscape('r')])
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
    node = nodes.CharacterClass(False, [nodes.ClassEscape('b')])
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
    node = nodes.CharacterClass(False, [nodes.ClassEscape('B')])
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
    node = nodes.Anchor("Start")
    return Pattern(node)


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
    node = nodes.Anchor("End")
    return Pattern(node)
