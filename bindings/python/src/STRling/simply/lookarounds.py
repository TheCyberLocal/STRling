from .pattern import STRlingError, Pattern, lit
from STRling.core import nodes


def ahead(pattern):
    """
    Creates a positive lookahead assertion that checks for a pattern ahead without consuming it.

    A positive lookahead verifies that the specified pattern exists immediately after
    the current position, but does not include it in the match result. This allows
    you to enforce conditions on what follows without actually matching it.

    Parameters
    ----------
    pattern : Pattern or str
        The pattern to look ahead for. Strings are automatically converted to
        literal patterns.

    Returns
    -------
    Pattern
        A new Pattern object representing the positive lookahead assertion.

    Examples
    --------
    Simple Use: Match a digit only if followed by a letter
        >>> import STRling.simply as s
        >>> import re
        >>> pattern = s.merge(s.digit(), s.ahead(s.letter()))
        >>> match = re.search(str(pattern), '5A')
        >>> match.group()
        '5'
        >>> bool(re.search(str(pattern), '56'))
        False

    Advanced Use: Password validation requiring a digit somewhere
        >>> # Ensure password has at least one digit
        >>> has_digit = s.ahead(s.merge(s.any(), s.digit()))
        >>> password_pattern = s.merge(has_digit, s.alpha_num(8, 0))
        >>> bool(re.search(str(password_pattern), 'pass1word'))
        True
        >>> bool(re.search(str(password_pattern), 'password'))
        False

    Raises
    ------
    STRlingError
        If the pattern parameter is not a Pattern or string.

    Notes
    -----
    Lookaheads are zero-width assertions: they don't consume any characters.
    The regex engine position remains at the same spot after a lookahead check.
    
    Lookaheads can contain capturing groups, but those groups will still be
    captured even though the lookahead doesn't consume characters.

    See Also
    --------
    not_ahead : For negative lookahead (pattern must NOT be present)
    behind : For positive lookbehind (check what comes before)
    has : For checking pattern existence anywhere in the string
    """
    if isinstance(pattern, str):
        pattern = lit(pattern)

    if not isinstance(pattern, Pattern):
        message = """
        Method: simply.ahead(pattern)

        The parameter must be an instance of `Pattern` or `str`.

        Use a string such as "123abc$" to match literal characters, or use a predefined set like `simply.letter()`.
        """
        raise STRlingError(message)

    node = nodes.Look(dir="Ahead", neg=False, body=pattern.node)
    return Pattern(node, composite=True)

def not_ahead(pattern):
    """
    Creates a negative lookahead assertion that checks a pattern is NOT ahead.

    A negative lookahead verifies that the specified pattern does NOT exist
    immediately after the current position. The match succeeds only if the
    pattern is absent. Like all lookarounds, it doesn't consume any characters.

    Parameters
    ----------
    pattern : Pattern or str
        The pattern to check for absence. Strings are automatically converted
        to literal patterns.

    Returns
    -------
    Pattern
        A new Pattern object representing the negative lookahead assertion.

    Examples
    --------
    Simple Use: Match a digit only if NOT followed by a letter
        >>> import STRling.simply as s
        >>> import re
        >>> pattern = s.merge(s.digit(), s.not_ahead(s.letter()))
        >>> match = re.search(str(pattern), '56')
        >>> match.group()
        '5'
        >>> bool(re.search(str(pattern), '5A'))
        False

    Advanced Use: Match identifiers that don't end with '_tmp'
        >>> identifier = s.merge(s.letter(), s.alpha_num(0, 0))
        >>> not_temp = s.not_ahead(s.merge('_tmp', s.word_boundary()))
        >>> valid_id = s.merge(identifier, not_temp)
        >>> # This ensures we don't match temporary variable names

    Raises
    ------
    STRlingError
        If the pattern parameter is not a Pattern or string.

    Notes
    -----
    Negative lookaheads are particularly useful for:
    - Excluding certain patterns from matches
    - Implementing "not followed by" logic
    - Password validation (e.g., "must not contain spaces")
    
    Remember that lookaheads are zero-width: they verify conditions without
    consuming characters from the input.

    See Also
    --------
    ahead : For positive lookahead (pattern MUST be present)
    not_behind : For negative lookbehind (check what's NOT before)
    has_not : For checking pattern absence anywhere in the string
    """
    if isinstance(pattern, str):
        pattern = lit(pattern)

    if not isinstance(pattern, Pattern):
        message = """
        Method: simply.not_ahead(pattern)

        The parameter must be an instance of `Pattern` or `str`.

        Use a string such as "123abc$" to match literal characters, or use a predefined set like `simply.letter()`.
        """
        raise STRlingError(message)

    node = nodes.Look(dir="Ahead", neg=True, body=pattern.node)
    return Pattern(node, composite=True)

def behind(pattern):
    """
    Creates a positive lookbehind assertion that checks for a pattern behind without consuming it.

    A positive lookbehind verifies that the specified pattern exists immediately
    before the current position, but does not include it in the match result.
    This allows you to enforce conditions on what precedes a match.

    Parameters
    ----------
    pattern : Pattern or str
        The pattern to look behind for. Strings are automatically converted to
        literal patterns.

    Returns
    -------
    Pattern
        A new Pattern object representing the positive lookbehind assertion.

    Examples
    --------
    Simple Use: Match a letter only if preceded by a digit
        >>> import STRling.simply as s
        >>> import re
        >>> pattern = s.merge(s.behind(s.digit()), s.letter())
        >>> match = re.search(str(pattern), '5A')
        >>> match.group()
        'A'
        >>> bool(re.search(str(pattern), 'BA'))
        False

    Advanced Use: Match prices with currency symbol
        >>> # Match digits only if preceded by $
        >>> price = s.merge(s.behind(s.lit('$')), s.digit(1, 0))
        >>> text = "Item costs $42.50 or 50 euros"
        >>> match = re.search(str(price), text)
        >>> match.group()
        '42'

    Raises
    ------
    STRlingError
        If the pattern parameter is not a Pattern or string.

    Notes
    -----
    Lookbehinds are zero-width assertions: they don't consume any characters.
    The regex engine position remains unchanged after a lookbehind check.
    
    Some regex engines (including Python's) require lookbehinds to have a
    fixed width. Variable-length lookbehinds may not be supported in all contexts.

    See Also
    --------
    not_behind : For negative lookbehind (pattern must NOT be before)
    ahead : For positive lookahead (check what comes after)
    """
    if isinstance(pattern, str):
        pattern = lit(pattern)

    if not isinstance(pattern, Pattern):
        message = """
        Method: simply.behind(pattern)

        The parameter must be an instance of `Pattern` or `str`.

        Use a string such as "123abc$" to match literal characters, or use a predefined set like `simply.letter()`.
        """
        raise STRlingError(message)

    node = nodes.Look(dir="Behind", neg=False, body=pattern.node)
    return Pattern(node, composite=True)

def not_behind(pattern):
    """
    Creates a negative lookbehind assertion that checks a pattern is NOT behind.

    A negative lookbehind verifies that the specified pattern does NOT exist
    immediately before the current position. The match succeeds only if the
    pattern is absent. Like all lookarounds, it doesn't consume any characters.

    Parameters
    ----------
    pattern : Pattern or str
        The pattern to check for absence before the current position. Strings
        are automatically converted to literal patterns.

    Returns
    -------
    Pattern
        A new Pattern object representing the negative lookbehind assertion.

    Examples
    --------
    Simple Use: Match a letter only if NOT preceded by a digit
        >>> import STRling.simply as s
        >>> import re
        >>> pattern = s.merge(s.not_behind(s.digit()), s.letter())
        >>> match = re.search(str(pattern), 'AB')
        >>> match.group()
        'A'
        >>> bool(re.search(str(pattern), '5A'))
        False

    Advanced Use: Match words not preceded by negation
        >>> # Match 'possible' but not when preceded by 'im'
        >>> word = s.merge(s.not_behind(s.lit('im')), s.lit('possible'))
        >>> bool(re.search(str(word), 'possible'))
        True
        >>> bool(re.search(str(word), 'impossible'))
        False

    Raises
    ------
    STRlingError
        If the pattern parameter is not a Pattern or string.

    Notes
    -----
    Some regex engines (including Python's) require lookbehinds to have a
    fixed width. Variable-length lookbehinds may not be supported in all contexts.

    See Also
    --------
    behind : For positive lookbehind (pattern MUST be before)
    not_ahead : For negative lookahead (check what's NOT after)
    """
    if isinstance(pattern, str):
        pattern = lit(pattern)

    if not isinstance(pattern, Pattern):
        message = """
        Method: simply.not_behind(pattern)

        The parameter must be an instance of `Pattern` or `str`.

        Use a string such as "123abc$" to match literal characters, or use a predefined set like `simply.letter()`.
        """
        raise STRlingError(message)

    node = nodes.Look(dir="Behind", neg=True, body=pattern.node)
    return Pattern(node, composite=True)

def has(pattern):
    """
    Creates a lookahead that checks for pattern presence anywhere in the remaining string.

    This function creates a lookahead assertion that succeeds if the specified
    pattern can be found anywhere in the string after the current position. It's
    useful for validating that certain content exists without consuming it.

    Parameters
    ----------
    pattern : Pattern or str
        The pattern to search for in the remaining string. Strings are
        automatically converted to literal patterns.

    Returns
    -------
    Pattern
        A new Pattern object representing the presence check.

    Examples
    --------
    Simple Use: Verify a string contains a digit somewhere
        >>> import STRling.simply as s
        >>> import re
        >>> pattern = s.has(s.digit())
        >>> bool(re.search(str(pattern), 'abc123'))
        True
        >>> bool(re.search(str(pattern), 'abcdef'))
        False

    Advanced Use: Password must contain both letter and digit
        >>> has_letter = s.has(s.letter())
        >>> has_digit = s.has(s.digit())
        >>> password = s.merge(has_letter, has_digit, s.any(8, 0))
        >>> bool(re.match(str(password), 'pass1word'))
        True
        >>> bool(re.match(str(password), 'password'))
        False

    Raises
    ------
    STRlingError
        If the pattern parameter is not a Pattern or string.

    Notes
    -----
    This is implemented as a positive lookahead containing `.*pattern`, which
    means it checks from the current position to the end of the string.
    
    Since this is a lookahead, it doesn't consume any characters. You can use
    multiple `has()` assertions to check for multiple required patterns.

    See Also
    --------
    has_not : For checking pattern absence anywhere in the string
    ahead : For checking pattern at the immediate next position
    """
    if isinstance(pattern, str):
        pattern = lit(pattern)

    if not isinstance(pattern, Pattern):
        message = """
        Method: simply.has(pattern)

        The parameter must be an instance of `Pattern` or `str`.

        Use a string such as "123abc$" to match literal characters, or use a predefined set like `simply.letter()`.
        """
        raise STRlingError(message)

    # Create a Look node with dir="Ahead" and a body that matches .*pattern
    dot_star = nodes.CharClass(False, [nodes.ClassEscape('s')])
    dot_star_node = nodes.Quant(child=dot_star, min=0, max=float('inf'), mode="Greedy")
    seq_node = nodes.Seq([dot_star_node, pattern.node])
    
    node = nodes.Look(dir="Ahead", neg=False, body=seq_node)
    return Pattern(node, composite=True)

def has_not(pattern):
    """
    Creates a lookahead that checks for pattern absence anywhere in the remaining string.

    This function creates a lookahead assertion that succeeds only if the specified
    pattern cannot be found anywhere in the string after the current position. It's
    useful for validation that certain content does NOT exist.

    Parameters
    ----------
    pattern : Pattern or str
        The pattern to verify is absent from the remaining string. Strings are
        automatically converted to literal patterns.

    Returns
    -------
    Pattern
        A new Pattern object representing the absence check.

    Examples
    --------
    Simple Use: Verify a string contains no digits
        >>> import STRling.simply as s
        >>> import re
        >>> pattern = s.has_not(s.digit())
        >>> bool(re.search(str(pattern), 'abcdef'))
        True
        >>> bool(re.search(str(pattern), 'abc123'))
        False

    Advanced Use: Password must not contain spaces or special characters
        >>> no_spaces = s.has_not(s.lit(' '))
        >>> no_special = s.has_not(s.special_char())
        >>> password = s.merge(no_spaces, no_special, s.alpha_num(8, 0))
        >>> bool(re.match(str(password), 'password123'))
        True
        >>> bool(re.match(str(password), 'pass word'))
        False

    Raises
    ------
    STRlingError
        If the pattern parameter is not a Pattern or string.

    Notes
    -----
    This is implemented as a negative lookahead containing `.*pattern`, which
    means it checks from the current position to the end of the string.
    
    Since this is a lookahead, it doesn't consume any characters. You can use
    multiple `has_not()` assertions to check for multiple forbidden patterns.

    See Also
    --------
    has : For checking pattern presence anywhere in the string
    not_ahead : For checking pattern absence at the immediate next position
    """
    if isinstance(pattern, str):
        pattern = lit(pattern)

    if not isinstance(pattern, Pattern):
        message = """
        Method: simply.has(pattern)

        The parameter must be an instance of `Pattern` or `str`.

        Use a string such as "123abc$" to match literal characters, or use a predefined set like `simply.letter()`.
        """
        raise STRlingError(message)

    # Create a Look node with dir="Ahead", neg=True and a body that matches .*pattern
    dot_star = nodes.CharClass(False, [nodes.ClassEscape('s')])
    dot_star_node = nodes.Quant(child=dot_star, min=0, max=float('inf'), mode="Greedy")
    seq_node = nodes.Seq([dot_star_node, pattern.node])
    
    node = nodes.Look(dir="Ahead", neg=True, body=seq_node)
    return Pattern(node, composite=True)
