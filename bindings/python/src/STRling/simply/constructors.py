"""
Pattern constructors for building composite patterns in STRling.

This module provides high-level functions for creating complex pattern structures
through composition. Functions here handle alternation (any_of), optionality (may),
concatenation (merge), and grouping operations (capture, group). These are the
primary building blocks for constructing sophisticated regex patterns in a
readable and maintainable way.
"""

from .pattern import STRlingError, Pattern, lit
from STRling.core import nodes


def any_of(*patterns):
    """
    Matches any one of the provided patterns (alternation/OR operation).

    This function creates a pattern that succeeds if any of the provided patterns
    match at the current position. It's equivalent to the | operator in regular
    expressions.

    Parameters
    ----------
    *patterns : Pattern or str
        One or more patterns to be matched. Strings are automatically converted
        to literal patterns.

    Returns
    -------
    Pattern
        A new Pattern object representing the alternation of all provided patterns.

    Examples
    --------
    Simple Use: Match either 'cat' or 'dog'
        >>> import STRling.simply as s
        >>> import re
        >>> pattern = s.any_of('cat', 'dog')
        >>> bool(re.search(str(pattern), 'I have a cat'))
        True
        >>> bool(re.search(str(pattern), 'I have a dog'))
        True

    Advanced Use: Match different number formats
        >>> # Matches 3 digits followed by 3 letters, OR 3 letters followed by 3 digits
        >>> pattern1 = s.merge(s.digit(3), s.letter(3))
        >>> pattern2 = s.merge(s.letter(3), s.digit(3))
        >>> either_pattern = s.any_of(pattern1, pattern2)
        >>> bool(re.search(str(either_pattern), 'ABC123'))
        True
        >>> bool(re.search(str(either_pattern), '123ABC'))
        True

    Raises
    ------
    STRlingError
        If any parameter is not a Pattern or string, or if duplicate named groups
        are found across the patterns.

    Notes
    -----
    Named groups must be unique across all alternatives. If you need to use the
    same group name in different branches, consider using numbered capture groups
    with `s.capture()` instead.

    See Also
    --------
    merge : For concatenating patterns sequentially
    may : For optional patterns
    """

    clean_patterns = []
    for pattern in patterns:
        if isinstance(pattern, str):
            pattern = lit(pattern)

        if not isinstance(pattern, Pattern):
            message = """
            Method: simply.any_of(*patterns)

            The parameters must be instances of `Pattern` or `str`.

            Use a string such as "123abc$" to match literal characters, or use a predefined set like `simply.letter()`.
            """
            raise STRlingError(message)

        clean_patterns.append(pattern)


    named_group_counts = {}
    for pattern in clean_patterns:
        for group_name in pattern.named_groups:
            if group_name in named_group_counts:
                named_group_counts[group_name] += 1
            else:
                named_group_counts[group_name] = 1

    duplicates = {name: count for name, count in named_group_counts.items() if count > 1}
    if duplicates:
        duplicate_info = ", ".join([f"{name}: {count}" for name, count in duplicates.items()])
        message = f"""
        Method: simply.any_of(*patterns)

        Named groups must be unique.
        Duplicate named groups found: {duplicate_info}.

        If you need later reference change the named group argument to `simply.capture()`.
        If you don't need later reference change the named group argument to `simply.merge()`.
        """
        raise STRlingError(message)

    sub_names = named_group_counts.keys()

    # Create an Alt node with children nodes
    child_nodes = [p.node for p in clean_patterns]
    node = nodes.Alt(child_nodes)
    
    return Pattern(node, composite=True, named_groups=clean_patterns[0].named_groups)

def may(*patterns):
    """
    Makes the provided patterns optional (matches 0 or 1 times).

    This function creates a pattern that may or may not be present. If the pattern
    is absent, the overall match can still succeed. This is equivalent to the ?
    quantifier in regular expressions.

    Parameters
    ----------
    *patterns : Pattern or str
        One or more patterns to be optionally matched. Strings are automatically
        converted to literal patterns. Multiple patterns are concatenated together.

    Returns
    -------
    Pattern
        A new Pattern object representing the optional pattern(s).

    Examples
    --------
    Simple Use: Match a letter with optional trailing digit
        >>> import STRling.simply as s
        >>> import re
        >>> pattern = s.merge(s.letter(), s.may(s.digit()))
        >>> matches = re.findall(str(pattern), 'A B2 C')
        >>> matches
        ['A', 'B2', 'C']

    Advanced Use: Optional protocol in URL pattern
        >>> protocol = s.may(s.merge(s.any_of('http', 'https'), '://'))
        >>> domain = s.merge(s.letter(1, 0), '.', s.letter(2, 3))
        >>> url_pattern = s.merge(protocol, domain)
        >>> bool(re.search(str(url_pattern), 'https://example.com'))
        True
        >>> bool(re.search(str(url_pattern), 'example.com'))
        True

    Raises
    ------
    STRlingError
        If any parameter is not a Pattern or string, or if duplicate named groups
        are found.

    Notes
    -----
    When multiple patterns are provided, they are concatenated together before
    being made optional. For example, `s.may(s.digit(), s.letter())` matches
    zero or one occurrence of a digit followed by a letter, not zero or one
    of each individually.

    See Also
    --------
    any_of : For alternation between patterns
    merge : For concatenating patterns
    """

    clean_patterns = []
    for pattern in patterns:
        if isinstance(pattern, str):
            pattern = lit(pattern)

        if not isinstance(pattern, Pattern):
            message = """
            Method: simply.may(*patterns)

            The parameters must be instances of `Pattern` or `str`.

            Use a string such as "123abc$" to match literal characters, or use a predefined set like `simply.letter()`.
            """
            raise STRlingError(message)

        clean_patterns.append(pattern)


    named_group_counts = {}
    for pattern in clean_patterns:
        for group_name in pattern.named_groups:
            if group_name in named_group_counts:
                named_group_counts[group_name] += 1
            else:
                named_group_counts[group_name] = 1

    duplicates = {name: count for name, count in named_group_counts.items() if count > 1}
    if duplicates:
        duplicate_info = ", ".join([f"{name}: {count}" for name, count in duplicates.items()])
        message = f"""
        Method: simply.may(*patterns)

        Named groups must be unique.
        Duplicate named groups found: {duplicate_info}.

        If you need later reference change the named group argument to `simply.capture()`.
        If you don't need later reference change the named group argument to `simply.merge()`.
        """
        raise STRlingError(message)

    sub_names = named_group_counts.keys()

    # Create a sequence of nodes then wrap in Quant with min=0, max=1
    if len(clean_patterns) == 1:
        inner_node = clean_patterns[0].node
    else:
        child_nodes = [p.node for p in clean_patterns]
        inner_node = nodes.Seq(child_nodes)
    
    node = nodes.Quant(child=inner_node, min=0, max=1, mode="Greedy")
    
    return Pattern(node, composite=True, named_groups=clean_patterns[0].named_groups)



def merge(*patterns):
    """
    Concatenates the provided patterns into a single sequential pattern.

    This function creates a pattern that matches all provided patterns in order,
    one after another. It's the fundamental operation for building complex patterns
    from simpler components.

    Parameters
    ----------
    *patterns : Pattern or str
        One or more patterns to be concatenated. Strings are automatically
        converted to literal patterns.

    Returns
    -------
    Pattern
        A new Pattern object representing the concatenated sequence.

    Examples
    --------
    Simple Use: Match digit followed by literal text
        >>> import STRling.simply as s
        >>> import re
        >>> pattern = s.merge(s.digit(), ',.')
        >>> match = re.search(str(pattern), 'test5,.')
        >>> match.group()
        '5,.'

    Advanced Use: Build a complete email pattern
        >>> username = s.merge(s.alpha_num(1, 0), s.may(s.merge('.', s.alpha_num(1, 0))))
        >>> at_sign = s.lit('@')
        >>> domain = s.merge(s.alpha_num(1, 0), '.', s.letter(2, 4))
        >>> email = s.merge(username, at_sign, domain)
        >>> bool(re.search(str(email), 'user@example.com'))
        True

    Raises
    ------
    STRlingError
        If any parameter is not a Pattern or string, or if duplicate named groups
        are found across the patterns.

    Notes
    -----
    All named groups within merged patterns must be unique. If the same named
    group appears multiple times, use `s.capture()` for numbered groups or
    ensure each named group has a distinct name.

    See Also
    --------
    any_of : For alternation (OR operation)
    capture : For creating numbered capture groups
    group : For creating named capture groups
    """

    clean_patterns = []
    for pattern in patterns:
        if isinstance(pattern, str):
            pattern = lit(pattern)

        if not isinstance(pattern, Pattern):
            message = """
            Method: simply.merge(*patterns)

            The parameters must be instances of `Pattern` or `str`.

            Use a string such as "123abc$" to match literal characters, or use a predefined set like `simply.letter()`.
            """
            raise STRlingError(message)

        clean_patterns.append(pattern)


    named_group_counts = {}
    for pattern in clean_patterns:
        for group_name in pattern.named_groups:
            if group_name in named_group_counts:
                named_group_counts[group_name] += 1
            else:
                named_group_counts[group_name] = 1

    duplicates = {name: count for name, count in named_group_counts.items() if count > 1}
    if duplicates:
        duplicate_info = ", ".join([f"{name}: {count}" for name, count in duplicates.items()])
        message = f"""
        Method: simply.merge(*patterns)

        Named groups must be unique.
        Duplicate named groups found: {duplicate_info}.

        If you need later reference change the named group argument to `simply.capture()`.
        If you don't need later reference change the named group argument to `simply.merge()`.
        """
        raise STRlingError(message)

    sub_names = named_group_counts.keys()

    # Create a Seq node with children nodes
    child_nodes = [p.node for p in clean_patterns]
    node = nodes.Seq(child_nodes)
    
    sub_names = []
    for pattern in clean_patterns:
        sub_names.extend(pattern.named_groups)
    
    return Pattern(node, composite=True, named_groups=sub_names)

def capture(*patterns):
    """
    Creates a numbered capture group for extracting matched content by index.

    Capture groups allow you to extract specific portions of a matched pattern
    using numeric indices. Unlike named groups, capture groups can be repeated
    with quantifiers, and each repetition creates a new numbered group.

    Parameters
    ----------
    *patterns : Pattern or str
        One or more patterns to be captured. Strings are automatically
        converted to literal patterns. Multiple patterns are concatenated.

    Returns
    -------
    Pattern
        A new Pattern object representing the numbered capture group.

    Examples
    --------
    Simple Use: Capture a digit-comma-period sequence
        >>> import STRling.simply as s
        >>> import re
        >>> pattern = s.capture(s.digit(), ',.')
        >>> match = re.search(str(pattern), '5,.')
        >>> match.group(0)  # Full match
        '5,.'
        >>> match.group(1)  # First capture group
        '5,.'

    Advanced Use: Multiple captures with repetition
        >>> three_digit_group = s.capture(s.digit(3))
        >>> four_groups = three_digit_group.rep(4)
        >>> text = "Here is a number: 111222333444"
        >>> match = re.search(str(four_groups), text)
        >>> match.group(0)  # Full match
        '111222333444'
        >>> match.group(1)  # First capture
        '111'
        >>> match.group(2)  # Second capture
        '222'
        >>> match.group(3)  # Third capture
        '333'
        >>> match.group(4)  # Fourth capture
        '444'

    Raises
    ------
    STRlingError
        If any parameter is not a Pattern or string, or if duplicate named groups
        are found within the captured patterns.

    Notes
    -----
    Captures can be repeated with `.rep(n)` or `.rep(min, max)`, and each
    repetition creates a new numbered group. However, captures CANNOT be
    invoked with a range using the call syntax:
    
    - VALID: `s.capture(s.digit(), s.letter()).rep(3)`
    - INVALID: `s.capture(s.digit(), s.letter())(1, 2)`

    See Also
    --------
    group : For creating named capture groups
    merge : For non-capturing concatenation
    """


    clean_patterns = []
    for pattern in patterns:
        if isinstance(pattern, str):
            pattern = lit(pattern)

        if not isinstance(pattern, Pattern):
            message = """
            Method: simply.capture(*patterns)

            The parameters must be instances of `Pattern` or `str`.

            Use a string such as "123abc$" to match literal characters, or use a predefined set like `simply.letter()`.
            """
            raise STRlingError(message)

        clean_patterns.append(pattern)


    named_group_counts = {}
    for pattern in clean_patterns:
        for group_name in pattern.named_groups:
            if group_name in named_group_counts:
                named_group_counts[group_name] += 1
            else:
                named_group_counts[group_name] = 1

    duplicates = {name: count for name, count in named_group_counts.items() if count > 1}
    if duplicates:
        duplicate_info = ", ".join([f"{name}: {count}" for name, count in duplicates.items()])
        message = f"""
        Method: simply.capture(*patterns)

        Named groups must be unique.
        Duplicate named groups found: {duplicate_info}.

        If you need later reference change the named group argument to `simply.capture()`.
        If you don't need later reference change the named group argument to `simply.merge()`.
        """
        raise STRlingError(message)

    sub_names = named_group_counts.keys()

    # Create a Group node with capturing=True
    if len(clean_patterns) == 1:
        body_node = clean_patterns[0].node
    else:
        child_nodes = [p.node for p in clean_patterns]
        body_node = nodes.Seq(child_nodes)
    
    node = nodes.Group(capturing=True, body=body_node)
    
    sub_names = []
    for pattern in clean_patterns:
        sub_names.extend(pattern.named_groups)
    
    return Pattern(node, composite=True, numbered_group=True, named_groups=sub_names)

def group(name, *patterns):
    """
    Creates a named capture group that can be referenced by name for extracting matched content.

    Named groups allow you to extract specific portions of a matched pattern using
    descriptive names rather than numeric indices, making your code more readable
    and maintainable.

    Parameters
    ----------
    name : str
        The unique name for the group (e.g., 'area_code'). Must be a valid Python
        identifier and must be unique within the entire pattern.
    *patterns : Pattern or str
        One or more patterns to be captured. Strings are automatically converted
        to literal patterns. Multiple patterns are concatenated.

    Returns
    -------
    Pattern
        A new Pattern object representing the named capture group.

    Examples
    --------
    Simple Use: Capture a digit-comma-period sequence with a name
        >>> import STRling.simply as s
        >>> import re
        >>> pattern = s.group('my_group', s.digit(), ',.')
        >>> match = re.search(str(pattern), '5,.')
        >>> match.group('my_group')
        '5,.'

    Advanced Use: Build a phone number pattern with named groups
        >>> first = s.group("first", s.digit(3))
        >>> second = s.group("second", s.digit(3))
        >>> third = s.group("third", s.digit(4))
        >>> phone_pattern = s.merge(first, "-", second, "-", third)
        >>> text = "Here is a phone number: 123-456-7890."
        >>> match = re.search(str(phone_pattern), text)
        >>> match.group()
        '123-456-7890'
        >>> match.group("first")
        '123'
        >>> match.group("second")
        '456'
        >>> match.group("third")
        '7890'

    Raises
    ------
    STRlingError
        If name is not a string, if any pattern parameter is not a Pattern or
        string, or if duplicate named groups are found.

    Notes
    -----
    Named groups CANNOT be repeated with quantifiers like `.rep(1, 3)` because
    each repetition would create multiple groups with the same name, which is not
    allowed. For repeatable patterns, use `s.capture()` for numbered groups or
    `s.merge()` for non-capturing concatenation.
    
    Groups cannot be invoked with ranges using the call syntax:
    - INVALID: `s.group('name', s.digit())(1, 2)`
    
    All named groups must have unique names throughout the entire pattern. If you
    need to use the same pattern multiple times, create it once and reference it,
    or use numbered captures instead.

    See Also
    --------
    capture : For numbered, repeatable capture groups
    merge : For non-capturing concatenation
    """

    if not isinstance(name, str):
        message = """
        Method: simply.group(name, *patterns)

        The group is missing a specified name.
        The `name` parameter must be a string like 'group_name'.
        """
        raise STRlingError(message)


    clean_patterns = []
    for pattern in patterns:
        if isinstance(pattern, str):
            pattern = lit(pattern)

        if not isinstance(pattern, Pattern):
            message = """
            Method: simply.group(name, *patterns)

            The parameters must be instances of `Pattern` or `str`.

            Use a string such as "123abc$" to match literal characters, or use a predefined set like `simply.letter()`.
            """
            raise STRlingError(message)

        clean_patterns.append(pattern)


    named_group_counts = {}
    for pattern in clean_patterns:
        for group_name in pattern.named_groups:
            if group_name in named_group_counts:
                named_group_counts[group_name] += 1
            else:
                named_group_counts[group_name] = 1

    duplicates = {name: count for name, count in named_group_counts.items() if count > 1}
    if duplicates:
        duplicate_info = ", ".join([f"{name}: {count}" for name, count in duplicates.items()])
        message = f"""
        Method: simply.group(name, *patterns)

        Named groups must be unique.
        Duplicate named groups found: {duplicate_info}.

        If you need later reference change the named group argument to `simply.capture()`.
        If you don't need later reference change the named group argument to `simply.merge()`.
        """
        raise STRlingError(message)

    sub_names = named_group_counts.keys()

    # Create a Group node with capturing=True and name=name
    if len(clean_patterns) == 1:
        body_node = clean_patterns[0].node
    else:
        child_nodes = [p.node for p in clean_patterns]
        body_node = nodes.Seq(child_nodes)
    
    node = nodes.Group(capturing=True, body=body_node, name=name)
    
    sub_names = []
    for pattern in clean_patterns:
        sub_names.extend(pattern.named_groups)
    
    return Pattern(node, composite=True, named_groups=[name, *sub_names])
